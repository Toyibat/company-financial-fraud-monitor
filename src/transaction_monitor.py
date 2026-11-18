from datetime import datetime
from data_manager import id_key

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