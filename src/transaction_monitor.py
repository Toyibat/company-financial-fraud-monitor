from datetime import datetime
from data_manager import id_key

def parse_id_number(text): 

    text = text.strip().upper()
    if text.startswith("TXN"):
        text = text[3:]
    return int(text) if text.isdigit() else None
def find_by_id(records, text):
    """ This should look up a transaction from what the user typed and return the record or None if its not found"""
    number = parse_id_number(text)
    if number is None:
        return None, 0
    index, comparisons = binary_search(records, number)
    return (records[index] if index >= 0 else None), comparisons