**PURPOSE** 
This directory contains the Python scripts that make up the application's main functionality

**OVERVIEW**
**main.py**: 
This is where the user interacts with the application.It start the application, presents the menu and manages the navigation.

**data_manager.py**
This will load, save,retrieve and manage the record from the application's data files.
Data structures like dictionaries, lists and file handling techniques will be used to organise, retrieve and store records.

**transaction_monitor.py**
This script will be used to check financial records, match transactions and identifies and flag discrepancies.
Binary search logic will be used in locating a specific transaction or record efficiently, provided the records are sorted by the search key.
For example, searching for a transaction using the transaction ID.

**risk_analyser.py**
It applies the pre-defined risk rules, calculates risk scores and explains suspicious indicators.
This is where we use our control flows. The if, elif and else statements can be used to determine different outcomes.

For example:
*  If a payment matches the expected amount, mark it as satisfied.
*  If there's a small difference explained by processing fees, flag it for review or account for it.
*  If there's an unexplained discrepancy, flag it for investigation.



**DEVELOPMENT**
Datasets are being sourced for while working on the final SRS, implementtaions will follow.