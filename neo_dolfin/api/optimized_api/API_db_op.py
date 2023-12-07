import sqlite3
from optimized_API import Core, Data
import os
from dotenv import load_dotenv
import json
import webbrowser
import pandas as pd

load_dotenv()
API_KEY = os.getenv("API_KEY")
api_key = API_KEY
core_instance = Core(api_key)
data_instance = Data()
access_token = core_instance.generate_auth_token()


# Operations specifically for interacting with the Dolfin Database
def init_dolfin_db():
    """
    Initialize the DolFin database and create user and transaction tables.
    Connects to the SQLite database and sets up foreign key constraints.
    Creates users and transactions tables if they don't exist.
    """
    try:
        with sqlite3.connect("dolfin_db.db") as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users
                (u_id INTEGER PRIMARY KEY AUTOINCREMENT,
                 email VARCHAR(255),
                 mobile VARCHAR(255),
                 first_name VARCHAR(255),
                 middle_name VARCHAR(255),
                 last_name VARCHAR(255),
                 password VARCHAR(255),
                 basiq_id VARCHAR(255) DEFAULT NULL);
            ''')
            cursor.execute('''
                            CREATE TABLE IF NOT EXISTS transactions
                            (id VARCHAR(255) PRIMARY KEY,
                             type VARCHAR(50),
                             status VARCHAR(50),
                             description TEXT,
                             amount REAL,
                             account VARCHAR(255),
                             balance REAL,
                             direction VARCHAR(50),
                             class VARCHAR(50),
                             institution VARCHAR(50),
                             postDate TIMESTAMP,
                             subClass_title VARCHAR(255),
                             subClass_code VARCHAR(50),
                             trans_u_id INTEGER NOT NULL,
                             FOREIGN KEY (trans_u_id) REFERENCES users (u_id) ON DELETE CASCADE ON UPDATE CASCADE);
                        ''')
            return "managed to init dolfin_db."
    except sqlite3.Error as e:
        return "An error occurred: " + str(e)


def register_user(email, mobile, first_name, middle_name, last_name, password):
    """
    Registers a new DolFin user.
    Inserts user information into the users table.
    Parameters include email, mobile number, first name, middle name, last name, and password.
    """
    try:
        with sqlite3.connect("dolfin_db.db") as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO users (email, mobile, first_name, middle_name, last_name, password)
                              VALUES (?, ?, ?, ?, ?, ?)''',
                           (email, mobile, first_name, middle_name, last_name, password))
            conn.commit()
            return "User inserted successfully into 'users' table."
    except sqlite3.Error as e:
        return "An error occurred: " + str(e)


def get_basiq_id(user_id):
    """
    Retrieves the basiq ID for a specific DolFin user.
    Queries the users table for the basiq ID based on the user ID.
    """
    try:
        with sqlite3.connect("dolfin_db.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT basiq_id FROM users WHERE u_id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return "No user found with the given ID."
    except sqlite3.Error as e:
        return "An error occurred: " + str(e)


def get_user_info(user_id):
    """
    Retrieves information of a DolFin user.
    Queries for basic information of a user by user ID, including email, mobile, first name, middle name, and last name.
    """
    try:
        with sqlite3.connect("dolfin_db.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT email, mobile, first_name, middle_name, last_name FROM users WHERE u_id = ?",
                           (user_id,))
            result = cursor.fetchone()
            if result:
                user_info = {
                    "email": result[0],
                    "mobile": result[1],
                    "firstName": result[2],
                    "middleName": result[3],
                    "lastName": result[4]
                }
                return user_info
            else:
                return "No user found with the given ID."
    except sqlite3.Error as e:
        return "An error occurred: " + str(e)


def register_basiq_id(user_id):
    """
    Registers a basiq ID for a DolFin user.
    Generates a basiq ID based on user information and updates the basiq ID field in the users table.
    """
    try:
        new_basiq_id = json.loads(core_instance.create_user_by_dict(get_user_info(user_id), access_token)).get('id')
        with sqlite3.connect("dolfin_db.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET basiq_id = ? WHERE u_id = ?", (new_basiq_id, user_id))
            if cursor.rowcount == 0:
                return "No user found with the given ID."
            conn.commit()
            return "basiq_id updated successfully for user ID {}".format(user_id)
    except sqlite3.Error as e:
        return "An error occurred: " + str(e)


def link_bank_account(user_id):
    """
    Link a DolFin user to their bank accounts.
    Generates an authorization link based on the user's basiq ID and opens it in a web browser.
    """
    try:
        with sqlite3.connect("dolfin_db.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT basiq_id FROM users WHERE u_id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                link = json.loads(core_instance.create_auth_link(result[0], access_token)).get('links').get('public')
                webbrowser.open(link)
            else:
                return "No user found with the given ID."
    except sqlite3.Error as e:
        return "An error occurred: " + str(e)


def request_transactions_df(user_id, limit_para=500, filter_para=''):
    """
    Requests and returns user transaction data in DataFrame format.
    Fetches the transaction list based on the user's basiq ID and converts it into a DataFrame.
    """
    tran_data = json.loads(
        data_instance.get_transaction_list(get_basiq_id(user_id), limit_para, filter_para, access_token))
    transaction_list = tran_data['data']
    transactions = []
    for transaction in transaction_list:
        transaction = {
            'type': transaction['type'],
            'id': transaction['id'],
            'status': transaction['status'],
            'description': transaction['description'],
            'amount': transaction['amount'],
            'account': transaction['account'],
            'balance': transaction['balance'],
            'direction': transaction['direction'],
            'class': transaction['class'],
            'institution': transaction['institution'],
            'postDate': transaction['postDate'],
            'subClass_title': transaction['subClass']['title'] if transaction.get('subClass') else None,
            'subClass_code': transaction['subClass']['code'] if transaction.get('subClass') else None
        }
        transactions.append(transaction)
    transaction_df = pd.DataFrame(transactions)
    return transaction_df


def cache_transactions(user_id, tran_data):
    """
    Caches transaction data for a Dolfin user.
    Inserts transaction data into the transactions table, including transaction ID, type, status, description, etc.
    """
    try:
        with sqlite3.connect("dolfin_db.db") as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            cursor = conn.cursor()
            insert_statement = '''
                INSERT INTO transactions (id, type, status, description, amount, account, balance, direction, class, institution, postDate, subClass_title, subClass_code, trans_u_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            for index, row in tran_data.iterrows():
                cursor.execute(insert_statement, (
                    row['id'], row['type'], row['status'], row['description'], row['amount'],
                    row['account'], row['balance'], row['direction'], row['class'], row['institution'],
                    row['postDate'], row['subClass_title'], row['subClass_code'], user_id))

        return "Transactions successfully inserted."

    except sqlite3.Error as e:
        return "An error occurred: " + str(e)


def fetch_transactions_by_user(user_id):
    """
    Fetches cached transaction data based on the user ID.
    Queries the transactions table for all transaction information for a specific user.
    """
    try:
        with sqlite3.connect("dolfin_db.db") as conn:
            query = "SELECT * FROM transactions WHERE trans_u_id = ?"
            return pd.read_sql_query(query, conn, params=(user_id,))
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")


def clear_transactions():
    """
    Clears all cached data from the transactions table.
    Deletes all records from the transactions table.
    """
    try:
        # Database connection
        with sqlite3.connect("dolfin_db.db") as conn:
            cursor = conn.cursor()
            # SQL statement to delete all data from the transactions table
            cursor.execute("DELETE FROM transactions;")
        return "Transactions table cleared successfully."
    except sqlite3.Error as e:
        return "An error occurred: " + str(e)