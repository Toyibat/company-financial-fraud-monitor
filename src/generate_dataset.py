"""
generate_dataset.py - This synthetic transactions.csv was made for the project instead of manually creating it. IBM dataset was used as a reference to create the dataset.

The fixed seed means everyone who runs it gets the identical file (repeatable results for the report).

The company is intentionally made small to make it realistic: one store, one bank account.
Instead of random numbers, every row comes from a SCENARIO with a known
outcome, so that the monitor and risk analyzer can be evaluated against the truth.

The design is based on public transaction datasets (IBM AML: timestamp, payment
format, amount, laundering label; PaySim: type, amount, balances, fraud flag):
    time           - timestamp (for unusual times)
    payment_method - "Payment Format" / "type"
    direction      - money in or out of the business
    pay_source_recipient/counterparty   - who the money came from / went to
    reference      - links a sale to its bank or an invoice to
                      its payment (duplicates share a reference)
    scenario / expected_outcome - our ground truth for evaluation 
Our own extra column is expected_amount, which should show the risk rules.

"""





import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 42
START, END = date(2026, 1, 1), date(2026, 3, 31)
CARD_FEE_RATE = 0.015           # normal processor fee, already in expected_amount
APPROVAL_LIMIT = 500_000        # transfers above this need manager approval

FIELDS = [
    "transaction_id", "date", "time", "transaction_type", "payment_method",
    "direction", "pay_source_recipient", "reference", "amount", "expected_amount",
    "description", "recorded_by", "scenario", "expected_outcome","approval_required"
]

OUTCOME = {"normal": "satisfied", "fee_difference": "review"}   # all else: investigate

SUPPLIERS = {                    
    "Apple_LTD": (120_000, 30_000),
    "Side_Quest_electronics": (200_000, 40_000),
    "Argos": (90_000, 20_000),
    "Keele_Gadgets": (70_000, 15_000),
    "Anees_Mobiles": (25_000, 6_000),
    "Nokia_Retails": (18_000, 4_000),
}

rng = random.Random(SEED) # we use this so that everyone who runs this gets the identical file (repeatable results for the report).
rows = []
counters = {"SINV": 0, "REF": 0, "TRF": 0} # store the last used number for each reference type, so that we can generate unique references.


# - help
def money(value):
    return round(value, 2)


def clock(start_hour, end_hour):
    
    minutes = rng.randint(int(start_hour * 60), int(end_hour * 60) - 1)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def next_business_day(day):
    day += timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def next_ref(prefix):
    counters[prefix] += 1
    return f"{prefix}-{counters[prefix]:04d}"


def add(day, time, ttype, method, direction, counterparty, ref, amount,
        expected, description, by, scenario="normal"):
    rows.append({
        "date": day.isoformat(), "time": time, "transaction_type": ttype,
        "payment_method": method, "direction": direction,
        "pay_source_recipient": counterparty, "reference": ref,
        "amount": f"{money(amount):.2f}", "expected_amount": f"{money(expected):.2f}",
        "description": description, "recorded_by": by, "scenario": scenario,
        "expected_outcome": OUTCOME.get(scenario, "investigate"),
        "approval_required": "yes" if expected > APPROVAL_LIMIT else "no"
    })


# normal activity
def build_normal(days, fee_days, shortfall_days):
    for day in days:
        factor = {5: 1.2, 6: 0.6}.get(day.weekday(), 1.0)       # Sat busy, Sun slow
        cash = max(20_000, rng.gauss(65_000, 12_000) * factor)
        card = max(30_000, rng.gauss(95_000, 18_000) * factor)
        tag = day.strftime("%Y%m%d")
        bank_day = next_business_day(day)

        add(day, clock(21, 21.75), "sale", "cash", "in", "Walk-in customers",
            f"CASH-{tag}", cash, cash, "Daily cash sales", rng.choice(["C01", "C02", "C03"]))
        add(day, clock(21, 21.75), "sale", "card", "in", "Walk-in customers",
            f"POS-{tag}", card, card, "Daily card sales", rng.choice(["C01", "C02", "C03"]))

        deposit = cash
        deposit_scenario = "normal"
        if day in shortfall_days:                 # cash goes missing before the bank
            deposit = cash * (1 - rng.uniform(0.12, 0.35))
            deposit_scenario = "unexplained_shortfall"
        add(bank_day, clock(10, 15), "bank_transfer", "cash", "in",
            "Own account (cash deposit)", f"CASH-{tag}", deposit, cash,
            "Cash deposit", "A01", deposit_scenario)

        expected_settlement = card * (1 - CARD_FEE_RATE)
        settlement = expected_settlement
        settle_scenario = "normal"
        if day in fee_days:                       # a bit more fee than expected
            settlement = expected_settlement * (1 - rng.uniform(0.005, 0.025))
            settle_scenario = "fee_difference"
        add(bank_day, clock(9, 11), "bank_transfer", "bank_transfer", "in",
            "PayGate Card Processor", f"POS-{tag}", settlement, expected_settlement,
            "Card settlement", "BANK", settle_scenario)


