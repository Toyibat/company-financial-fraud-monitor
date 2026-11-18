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