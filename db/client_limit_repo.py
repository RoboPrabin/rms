import pandas as pd
from db.db import get_connection
from psycopg2 import sql


table_name = "bro_limit"
def get_clients_by_rm(rm_name):
    conn = get_connection()
    query = sql.SQL("""
        SELECT "rmName","clientCode", "clientName", category, credit_limit, trading_limit
        FROM client_rm_map
        WHERE "rmName" = %s
    """)
    
    with conn.cursor() as cur:
        cur.execute(query, (rm_name,))
        rows = cur.fetchall()
    
    conn.close()
    return rows

def get_all_clients():
    conn = get_connection()
    query = sql.SQL("""
        SELECT "rmName","clientCode", "clientName", category, credit_limit, trading_limit
        FROM client_rm_map
    """)
    
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    conn.close()
    return rows



def get_loggedin_bro_limits(bro_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT b.username,
               b.full_name,
               bl.limit_value
        FROM app_user b
        LEFT JOIN {table_name} bl ON b.id = bl.bro_user_id
        WHERE b.id = %s AND b.role = 'BRO';
    """, (bro_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None  # No bro found with this id

    # Build DataFrame for consistency with your other functions
    df = pd.DataFrame([row], columns=['BRO CODE', 'FULL NAME', 'TOTAL LIMIT'])
    df['FULL NAME'] = df['FULL NAME'].str.upper()
    df.reset_index(inplace=True, drop=True)
    df['TOTAL LIMIT'] = df['TOTAL LIMIT'].apply(lambda x: f"{x:,}" if x is not None else 0)  # Format with commas
    df.index += 1
    return df
    

def update_client_limit(client_code: str, limit_amount: int, category: str, updated_by: str):
    conn = get_connection()
    cur = conn.cursor()

    # Normalize client_code to uppercase for consistency
    client_code = client_code.upper()

    # Update directly — no insert if not found
    cur.execute("""
        UPDATE client_rm_map
        SET trading_limit = %s,
            updated_at = CURRENT_TIMESTAMP,
            category = %s,
            updated_by = %s
        WHERE UPPER("clientCode") = %s;
    """, (limit_amount, category, updated_by, client_code))

    conn.commit()
    cur.close()
    conn.close()
