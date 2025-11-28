

#db.py
from psycopg2 import sql
import psycopg2
import psycopg2.extras
import pandas as pd
from utils import helper
from psycopg2.extras import execute_batch
from datetime import datetime


def get_connection():
    return psycopg2.connect(
        host="localhost",
        dbname="client_holdings",
        user="postgres",
        password="admin",
        cursor_factory=psycopg2.extras.DictCursor
    )



def get_table_holdings_in_df():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM holdings;")
        rows = cur.fetchall()

        # Read column names
        cols = [desc[0] for desc in cur.description]

        # Build DataFrame
        df = pd.DataFrame(rows, columns=cols)
        return df
    finally:
        conn.close()



def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM app_user WHERE username = %s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_meroshare_accounts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM meroshare_acc")
    rows = cur.fetchall()

    # Get column names from cursor description
    columns = [desc[0] for desc in cur.description]

    cur.close()
    conn.close()

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=columns)
    return df


def has_given_feedback(bro: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    # Check if rating_given is true for this bro
    cur.execute("SELECT 1 FROM feedback WHERE bro = %s AND rating_given = TRUE", (bro,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None


def has_given_remarks(bro: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    # Check if remarks_given is true for this bro
    cur.execute("SELECT 1 FROM feedback WHERE bro = %s AND remarks_given = TRUE", (bro,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None


def save_feedback(bro: str, star: int, remarks: str = "") -> None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO feedback (id, bro, star, remarks, rating_given, remarks_given)
            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s)
            ON CONFLICT (bro)
            DO UPDATE SET 
                star = EXCLUDED.star,
                remarks = EXCLUDED.remarks,
                rating_given = EXCLUDED.rating_given,
                remarks_given = EXCLUDED.remarks_given
            WHERE feedback.bro = EXCLUDED.bro;
            """,
            (bro, star, remarks.strip(), True, bool(remarks.strip()))
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def change_password(username: str, current_password: str, new_password: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 1) Check if current password is correct
        cur.execute(
            """
            SELECT password 
            FROM app_user 
            WHERE username = %s;
            """,
            (username.lower().strip(),)
        )
        row = cur.fetchone()

        if not row:
            return False  # user not found

        stored_password = row[0]

        if stored_password != current_password:
            return False  # invalid current password

        # 2) Update the password
        cur.execute(
            """
            UPDATE app_user
            SET password = %s
            WHERE username = %s;
            """,
            (new_password, username.lower().strip())
        )
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()


def change_user_info(username: str, password:str, phone: str, email: str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Update the user information
        cur.execute(
            """
            UPDATE app_user
            SET password = %s, phone = %s, email = %s
            WHERE username = %s;
            """,
            (password.strip(), phone.strip(), email.strip(), username.lower().strip())
        )
        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e

    finally:
        cur.close()
        conn.close()



def ensure_holdings_columns_exist():
    column_types = {
        "pendingWaccValuation": "NUMERIC",
        "pendingWaccTotalQuantity": "NUMERIC",
        "totalPurchaseCost": "NUMERIC",
        "calculatedWacc": "NUMERIC",
        "ltp": "NUMERIC",
        "marketValue": "NUMERIC",
        "averageBrokerCommission": "NUMERIC",
        "sebon": "NUMERIC",
        "dpFee": "NUMERIC",
        "capitalGain": "NUMERIC",
        "estimatedCapitalGainTax": "NUMERIC",
        "profitLoss": "NUMERIC",
        "profitLossPercentage": "NUMERIC",
        "lastUpdated": "TIMESTAMP"     # ← FIXED HERE
    }

    conn = get_connection()
    cursor = conn.cursor()

    try:
        for col, coltype in column_types.items():
            alter_sql = f'''
                ALTER TABLE holdings 
                ADD COLUMN IF NOT EXISTS "{col}" {coltype};
            '''
            cursor.execute(alter_sql)

        conn.commit()
        # print("[Column Check] All required columns verified/created.")

    except Exception as e:
        conn.rollback()
        # print("Column creation failed:", str(e))
        raise

    finally:
        cursor.close()
        conn.close()

def update_holdings_in_db(df):
    update_query = """
        UPDATE holdings
        SET 
            "pendingWaccValuation" = %s,
            "pendingWaccTotalQuantity" = %s,
            "totalPurchaseCost" = %s,
            "calculatedWacc" = %s,
            "ltp" = %s,
            "marketValue" = %s,
            "averageBrokerCommission" = %s,
            "sebon" = %s,
            "dpFee" = %s,
            "capitalGain" = %s,
            "estimatedCapitalGainTax" = %s,
            "profitLoss" = %s,
            "profitLossPercentage" = %s,
            "lastUpdated" = %s
        WHERE boid = %s AND script = %s
    """

    conn = get_connection()
    cursor = conn.cursor()

    try:
        records = []
        for _, row in df.iterrows():
            records.append((
                row["pendingWaccValuation"],
                row["pendingWaccTotalQuantity"],
                row["totalPurchaseCost"],
                row["calculatedWacc"],
                row["ltp"],
                row["marketValue"],
                row["averageBrokerCommission"],
                row["sebon"],
                row["dpFee"],
                row["capitalGain"],
                row["estimatedCapitalGainTax"],
                row["profitLoss"],
                row["profitLossPercentage"],
                row["lastUpdated"],
                row["boid"],        # WHERE clause
                row["script"]       # WHERE clause
            ))

        psycopg2.extras.execute_batch(cursor, update_query, records)
        conn.commit()
        # print("[999999999] PostgreSQL updated successfully.")

    except Exception as e:
        conn.rollback()
        # print("DB update failed:", str(e))
        raise

    finally:
        cursor.close()
        conn.close()

def update_meroshare_accounts_status(df_client_data: pd.DataFrame):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                for _, row in df_client_data.iterrows():
                    cur.execute("""
                        UPDATE meroshare_acc
                        SET 
                            login_message = %s,
                            password_expired = %s,
                            account_expired = %s,
                            demat_expired = %s
                        WHERE username = %s;
                    """, (
                        row['login_message'],
                        row['password_expired'],
                        row['account_expired'],
                        row['demat_expired'],
                        row['username']
                    ))
        helper.show_message("[DB] Meroshare_acc updated successfully.", color='green')
        print("\n")
    finally:
        conn.close()



def update_ledger_table(df: pd.DataFrame, table_name: str = "holdings"):
    """
    Updates the 'holding' table in PostgreSQL with ledgerBalance, clientCode, ledgerFetched
    based on BOID from the given DataFrame.
    """
    conn = get_connection()  # your existing connection function
    update_query = sql.SQL("""
        UPDATE {table}
        SET
            "ledgerBalance" = %s,
            "clientCode" = %s,
            "ledgerFetched" = %s
        WHERE "boid" = %s
    """).format(table=sql.Identifier(table_name))

    # Prepare data for batch update
    update_data = [
        (row['ledgerBalance'], row['clientCode'], row['ledgerFetched'], row['boid'])
        for _, row in df.iterrows()
    ]

    try:
        with conn.cursor() as cur:
            execute_batch(cur, update_query, update_data)
        conn.commit()
        # helper.show_message(f"✅ Table '{table_name}' updated successfully with {len(update_data)} records.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to update table '{table_name}': {e}")
    finally:
        conn.close()


def update_login_status(username: str, success: bool) -> int:
    """
    Update login status for a user.
    Returns remaining attempts if failed login.
    """
    MAX_ATTEMPTS = 3
    now = datetime.now()
    conn = get_connection()
    remaining = 0
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if success:
                    cur.execute("""
                        UPDATE app_user
                        SET failed_attempts = 0,
                            last_failed_at = NULL,
                            status = 'ACTIVE'
                        WHERE username = %s
                    """, (username,))
                else:
                    # increment failed attempts
                    cur.execute("""
                        UPDATE app_user
                        SET failed_attempts = failed_attempts + 1,
                            last_failed_at = %s,
                            status = CASE
                                WHEN failed_attempts + 1 >= 3 THEN 'BLOCKED'
                                ELSE status
                            END,
                            blocked_at = CASE
                                WHEN failed_attempts + 1 >= 3 THEN %s
                                ELSE blocked_at
                            END
                        WHERE username = %s
                        RETURNING failed_attempts
                    """, (now, now, username))
                    row = cur.fetchone()
                    if row:
                        remaining = MAX_ATTEMPTS - row["failed_attempts"]
                        remaining = max(remaining, 0)
    finally:
        conn.close()
    return remaining


def create_session(username: str) -> str:
    """
    Create a new user session or update an existing session for the given username.
    Returns the session UUID as a string.
    """
    session_id = None
    conn = get_connection()
    now = datetime.now()
    ip_address = helper.get_client_ip()
    user_agent = helper.get_user_agent()
    
    try:
        with conn:
            with conn.cursor() as cur:
                # Check if a session exists for this username
                cur.execute("""
                    SELECT id FROM user_session
                    WHERE LOWER(username) = %s
                    LIMIT 1
                """, (username.lower(),))
                row = cur.fetchone()
                
                if row:
                    # Update existing session
                    session_id = row[0]
                    cur.execute("""
                        UPDATE user_session
                        SET login_time = %s,
                            ip_address = %s,
                            user_agent = %s,
                            session_status = 'ACTIVE'
                        WHERE id = %s
                    """, (now, ip_address, user_agent, session_id))
                else:
                    # Insert new session
                    cur.execute("""
                        INSERT INTO user_session (username, login_time, session_status, ip_address, user_agent)
                        VALUES (%s, %s, 'ACTIVE', %s, %s)
                        RETURNING id
                    """, (username.lower(), now, ip_address, user_agent))
                    row = cur.fetchone()
                    if row:
                        session_id = row[0]
    finally:
        conn.close()
    
    return str(session_id)  # Return UUID as string



def end_session(username: str):
    """
    Mark all active sessions of the given username as logged out.
    """
    conn = get_connection()
    now = datetime.now()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_session
                    SET logout_time = %s,
                        session_status = 'LOGGED_OUT'
                    WHERE LOWER(username) = %s
                      AND session_status = 'ACTIVE'
                    RETURNING id
                """, (now, username.lower()))
                cur.fetchall()
    finally:
        conn.close()

