# This is the application entry point for the Financial Transaction Monitoring and Risk Analysis System
""" The responsibility of this main.py file is to start the application, log the admin in
,show the mainmenu, and manage the navigation on the app. 

 Note that each menu option points to a function in another module;
 data_manager.py will store, retrieve and manage transaction data.
 transaction_monitor.py will search using binary search and check transaction data.
 risk_analyzer.py will analyze the risk of transactions.
 dashboard.py will display transaction monitoring summaries.
 To add a feature later, write and create the module and add menuItem to menu below


"""

import getpass
import hashlib
import importlib
from dataclasses import dataclass,fields

APPTITLE = "Transaction Monitoring and Risk Analysis System"
LINE="=" * 60
MAX_LOGIN_ATEMPTS = 3

USERS = {
    "admin": hashlib.sha256(b"admin123").hexdigest(), # For demo purpose, the password is hashed using SHA-256 and admin123 is the placeholder password.
}

# FOR LOGGING IN
# This function authenticates the administrator before accessing the application, it will return true if the admin login is successful, otherwise it will return false. The admin has a maximum of 3 attempts to login before the application exits.
def login(session):
    print(f"\n{LINE}\n {APPTITLE} \n{LINE}\n Admin Login")

    for attempt in range(1,MAX_LOGIN_ATEMPTS + 1):
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ")

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        if username in USERS and USERS[username] == hashed_password:
            print(f"\n  Welcome, {username}.")
            session.user = username
            return True
        
            remaining = MAX_LOGIN_ATEMPTS - attempt
            print(f"login unsuccessful. Attempts left: {remaining}")
    print("\n  Too many failed attempts. Exiting.")
    return False

# FOR THE MENU

@dataclass (frozen=True)
class MenuItem:
    label: str
    module: str # the python file that has the feature.
    function: str # The function to be executed.
    need_record: bool = False # it could be true if the record is needed to be passed to the function. i.e if the function needs a transaction record to analyze, this will be set to True.

MENU={
    "1": MenuItem("Load transaction records", "data_manager", "load_transactions"),

    "2": MenuItem("Enter a new transaction", "data_manager", "add_transaction"),

    "3": MenuItem("Search transaction by ID", "transaction_monitor", "search_by_id", True),

    "4": MenuItem("Run transaction monitoring", "transaction_monitor", "run_monitoring", True),

    "5": MenuItem("Risk analysis report", "risk_analyzer", "risk_report", True),

    "6": MenuItem("Investigation dashboard", "dashboard", "show_dashboard", True),

    # For more feature (using RAG)"7": MenuItem("Investigation assistant (RAG)", "rag_assistant", "explain_flagged", True)
}
