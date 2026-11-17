"""

This  handles loading, retrieving, validating and updating
transaction records during application use.

Concepts used: dictionaries (one record = one dict), lists (the record
collection), file handling (CSV read/write), validation with exceptions.

Record format (a dict):
    Record format (a dict):
    transaction_id       str       unique transaction ID
    date                 str       transaction date (YYYY-MM-DD)
    time                 str       transaction time (HH:MM)
    transaction_type     str       sale, bank_transfer, refund, supplier_payment
    payment_method       str       payment method
    direction            str       incoming or outgoing transaction
    pay_source_recipient str       source or recipient
    reference            str       transaction reference
    amount               float     amount actually recorded
    expected_amount      float     expected amount
    description          str       transaction description
    recorded_by          str       person recording the transaction
    scenario             str       dataset scenario label
    expected_outcome     str       expected detection outcome
    approval_required    str       whether approval is required

note: session.records is always sorted by id_key(). Binary search in
transaction_monitor depends on this.

Feature functions called from the main menu:
    load_transactions(session)
    add_transaction(session)
"""

import csv
import re
from datetime import datetime
from pathlib import Path
import math

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "transactions.csv"
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "transaction_id",
    "date",
    "time",
    "transaction_type",
    "payment_method",
    "direction",
    "pay_source_recipient",
    "reference",
    "amount",
    "expected_amount",
    "description",
    "recorded_by",
    "scenario",
    "expected_outcome",
    "approval_required",
]
REQUIRED_FIELDS = [
    field for field in FIELDS
    if field not in ("scenario", "expected_outcome")
]           
TRANSACTION_TYPES = ["sale", "bank_transfer", "refund", "supplier_payment"]

ID_PATTERN = re.compile(r"^TXN(\d+)$")
DATE_FORMAT = "%Y-%m-%d"


# for help with menu
def id_key(record):
    """Numeric sort key for a record, e.g. TXN0042 -> 42.
    transaction_monitor should use this same key for binary search."""
    return int(ID_PATTERN.match(record["transaction_id"]).group(1))


def parse_row(row):
    """Validate one CSV row and return a good record dict.
    it should raise ValueError with a readable reason if the row is bad."""
    tid = (row.get("transaction_id") or "").strip().upper()
    if not ID_PATTERN.match(tid):
        raise ValueError(f"invalid transaction ID '{tid}'")

    date_text = (row.get("date") or "").strip()
    try:
        datetime.strptime(date_text, DATE_FORMAT)
    except ValueError:
        raise ValueError(f"invalid date '{date_text}' (use YYYY-MM-DD)")

    ttype = (row.get("transaction_type") or "").strip().lower()
    if ttype not in TRANSACTION_TYPES:
        raise ValueError(f"unknown transaction type '{ttype}'")

    amounts = {}
    for name in ("amount", "expected_amount"):
        text = (row.get(name) or "").strip()
        try:
            value = float(text)
        except ValueError:
            raise ValueError(f"{name} '{text}' is not a number")
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a non-negative number")
        amounts[name] = value

    return {
        "transaction_id": tid,
        "date": date_text,
        "time": (row.get("time") or "").strip(),
        "transaction_type": ttype,
        "payment_method": (row.get("payment_method") or "").strip(),
        "direction": (row.get("direction") or "").strip(),
        "pay_source_recipient": (row.get("pay_source_recipient") or "").strip(),
        "reference": (row.get("reference") or "").strip(),
        "amount": amounts["amount"],
        "expected_amount": amounts["expected_amount"],
        "description": (row.get("description") or "").strip(),
        "recorded_by": (row.get("recorded_by") or "").strip(),
        "scenario": (row.get("scenario") or "").strip(),
        "expected_outcome": (row.get("expected_outcome") or "").strip(),
        "approval_required": (row.get("approval_required") or "").strip(),
    }


def next_transaction_id(records):
    """Next free ID. Because it is always max + 1, appending keeps the
    list sorted."""
    highest = max((id_key(r) for r in records), default=0)
    return f"TXN{highest + 1:04d}"


def count_by_type(records):
    """Dictionary of how many records exist for each transaction type."""
    counts = {}
    for record in records:
        kind = record["transaction_type"]
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def get_by_type(records, transaction_type):
    """Retrieve every record of one type (helper for other modules)."""
    return [r for r in records if r["transaction_type"] == transaction_type]


