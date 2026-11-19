
from src.data_manager import load_records
from src.transaction_monitor import (
    check_amount_mismatch,
    check_no_expected_record,
    check_duplicate_payment,
    check_large_amount,
    check_off_hours,
    check_split_below_limit,
)

records, problems = load_records()

checks = [
    ("Amount mismatches", check_amount_mismatch),
    ("Missing expected records", check_no_expected_record),
    ("Duplicate payments", check_duplicate_payment),
    ("Large amounts", check_large_amount),
    ("Off-hours transactions", check_off_hours),
    ("Possible split payments", check_split_below_limit),
]

print("Records loaded:", len(records))
print("Loading problems:", len(problems))

for name, check in checks:
    findings = list(check(records))

    print(f"\n{name}: {len(findings)}")

    for record, code, detail in findings:
        print(f"  {record['transaction_id']} | {code} | {detail}")
print("\n--- SPLIT PAYMENT RECORD DETAILS ---")

for record, code, detail in check_split_below_limit(records):
    print(
        record["transaction_id"],
        record["date"],
        record["transaction_type"],
        record["direction"],
        record["pay_source_recipient"],
        f'{record["amount"]:,.2f}',
        record["reference"]
    )