def build_supplier_payments(days):
    paid = []
    for day in days:
        if day.weekday() == 2:                    # supplier run every Wednesday
            for name in rng.sample(list(SUPPLIERS), rng.choice([2, 3])):
                mean, spread = SUPPLIERS[name]
                amount = max(5_000, rng.gauss(mean, spread))
                add(day, clock(10, 16), "supplier_payment", "bank_transfer", "out",
                    name, next_ref("SINV"), amount, amount,
                    "Supplier invoice payment", "A01")
                paid.append(rows[-1])
        if day.day == 1:
            add(day, clock(9, 10), "supplier_payment", "bank_transfer", "out",
                "Harbour Properties", f"RENT-{day.strftime('%Y%m')}", 250_000, 250_000,
                "Monthly shop rent", "A01")
    return paid


def build_normal_refunds(days):
    for day in rng.sample(days, 12):
        amount = rng.uniform(1_500, 6_000)
        add(day, clock(10, 19), "refund", rng.choice(["cash", "card"]), "out",
            "Customer refund", next_ref("REF"), amount, amount,
            "Customer refund - returned item", rng.choice(["C01", "C02"]))


# anomaly/potential fraud scenarios
def build_anomalies(days, weekdays, supplier_rows):
    # duplicate payment: same invoice paid twice a few days later
    eligible = [r for r in supplier_rows
                if datetime.fromisoformat(r["date"]).date() <= END - timedelta(days=4)
                and r["reference"].startswith("SINV")]
    for original in rng.sample(eligible, 4):
        later = datetime.fromisoformat(original["date"]).date() + timedelta(days=rng.randint(1, 3))
        add(later, clock(10, 16), "supplier_payment", "bank_transfer", "out",
            original["pay_source_recipient"], original["reference"],
            float(original["amount"]), 0.0, "Supplier invoice payment", "A01",
            "duplicate_payment")

    # payment with no invoice to a new payee
    for name in ["Apex Logistics Services", "Delta Facilities Ltd",
                 "QuickFix Maintenance", "Omega Consulting"]:
        add(rng.choice(weekdays), clock(10, 16), "supplier_payment", "bank_transfer",
            "out", name, "N/A", rng.uniform(40_000, 180_000), 0.0,
            "Service payment", "A01", "unmatched_payment")

    # very large transfers out, far above anything normal
    for name in ["Kestrel Holdings", "Ridgeway Ventures", "Unlisted Trading Co"]:
        add(rng.choice(weekdays), clock(11, 15), "bank_transfer", "bank_transfer",
            "out", name, next_ref("TRF"), rng.uniform(1_200_000, 3_500_000), 0.0,
            "Funds transfer", "A01", "large_transfer")

    # transfers in the middle of the night
    for name in ["Nova Capital Ltd", "Blue Harbour Traders", "Crestline Partners"]:
        add(rng.choice(weekdays), clock(1, 4.5), "bank_transfer", "bank_transfer",
            "out", name, next_ref("TRF"), rng.uniform(300_000, 900_000), 0.0,
            "Funds transfer", "A01", "off_hours_transfer")

    # several transfers just under the approval limit, same day
    for day in rng.sample(weekdays, 2):
        for slot in ("09:30", "11:15", "14:00"):
            add(day, slot, "bank_transfer", "bank_transfer", "out", "Zenith Ventures",
                next_ref("TRF"), rng.uniform(470_000, APPROVAL_LIMIT - 1_000), 0.0,
                "Funds transfer", "A01", "structuring")

    # refunds with no original sale, done by one cashier nearing closing time
    for day in rng.sample(days, 6):
        add(day, clock(20.5, 21.5), "refund", "cash", "out", "Customer refund",
            next_ref("REF"), rng.uniform(8_000, 22_000), 0.0,
            "Customer refund - returned item", "C03", "unauthorized_refund")


# main
def main():
    days = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    weekdays = [d for d in days if d.weekday() < 5]
    special = rng.sample(days[:-3], 15)          # keeping last days clear of bank lagging
    fee_days, shortfall_days = set(special[:10]), set(special[10:])

    build_normal(days, fee_days, shortfall_days)
    supplier_rows = build_supplier_payments(days)
    build_normal_refunds(days)
    build_anomalies(days, weekdays, supplier_rows)

    rows.sort(key=lambda r: (r["date"], r["time"]))     #  like a bank export
    for number, row in enumerate(rows, start=1):
        row["transaction_id"] = f"TXN{number:04d}"
    path = Path(__file__).resolve().parent.parent / "data" / "transactions.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} transactions to {path.name}")


if __name__ == "__main__":
    main()