# file Input/Output functions that read/write the csv.
def load_records(path=DATA_FILE):
    """Read the CSV. Returns (records sorted by ID, list of problem messages).
    Bad rows and duplicate IDs are skipped and reported, not fatal."""
    records, problems, seen = [], [], set()
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [f for f in REQUIRED_FIELDS if f not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"file is missing column(s): {', '.join(missing)}")
        for line_no, row in enumerate(reader, start=2):   # line 1 is the header
            try:
                record = parse_row(row)
            except ValueError as err:
                problems.append(f"line {line_no}: {err}")
                continue
            if record["transaction_id"] in seen:
                problems.append(f"line {line_no}: duplicate ID {record['transaction_id']}")
                continue
            seen.add(record["transaction_id"])
            records.append(record)
    records.sort(key=id_key)
    return records, problems


def append_record(record, path=DATA_FILE):
    """Add one record to the end of the CSV without touching existing rows
    so the rows skipped at load time are never lost). 
    Creates the file with aheader if it does not exist yet."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0
    needs_newline = False
    if not needs_header:
        with open(path, "rb") as handle:
            handle.seek(-1, 2)
            needs_newline = handle.read(1) not in (b"\n", b"\r")
    with open(path, "a", newline="", encoding="utf-8") as handle:
        if needs_newline:
            handle.write("\n")
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if needs_header:
            writer.writeheader()
        writer.writerow(record)


def save_records(records, path=DATA_FILE):
# Save the entire list of records to the CSV, overwriting the file.
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    with open(temp, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    temp.replace(path)


# input help navigation
def ask_date(prompt):
    while True:
        text = input(prompt).strip()
        try:
            datetime.strptime(text, DATE_FORMAT)
            return text
        except ValueError:
            print("  Use the format YYYY-MM-DD, e.g. 2026-03-14.")


def ask_amount(prompt):
    while True:
        text = input(prompt).strip()
        try:
            value = float(text)
        except ValueError:
            print("  Please enter a number.")
            continue
        if not math.isfinite(value) or value < 0:
            print("  Amount cannot be negative.")
            continue
        return value


def ask_type():
    print("  Transaction type:")
    for number, name in enumerate(TRANSACTION_TYPES, start=1):
        print(f"    {number}. {name}")
    while True:
        choice = input("  Choose a type: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(TRANSACTION_TYPES):
            return TRANSACTION_TYPES[int(choice) - 1]
        print(f"  Enter a number from 1 to {len(TRANSACTION_TYPES)}.")


#  (menu)
def load_transactions(session):
    """Menu option: load the transaction file into the session."""
    if not DATA_FILE.exists():
        print(f"\n  Data file not found: {DATA_FILE}")
        print("  Add a transactions data file next to the data file, or create a new")
        print("  transaction with the 'Enter a new transaction' option.")
        return
    try:
        records, problems = load_records(DATA_FILE)
    except (OSError, ValueError) as err:
        print(f"\n  Could not load the file: {err}")
        return

    session.records = records
    session.flagged = []          # old flags no longer match the data
    print(f"\n  Loaded {len(records)} transaction(s) from {DATA_FILE.name}.")
    for kind, count in count_by_type(records).items():
        print(f"    {kind:<18} {count}")
    if problems:
        print(f"\n  {len(problems)} row(s) skipped:")
        for message in problems[:5]:
            print(f"    - {message}")
        if len(problems) > 5:
            print(f"    ... and {len(problems) - 5} more.")

def add_transaction(session):
    """Menu option: enter one transaction by hand and save it."""

    record = {
        "transaction_id": next_transaction_id(session.records),
        "date": ask_date("  Date (YYYY-MM-DD): "),
        "time": input("  Time (HH:MM): ").strip(),
        "transaction_type": ask_type(),
        "payment_method": input("  Payment method: ").strip(),
        "direction": input("  Direction (in/out): ").strip().lower(),
        "pay_source_recipient": input("  Source/recipient: ").strip(),
        "reference": input("  Reference: ").strip(),
        "amount": ask_amount("  Amount recorded: "),
        "expected_amount": ask_amount("  Expected amount: "),
        "description": input("  Description: ").strip(),
        "recorded_by": input("  Recorded by: ").strip(),
        "scenario": "",
        "expected_outcome": "",
        "approval_required": input(
            "  Is approval required? (yes/no): "
        ).strip().lower(),
    }

    print(
        f"\n  New record {record['transaction_id']}: "
        f"{record['transaction_type']}, "
        f"{record['amount']:,.2f} "
        f"(expected {record['expected_amount']:,.2f}) "
        f"on {record['date']}"
    )

    if input("  Save this transaction? (y/n): ").strip().lower() != "y":
        print("  Cancelled. Nothing was saved.")
        return

    try:
        append_record(record)
    except OSError as err:
        print(f"\n  Could not save transaction: {err}")
        return

    session.records.append(record)
    print(f"\n  Saved {record['transaction_id']} to {DATA_FILE.name}.")
