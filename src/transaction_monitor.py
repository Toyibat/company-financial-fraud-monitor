from datetime import datetime
from .data_manager import id_key

def parse_id_number(text): 

    text = text.strip().upper()
    if text.startswith("TXN"):
        text = text[3:]
    return int(text) if text.isdigit() else None

def binary_search(records, target_number):
    """ This should search transactions using ID
        It should return (index, comparisons) if found or -1, comparisons if id not found
    """
    low = 0
    high = len(records) - 1
    comparisons = 0 

    while low <= high:
        mid = (low + high) // 2
        comparisons += 1 
        mid_number = id_key(records[mid])

        if mid_number == target_number:
            return mid, comparisons
        elif mid_number < target_number:
            low = mid + 1
        else:
            high = mid - 1

    return -1, comparisons

def find_by_id(records, text):
    """ This should look up a transaction from what the user typed and return the record or None if its not found"""
    number = parse_id_number(text)
    if number is None:
        return None, 0
    index, comparisons = binary_search(records, number)
    return (records[index] if index >= 0 else None), comparisons

# for matching using dictionary, we need to check if a record has a reference, and then group records by reference.

def has_reference(record):
    reference = record["reference"].strip()
    return reference not in ("", "N/A")


def match_by_reference(records):
    """Dictionary: reference - list of records sharing it.
    A sale and thebank settlement will share a reference, same as an invoice and
    each payment made against it."""
    groups = {}
    for record in records:
        if has_reference(record):
            groups.setdefault(record["reference"], []).append(record)
    return groups

MISMATCH_TOLERANCE = 0.005
# date and time to help
def to_date(record):
    return datetime.strptime(record["date"], "%Y-%m-%d").date()

def minutes_after_midnight(record):
    hours, minutes = record["time"].split(":")
    return int(hours) * 60 + int(minutes)

# checking for anomalies in the records like amount mismatches or missing expected records.
def check_amount_mismatch(records):
    """check if recorded/stored amount differs from the expected amount."""
    for r in records:
        if r["expected_amount"] > 0:
            difference = r["amount"] - r["expected_amount"]
            if abs(difference) > MISMATCH_TOLERANCE:
                percent = difference / r["expected_amount"] * 100
                yield (r, "amount_mismatch",
                       f"recorded {r['amount']:,.2f} but expected "
                       f"{r['expected_amount']:,.2f} ({percent:+.1f}%)")

def check_no_expected_record(records):
    """Money moved with nothing to explain it."""
    for r in records:
        if r["expected_amount"] == 0 and r["amount"] > 0:
            yield (r, "no_expected_record",
                   f"{r['amount']:,.2f} recorded with no matching expected amount")

APPROVAL_LIMIT = 500000 
LARGE_AMT_LIMIT = 2000000
OPENING_HOUR = 7*60
CLOSING_HOUR = 22*60  #22:00
NEAR_APPROVAL_LIMIT_RATIO = 0.90  
MIN_SPLIT_COUNT = 2 
def check_duplicate_payment(records):
    """The same billpaid to the same supplier more than once.
    Records are in ID order, so the first payment is kept and later ones
    are flagged just to confirm."""
    first_payment = {}
    for r in records:
        if r["transaction_type"] != "supplier_payment" or not has_reference(r):
            continue
        key = (r["reference"].strip(), r["pay_source_recipient"].strip())
        if key in first_payment:
            earlier = first_payment[key]
            yield (r, "duplicate_payment",
                   f"{r['reference']} already paid to {r['pay_source_recipient']} "
                   f"in {earlier['transaction_id']} on {earlier['date']}")
        else:
            first_payment[key] = r


def check_large_amount(records):
    """A single amount far above normal day-2-day amount being recorded."""
    for r in records:
        if r["amount"] > LARGE_AMT_LIMIT:
            yield (r, "large_amount",
                   f"{r['amount']:,.2f} exceeds {LARGE_AMT_LIMIT:,.0f}")


def check_off_hours(records):
    """RecordS outside business hours (will need the time column)."""
    for r in records:
        if not r["time"]or not r["time"].strip():
            continue
        minute = minutes_after_midnight(r)
        if minute < OPENING_HOUR or minute >= CLOSING_HOUR:
            yield (r, "off_hours",
                   f"recorded at {r['time']}, outside "
                   f"{OPENING_HOUR // 60:02d}:00-{CLOSING_HOUR // 60:02d}:00")


def check_split_below_limit(records):
    """Several transfers to one payee on one day, each just under the
    approval limit (splitting a large payment to avoid approval)."""
    lower = APPROVAL_LIMIT * NEAR_APPROVAL_LIMIT_RATIO
    groups = {}
    for r in records:
        if (r["transaction_type"] == "bank_transfer" and r["direction"] != "in"
                and lower <= r["amount"] < APPROVAL_LIMIT):
            groups.setdefault((r["date"], r["pay_source_recipient"]), []).append(r)
    for (day, payee), group in groups.items():
        if len(group) >= MIN_SPLIT_COUNT:
            total = sum(r["amount"] for r in group)
            for r in group:
                yield (r, "split_below_limit",
                       f"{len(group)} transfers to {payee} on {day}, each just "
                       f"under {APPROVAL_LIMIT:,.0f} (total {total:,.2f})")