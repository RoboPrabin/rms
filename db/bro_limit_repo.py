import pandas as pd
from db.db import get_connection

table_name = "bro_limit_test"
def get_bros():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, full_name
        FROM app_user
        WHERE role = 'BRO';
    """)
    bros = cur.fetchall()
    cur.close()
    conn.close()
    return bros

def get_all_bro_limits():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT b.username AS bro_code,
               b.full_name AS bro_name,
               bl.limit_value,
               m.username AS created_by_username,
               m.full_name AS created_by_name
        FROM app_user b
        LEFT JOIN {table_name} bl ON b.id = bl.bro_user_id
        LEFT JOIN app_user m ON bl.created_by = m.id
        WHERE b.role = 'BRO';
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    df = pd.DataFrame(rows, columns=['BRO CODE', 'FULL NAME', 'TOTAL LIMIT', 'CREATED BY', 'CREATED BY NAME'])
    df['FULL NAME'] = df['FULL NAME'].str.upper()
    df.drop(columns=['CREATED BY NAME'], inplace=True)
    df.sort_values(by='FULL NAME', inplace=True)
    df.reset_index(inplace=True, drop=True)
    df.index += 1
    return df


def update_bro_limit(bro_code: str, limit_amount: int, manager_id: str):
    conn = get_connection()
    cur = conn.cursor()

    # Normalize bro_code to uppercase
    bro_code = bro_code.upper()

    # Get bro_user_id from app_user (assuming bro_code maps to username or bro_code)
    cur.execute("""
        SELECT id
        FROM app_user
        WHERE UPPER(username) = %s AND role = 'BRO';
    """, (bro_code,))
    bro_row = cur.fetchone()

    if not bro_row:
        conn.close()
        raise ValueError(f"No BRO found with code {bro_code}")

    bro_user_id = bro_row[0]

    # Check if bro already has a limit record
    cur.execute(f"""
        SELECT bro_limit_id
        FROM {table_name}
        WHERE bro_user_id = %s;
    """, (bro_user_id,))
    exists = cur.fetchone()

    if exists:
        # Update existing record
        cur.execute(f"""
            UPDATE {table_name}
            SET limit_value = %s,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = %s
            WHERE bro_user_id = %s;
        """, (limit_amount, manager_id, bro_user_id))
    else:
        # Insert new record
        cur.execute(f"""
            INSERT INTO {table_name} 
                (bro_user_id, manager_id, limit_value, created_at, updated_at, created_by, updated_by)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s, %s);
        """, (bro_user_id, manager_id, limit_amount, manager_id, manager_id))

    conn.commit()
    cur.close()
    conn.close()