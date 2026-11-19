
from transaction_monitor import find_by_id, run_checks

LEVELS = [(80, "Critical"), (60, "High"), (40, "Medium"), (0, "Low")]
INDICATORS = {
    "amount_mismatch": (None, "Amount differs from expected"),
    "no_expected_record": (45, "Nothing in the books explains this amount"),
    "large_amount": (70, "Amount is significantly above the norm"),
    "off_hours": (50, "Transaction occurred outside business hours"),
    "split_below_limit": (50, "Multiple transfers just under approval limit")
}
