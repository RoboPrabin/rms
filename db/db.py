
#db.py
import ast
import json
import uuid
from psycopg2 import sql
import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_batch, execute_values
import pandas as pd
from utils import helper
from datetime import datetime, timedelta, date
import os

def get_connection():
    return psycopg2.connect(
        host="172.17.26.6",
        # host="localhost",
        dbname="rms",
        user="postgres",
        password="admin",
        cursor_factory=psycopg2.extras.DictCursor
    )


def fetch_category_client_data():
    query = """
        WITH due_list_parsed AS (
            SELECT
                *,
                TO_TIMESTAMP("uploaded_at", 'YYYY-MM-DD HH12:MI:SS AM') AS uploaded_at_ts
            FROM due_list
            WHERE "uploaded_at" IS NOT NULL
              AND TRIM("uploaded_at") <> ''
        ),
        due_list_filtered AS (
            SELECT *
            FROM due_list_parsed
            WHERE uploaded_at_ts::date = CURRENT_DATE
              AND (
                    (
                        EXISTS (
                            SELECT 1
                            FROM due_list_parsed
                            WHERE uploaded_at_ts::date = CURRENT_DATE
                              AND uploaded_at_ts::time > TIME '12:00:00'
                        )
                        AND uploaded_at_ts::time > TIME '12:00:00'
                    )
                    OR
                    (
                        NOT EXISTS (
                            SELECT 1
                            FROM due_list_parsed
                            WHERE uploaded_at_ts::date = CURRENT_DATE
                              AND uploaded_at_ts::time > TIME '12:00:00'
                        )
                    )
              )
        ),
        latest_due_list AS (
            SELECT DISTINCT ON ("clientCode")
                "clientCode",
                "adjustedBalance",
                "uploaded_at",
                uploaded_at_ts
            FROM due_list_filtered
            ORDER BY "clientCode", uploaded_at_ts DESC
        )
        SELECT
            crm."rmName",
            crm."rmFullName",
            crm."clientName",
            crm."clientCode",
            crm."category",
            crm."trading_limit",
            COALESCE(ldl."adjustedBalance", 0) AS "adjustedBalance",
            ldl."uploaded_at" AS "due_uploaded_at",
            ldl.uploaded_at_ts AS "due_uploaded_at_ts"
        FROM client_rm_map crm
        LEFT JOIN latest_due_list ldl
            ON crm."clientCode" = ldl."clientCode";
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
            columns = [desc.name for desc in cur.description]

        return pd.DataFrame(results, columns=columns)

    finally:
        conn.close()

# def fetch_category_client_data():
#     query = """
#     WITH has_after AS (
#         SELECT 1
#         FROM due_list
#         WHERE updated_at::date = CURRENT_DATE
#           AND updated_at::time > TIME '12:00:00'
#         LIMIT 1
#     )
#     SELECT 
#         crm."rmName" AS RM,
#         COUNT(DISTINCT crm."clientCode") AS "TOTAL CLIENTS",
#         SUM(CASE WHEN crm.category = 'CASH' THEN crm.adjustedBalance ELSE 0 END) AS CASH,
#         SUM(CASE WHEN crm.category = 'T+2' THEN crm.adjustedBalance ELSE 0 END) AS "T+2",
#         SUM(CASE WHEN crm.category = 'DUE' THEN crm.adjustedBalance ELSE 0 END) AS DUE,
#         SUM(CASE WHEN crm.category = 'MTF' THEN crm.adjustedBalance ELSE 0 END) AS MTF,
#         SUM(CASE WHEN crm.category IS NULL THEN crm.adjustedBalance ELSE 0 END) AS UNCATEGORIZED,
#         SUM(crm.adjustedBalance) AS "TOTAL ADJUSTED BALANCE"
#     FROM (
#         SELECT 
#             crm.*,
#             COALESCE(dl."adjustedBalance", 0) AS adjustedBalance
#         FROM client_rm_map crm
#         LEFT JOIN due_list dl
#             ON crm."clientCode" = dl."clientCode"
#            AND dl.updated_at::date = CURRENT_DATE
#            AND (
#                 (EXISTS (SELECT 1 FROM has_after) AND dl.updated_at::time > TIME '12:00:00')
#              OR (NOT EXISTS (SELECT 1 FROM has_after) AND dl.updated_at::time < TIME '12:00:00')
#            )
#     ) crm
#     GROUP BY crm."rmName"
#     ORDER BY crm."rmName";
#     """

#     conn = get_connection()
#     with conn.cursor() as cur:
#         cur.execute(query)
#         results = cur.fetchall()  # list of DictRow objects
#     conn.close()

#     # Convert to DataFrame for Streamlit display
#     df = pd.DataFrame(results, columns=[desc.name for desc in cur.description])
#     return df




# def fetch_category_client_data():
#     query = """
#         SELECT 
#             crm.*,
#             COALESCE(dl."adjustedBalance", 0) AS adjustedBalance
#         FROM client_rm_map crm
#         LEFT JOIN due_list dl
#             ON crm."clientCode" = dl."clientCode"
#            AND dl.updated_at::time < TIME '12:00:00'
#            AND dl.updated_at::date = CURRENT_DATE;
#     """
#     conn = get_connection()
#     df = pd.read_sql(query, conn)
#     conn.close()
#     return df




def fetch_clients_category():
    query = """SELECT "clientName", "clientCode", category, credit_limit FROM client_rm_map WHERE category IS NOT NULL"""
    
    try:
        # Establish connection
        conn = get_connection()
        
        with conn.cursor() as cur:
            cur.execute(query)
            # Fetch all rows as a list of DictRow objects
            results = cur.fetchall()
            return results
           
                
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to database: {e}")


# def get_latest_holdings_dpm3():
#     query = """select * from dpm3 where "FREE BALANCE" != '0'"""
    
#     try:
#         # Establish connection
#         conn = get_connection()
        
#         # Use cursor with column names
#         with conn.cursor() as cur:
#             cur.execute(query)
#             results = cur.fetchall()
            
#             # Extract column names from cursor description
#             colnames = [desc[0] for desc in cur.description]
            
#             # Convert to DataFrame
#             df = pd.DataFrame(results, columns=colnames)
#             return df
        
#         conn.close()
        
#     except Exception as e:
#         print(f"Error connecting to database: {e}")
#         return None


# def get_latest_holdings_dpm3():
#     query = """
#         SELECT d.*,
#             a."closePrice",
#             a.updated_at
#         FROM dpm3 d
#         LEFT JOIN average_price a
#         ON d."SCRIPT" = a."symbol"
#         WHERE d."FREE BALANCE" != '0'
#     """
    
#     try:
#         conn = get_connection()
        
#         with conn.cursor() as cur:
#             cur.execute(query)
#             results = cur.fetchall()
            
#             # Extract column names from cursor description
#             colnames = [desc[0] for desc in cur.description]
            
#             # Convert to DataFrame
#             df = pd.DataFrame(results, columns=colnames)
        
#         conn.close()
#         return df
    
#     except Exception as e:
#         print(f"Error connecting to database: {e}")
#         return None



def get_latest_holdings_dpm3():
    query = """
        SELECT d.*,
               a."closePrice",
               a.updated_at,
               COALESCE(c."rmName", 'N/A') AS "rmName"
        FROM dpm3 d
        LEFT JOIN average_price a
               ON d."SCRIPT" = a."symbol"
        LEFT JOIN client_rm_map c
               ON d."CLIENT CODE" = c."clientCode"
        WHERE d."FREE BALANCE" != '0'
    """
    
    try:
        conn = get_connection()
        
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
            
            # Extract column names from cursor description
            colnames = [desc[0] for desc in cur.description]
            
            # Convert to DataFrame
            df = pd.DataFrame(results, columns=colnames)
        
        conn.close()
        return df
    
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None
    

    

def get_dpm3_onhold():
    query = """
       select * from dpm3_onhold;
    """
    
    try:
        conn = get_connection()
        
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
            
            # Extract column names from cursor description
            colnames = [desc[0] for desc in cur.description]
            
            # Convert to DataFrame
            df = pd.DataFrame(results, columns=colnames)
        
        conn.close()
        return df
    
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None


def fetch_trade_book_test():
    query = """SELECT "clientName", "clientMemberCode" ,"buy/sell", "sellAmount" 
            FROM trade_book 
            WHERE "buy/sell" = 'SELL' OR "buy/sell" = 'BOTH';"""
                
    try:
        # Establish connection
        conn = get_connection()
        
        with conn.cursor() as cur:
            cur.execute(query)
            # Fetch all rows as a list of DictRow objects
            results = cur.fetchall()
            return results
           
                
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to database: {e}")


def insert_to_dpm3_bulk(df: pd.DataFrame):
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Define the query WITHOUT the "VALUES" part (execute_values handles that)
    insert_query = """
        INSERT INTO dpm3 (
            "CLIENT CODE", 
            "CLIENT NAME", 
            "SCRIPT", 
            "FREE BALANCE", 
            "CLOSING PRICE", 
            "FREE SHARE VALUATION", 
            "BRANCH"
        ) VALUES %s
    """

    # 2. Convert DataFrame rows into a list of tuples
    # Ensure the order here matches the column order in the INSERT statement above
    data_to_insert = [
        (
            row['CLIENT CODE'],
            row['CLIENT NAME'],
            row['SCRIPT'],
            row['QUANTITY'], 
            row['RATE'],     
            row['AMOUNT'],   
            row['BRANCH']
        ) 
        for row in df.to_dict('records')
    ]

    try:
        # 3. Use execute_values for high-speed insertion
        execute_values(cur, insert_query, data_to_insert)
        
        conn.commit()
        print(f"Bulk insert successful: {len(df)} rows added to dpm3.")
        
    except Exception as e:
        conn.rollback()
        print(f"Bulk insert failed: {e}")
    finally:
        cur.close()
        conn.close()


def get_floorsheet_from_date(target_date):
    """
    Fetch all rows from floorsheet where uploaded_at::date >= target_date
    target_date: string 'YYYY-MM-DD' or date object
    """
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    query = """
        SELECT clientcode, clientname, symbol, quantity, rate, amount, transaction_type, branch, uploaded_at
        FROM floorsheet
        WHERE uploaded_at::date >= %s
        AND transaction_type = 'Buy'
        ORDER BY uploaded_at DESC;
    """

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, (target_date,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows  # list of dicts (DictCursor)
    except Exception as e:
        print("Error:", e)
        return []
    

def get_tms_limit_report():
    conn = get_connection()
    cur = conn.cursor()

    # Run query
    cur.execute("SELECT * FROM zlog_tms_limit order by created_date_time desc")

    # Fetch all rows
    rows = cur.fetchall()

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])

    cur.close()
    conn.close()

    return df



def insert_client_comm(client_code, client_name, action_type, created_by,
                       comm_date=None, comm_time=None, 
                       script=None, remarks=None):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Generate UUID for id

        insert_query = """
            INSERT INTO client_comm (
                client_code, client_name, comm_date, comm_time, script, remarks, action_type, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cur.execute(insert_query, (
            client_code,
            client_name,
            comm_date,
            comm_time,
            script,
            remarks,
            action_type,
            created_by
        ))

        conn.commit()

        cur.close()
    except Exception as e:
        print("Error inserting record:", e)
    finally:
        if conn:
            conn.close()


def get_client_comm_report_by_bro(rm_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT client_code, client_name, script, comm_date, comm_time,action_type, remarks, created_by FROM client_comm WHERE created_by = %s",
        (rm_name,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_all_client_comm_report():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT client_code, client_name, script, comm_date, comm_time,action_type, remarks, created_by FROM client_comm order by created_date_time desc")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows



def update_kyc_branch(client_code: str, new_branch: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE kyc SET clientbranch = %s WHERE clientmembercode = %s",
        (new_branch, client_code)
    )
    conn.commit()
    cur.close()
    conn.close()


def insert_client_remark(client_code, client_name, remarks, created_by):
    conn = get_connection()
    try:
        query = """
            INSERT INTO client_remarks (
                client_code, client_name, remarks, created_at, created_by
            )
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
            RETURNING id;
        """
        with conn.cursor() as cur:
            cur.execute(query, (client_code, client_name, remarks, created_by))
            new_id = cur.fetchone()[0]  # get the UUID of the inserted row
        conn.commit()
        return new_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_client_remarks():
    conn = get_connection()
    try:
        query = """
            SELECT client_code, client_name, remarks, created_at ,created_by
            FROM client_remarks
            ORDER BY created_at DESC;
        """
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query)
            rows = cur.fetchall()
        return rows
    finally:
        conn.close()


def upsert_tms_session(cookies, session_id, created_by=None, updated_by=None):
    cookies_str = json.dumps(cookies) if isinstance(cookies, dict) else str(cookies)
    session_id_str = str(session_id)
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Try to update the single row
        cur.execute(
            """
            UPDATE tms_session
            SET cookies = %s,
                session_id = %s,
                updated_at = %s,
                updated_by = %s
            WHERE TRUE;  -- since only one row exists
            """,
            (cookies_str, session_id_str, datetime.now(), updated_by)
        )
        updated_count = cur.rowcount

        # If no row exists, insert one
        if updated_count == 0:
            cur.execute(
                """
                INSERT INTO tms_session (cookies, session_id, created_at, created_by)
                VALUES (%s, %s, %s, %s);
                """,
                (cookies_str, session_id_str, datetime.now(), created_by)
            )
            updated_count = cur.rowcount

        conn.commit()
    finally:
        cur.close()
        conn.close()

    return updated_count


def get_tms_session():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT cookies, session_id FROM tms_session LIMIT 1;")
        row = cur.fetchone()
        if row:
            cookies_raw, session_id = row

            # If cookies_raw is stored as a Python list string, parse it
            try:
                cookies_list = ast.literal_eval(cookies_raw)
            except Exception:
                cookies_list = cookies_raw  # fallback if already a list

            # Build dict keyed by cookie name
            cookies_dict = {
                cookie["name"]: cookie["value"]
                for cookie in cookies_list
                if cookie.get("name") in ["XSRF-TOKEN", "_aid", "_rid"]
            }
            session_set = ast.literal_eval(session_id)
            session_id = next(iter(session_set))
            return cookies_dict, session_id
        else:
            return None, None
    finally:
        cur.close()
        conn.close()



def update_limits(client_code, credit_limit, trading_limit, updated_by):
    conn = get_connection()
    cur = conn.cursor()
    query = sql.SQL("""
        UPDATE client_rm_map
        SET credit_limit = %s,
            trading_limit = %s,
            updated_by = %s,
            updated_at = %s
        WHERE "clientCode" = %s
    """)
    
    with conn.cursor() as cur:
        cur.execute(query, (
            credit_limit,
            trading_limit,
            updated_by,
            datetime.now(),
            client_code
        ))
        conn.commit()




def get_clients_by_rm_for_client_comm(rm_name):
    conn = get_connection()
    query = sql.SQL("""
        SELECT "clientCode", "clientName"
        FROM client_rm_map
        WHERE "rmName" = %s
    """)
    
    with conn.cursor() as cur:
        cur.execute(query, (rm_name,))
        rows = cur.fetchall()
    
    conn.close()
    return rows

def get_clients_for_client_comm():
    conn = get_connection()
    query = sql.SQL("""
        SELECT "clientCode", "clientName"
        FROM client_rm_map order by "clientName" asc
    """)
    
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
    
    conn.close()
    return rows






def update_restrict_company(client_code: str, updated_by:str ,restrict_company):
    query = """
        UPDATE transaction_monitor
        SET restrict_company = %s,
            updated_by = %s
        WHERE client_code = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            if restrict_company == None:
                companies = None
            else:
                companies = ",".join(restrict_company)
            cursor.execute(query, (companies, updated_by ,client_code))
        conn.commit()

def update_client_info_aml(client_name: str, company:str, occupation:str, updated_by:str, client_code:str):
    query = """
        UPDATE transaction_monitor
        SET client_name = %s,
            company = %s,
            occupation = %s,
            updated_by = %s

        WHERE client_code = %s;
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            if occupation == "":
                occupation = None
            if company == "":
                company = None

            cursor.execute(query, (client_name, company, occupation ,updated_by,client_code))
        conn.commit()

def get_restricted_scripts(client_code: str) -> list[str]:
    """
    Fetch restricted scripts for a given client from DB (Postgres, camelCase columns).
    Returns a list of strings in format "SYMBOL - SecurityName".
    """
    query = """
        SELECT ap."symbol", ap."securityName"
        FROM "transaction_monitor" tm
        JOIN "average_price" ap 
            ON ap."symbol" = ANY(string_to_array(tm."restrict_company", ','))
        WHERE tm."client_code" = %s
    """
    
    with get_connection() as conn:  # Replace with your actual DB connection handler
        with conn.cursor() as cursor:
            cursor.execute(query, (client_code,))
            rows = cursor.fetchall()
    
    # Format as "SYMBOL - SecurityName"
    return [f"{symbol} - {name}" for symbol, name in rows]

def get_aml_transaction_data():
    query = "SELECT client_code, client_name, occupation, company, restrict_company, flag from transaction_monitor ORDER BY client_code ASC;"
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()  # empty DataFrame if no records

            # Convert list of DictRow to DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            return df  

        
def get_clients_with_restriction_scripts():
    query = """
        SELECT client_code, client_name, restrict_company, company
        FROM transaction_monitor
        WHERE restrict_company IS NOT NULL
        ORDER BY id ASC;
        """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()  # empty DataFrame if no records

            # Convert list of DictRow to DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            return df  
        


def get_all_unverified_transaction():
    query = "SELECT * from unverified_trans ORDER BY created_at DESC;"
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()  # empty DataFrame if no records

            # Convert list of DictRow to DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            return df  

def get_scripts():
    query = """SELECT symbol, "securityName" from average_price ORDER BY symbol ASC;"""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()  

            # Convert list of DictRow to DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            return df  


def insert_aml_transactions_bulk(df, created_by='system'):
    """
    Insert multiple rows from a DataFrame into transaction_monitor.
    Skips rows if client_code already exists.
    
    Expects df columns: ['Client Code', 'Client Name', 'Occupation', 'Company', 'Restrict Company']
    """
    conn = None
    inserted_count = 0
    skipped_count = 0

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Step 1: fetch all existing client_codes to skip
        cur.execute("SELECT client_code FROM transaction_monitor;")
        existing_codes = set([row[0] for row in cur.fetchall()])

        # Step 2: prepare rows to insert
        rows_to_insert = []
        for _, row in df.iterrows():
            client_code = str(row.get('Client Code', '')).strip()
            if not client_code or client_code in existing_codes:
                skipped_count += 1
                continue

            client_name = str(row.get('Client Name', '')).strip()
            occupation = str(row.get('Occupation', '')).strip()
            company = str(row.get('Company', '')).strip()
            restrict_company = str(row.get('Restrict Company', '')).strip() if 'Restrict Company' in df.columns else None

            rows_to_insert.append((
                client_code,
                client_name,
                occupation,
                company,
                restrict_company,
                created_by,
                created_by
            ))

        # Step 3: bulk insert using execute_values
        if rows_to_insert:
            insert_query = """
                INSERT INTO transaction_monitor (
                    client_code,
                    client_name,
                    occupation,
                    company,
                    restrict_company,
                    created_by,
                    updated_by
                )
                VALUES %s
            """
            psycopg2.extras.execute_values(
                cur, insert_query, rows_to_insert, template=None, page_size=100
            )
            conn.commit()
            inserted_count = len(rows_to_insert)

        # print(f"Inserted {inserted_count} rows, skipped {skipped_count} rows (already exist).")
        return inserted_count, skipped_count

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error inserting bulk transactions: {e}")
        return 0, 0

    finally:
        if conn:
            cur.close()
            conn.close()


def dump_demat_records(df:pd.DataFrame, loggedin_username:str):
    # Read uploaded Excel file
    # Normalize columns to match your mapping
    df.columns = [col.strip().upper() for col in df.columns]

    # Map Excel columns to DB columns
    column_mapping = {
        'DATE': 'created_at_bs',
        'BOID': 'boid',
        'NAME': 'client_name',
        'CLIENT CODE': 'client_code',
        'TSL': 'tsl_number',
        'AMOUNT': 'payment_amount',
        'GATEWAY': 'gateway',
        'RENEW TYPE': 'renew_type',
        'OPEN BY': 'open_by',
        'REMARKS': 'remarks',
        'BRANCH':'branch',
        'BRO':'rm_name'
    }

    # Rename dataframe columns
    df = df.rename(columns=column_mapping)

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        inserted_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            boid = str(row['boid']).strip()  # Convert BOID to string

            # Check if BOID already exists
            cursor.execute("SELECT 1 FROM demat_records WHERE boid = %s", (boid,))
            if cursor.fetchone():
                skipped_count += 1
                continue  # Skip existing BOID

            # Prepare insert statement
            insert_query = """
                INSERT INTO demat_records
                (client_name, client_code, boid, tsl_number, payment_amount,
                 gateway, renew_type, open_by, created_at_bs, remarks, rm_name, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                row.get('client_name'),
                '' if pd.isna(row.get('client_code')) else row.get('client_code'),
                boid,
                row.get('tsl_number'),
                row.get('payment_amount'),
                row.get('gateway'),
                str(row.get('renew_type')).strip(),
                row.get('open_by'),
                row.get('created_at_bs'),
                '' if pd.isna(row.get('remarks')) else row.get('remarks'),  
                row.get('rm_name'),
                loggedin_username        
            ))
            inserted_count += 1

        conn.commit()
        return inserted_count, skipped_count
        # st.success(f"Data import completed! Inserted: {inserted_count}, Skipped (BOID exists): {skipped_count}")

    except Exception as e:
        if conn:
            conn.rollback()
        print(e)
        return 0,0

    finally:
        if conn:
            cursor.close()
            conn.close()




def delete_demat_records(boid: int):
    """
    Mark a record as DELETED in demat_records table.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE demat_records
                    SET status = 'DELETED'
                    WHERE boid = %s;
                    """,
                    (boid,)
                )
        # print(f"Record {boid} marked as DELETED.")
        return True
    except Exception as e:
        return False
    finally:
        conn.close()


def update_demat_record(
    # record_id: str,
    *,
    client_name: str,
    boid: str,
    tsl_number: str,
    payment_amount,
    gateway: str,
    renew_type: str,
    rm_name: str,
    updated_by: str,
    bo_to_bo:bool,
    client_code:str
):
    """
    Update a demat record by ID.
    """
    query = """
        UPDATE demat_records
        SET 
            client_name = %(client_name)s,
            boid = %(boid)s,
            tsl_number = %(tsl_number)s,
            payment_amount = %(payment_amount)s,
            gateway = %(gateway)s,
            renew_type = %(renew_type)s,
            rm_name = %(rm_name)s,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = %(updated_by)s,
            is_bo_to_bo = %(is_bo_to_bo)s,
            client_code = %(client_code)s
        WHERE boid = %(boid)s;
    """

    params = {
        "client_name": client_name.strip(),
        "boid": boid.strip(),
        "tsl_number": tsl_number.strip(),
        "payment_amount": payment_amount,
        "gateway": gateway.strip(),
        "renew_type": renew_type.strip(),
        "rm_name": rm_name.strip(),
        "updated_by": updated_by,
        "is_bo_to_bo":bo_to_bo,
        "client_code":client_code
        # "id": record_id
    }

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return True



def insert_demat_record(
    *,
    client_name: str,
    boid: str,
    tsl_number: str,
    payment_amount,
    gateway: str,
    renew_type: str,
    rm_name: str,
    open_by: str,
    created_at_bs:str,
    remarks:str,
    bo_to_bo:bool,
    client_code:str
):
    """
    Inserts a demat record if BOID does not already exist.
    Returns:
        - UUID if inserted
        - None if BOID already exists
    """
    conn = get_connection()
    
    boid = boid.strip()

    check_query = """
        SELECT 1
        FROM demat_records
        WHERE boid = %(boid)s
        LIMIT 1;
    """

    insert_query = """
        INSERT INTO demat_records (
            client_name,
            boid,
            tsl_number,
            payment_amount,
            gateway,
            renew_type,
            rm_name,
            open_by,
            created_at_bs,
            updated_by,
            remarks,
            is_bo_to_bo,
            client_code
        )
        VALUES (
            %(client_name)s,
            %(boid)s,
            %(tsl_number)s,
            %(payment_amount)s,
            %(gateway)s,
            %(renew_type)s,
            %(rm_name)s,
            %(open_by)s,
            %(created_at_bs)s,
            %(updated_by)s,
            %(remarks)s,
            %(is_bo_to_bo)s,
            %(client_code)s
        )
        RETURNING id;
    """

    params = {
        "client_name": client_name.strip(),
        "boid": boid,
        "tsl_number": tsl_number.strip().upper(),
        "payment_amount": float(payment_amount),
        "gateway": gateway.strip(),
        "renew_type": renew_type.strip(),
        "rm_name": rm_name.strip(),
        "open_by": open_by.strip().upper(),
        "created_at_bs":  created_at_bs,
        "updated_by":open_by.strip().upper(),
        "remarks":remarks,
        "is_bo_to_bo": bo_to_bo,
        "client_code":client_code
    }

    with conn.cursor() as cursor:
        cursor.execute(check_query, {"boid": boid})
        if cursor.fetchone():
            return None  # BOID already exists

        cursor.execute(insert_query, params)
        record_id = cursor.fetchone()["id"]
        conn.commit()
        return record_id


# def fetch_all_demat_records():
#     """
#     Fetches all records from demat_records table.
#     Returns:
#         - List of dictionaries (column_name -> value)
#     """
#     query = """
#         SELECT 
#             id,
#             client_name,
#             boid,
#             tsl_number,
#             payment_amount,
#             gateway,
#             renew_type,
#             rm_name,
#             open_by,
#             created_at,
#             created_at_bs
#         FROM demat_records
#         ORDER BY created_at DESC;
#     """

#     with get_connection() as conn:
#         with conn.cursor() as cursor:
#             cursor.execute(query)
#             rows = cursor.fetchall()
#             # Convert DictRow to regular dict
#             return [dict(row) for row in rows]
        
def fetch_demat_records_df():
    """
    Fetch all records from demat_records and return as a Pandas DataFrame
    """
    query = "SELECT * FROM demat_records WHERE status = 'ACTIVE' ORDER BY created_at DESC;"

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                return pd.DataFrame()  # empty DataFrame if no records

            # Convert list of DictRow to DataFrame
            df = pd.DataFrame([dict(row) for row in rows])
            return df  


def fetch_demat_records_with_branch_df():
    """
    Fetch all demat_records and add a 'Branch' column by joining with app_user on open_by=username
    Returns a DataFrame ready for display
    """
    # Fetch records
    df_records = fetch_demat_records_df()
    if df_records.empty:
        return df_records  # return empty if nothing in DB

    # Fetch app_user table
    query = "SELECT username, branch FROM app_user;"
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            if not rows:
                df_users = pd.DataFrame(columns=["username", "branch"])
            else:
                df_users = pd.DataFrame([dict(r) for r in rows])

    # Merge branch info on open_by -> username
    df = df_records.merge(
        df_users,
        how="left",
        left_on="open_by",
        right_on="username"
    )

    # Add branch column
    df.rename(columns={"branch": "Branch"}, inplace=True)

    # Drop helper username column (optional)
    df.drop(columns=["username"], inplace=True, errors="ignore")
        # Reorder columns: put Branch first
    cols = df.columns.tolist()
    if "Branch" in cols:
        cols.insert(0, cols.pop(cols.index("Branch")))
        df = df[cols]
    return df

def save_transactions_to_db(transactions, created_by):
    """
    Save all transaction rows to PostgreSQL 'unverified_trans' table,
    skipping rows where the 'description' already exists.
    
    Returns a list of skipped transactions.
    """
    skipped = []

    if not transactions:
        return skipped  # nothing to save

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Optional optimization: fetch all existing descriptions at once
            cur.execute("SELECT description FROM unverified_trans")
            existing_desc = set(r[0] for r in cur.fetchall())

            for row in transactions:
                description = row.get("Description", "").strip()

                # Skip if description already exists
                if description in existing_desc:
                    skipped.append(row)
                    continue  # skip this row

                # Generate UUID for id
                row_id = str(uuid.uuid4())

                # Uploaded at current datetime in 'YYYY-MM-DD HH:MI:SS AM/PM' format
                uploaded_at = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

                # Insert into DB
                cur.execute(
                    """
                    INSERT INTO unverified_trans (
                        id, transaction_date, description, remarks,
                        withdraw, deposit, balance, created_at, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row_id,
                        row.get("Transaction Date", ""),
                        description,
                        row.get("Remarks", ""),
                        row.get("Withdraw", ""),
                        row.get("Deposit", ""),
                        row.get("Balance (NPR)", ""),
                        uploaded_at,
                        created_by
                    )
                )

                # Add description to existing_desc to prevent duplicates in same batch
                existing_desc.add(description)

        conn.commit()
        # print(f"{len(transactions) - len(skipped)} transactions saved to DB successfully.")
        # if skipped:
        #     print(f"{len(skipped)} transactions skipped due to duplicate descriptions.")
        return skipped

    except Exception as e:
        conn.rollback()
        # print("Error saving transactions:", e)
        raise
    finally:
        conn.close()

def update_unverified_transaction(description, client_code, receipt_no, bank_name):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE unverified_trans
                SET client_code = %s,
                    receipt_no = %s,
                    bank_name = %s
                WHERE description = %s
                """,
                (client_code.upper(), receipt_no.upper(), bank_name.upper(), description)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def delete_unverified_transaction(description):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE unverified_trans
                SET status = 'VERIFIED'
                WHERE description = %s;
                """,
                (description,)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_unverified_transactions():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM unverified_trans
                WHERE status = 'ACTIVE'
                ORDER BY created_at DESC;
                """
            )
            rows = cur.fetchall()

            # This will include all columns from the DB exactly as they are
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])

            return df
    except Exception as e:
        print("Error fetching transactions:", e)
        raise
    finally:
        conn.close()

# def get_unique_client_code_from_floorsheet():
#     conn = get_connection()
#     try:
#         with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
#             cur.execute(
#                 """
#                 SELECT DISTINCT clientcode
#                 FROM floorsheet ORDER BY clientcode ASC LIMIT 10    ;
#                 """
#             )
#             rows = cur.fetchall()

#             # This will include all columns from the DB exactly as they are
#             df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])

#             return df
#     except Exception as e:
#         print("Error fetching transactions:", e)
#         raise
#     finally:
#         conn.close()


def get_unique_client_code_from_floorsheet():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT f.clientcode
                FROM floorsheet f
                LEFT JOIN transaction_monitor t
                ON f.clientcode = t.client_code
                WHERE t.client_code IS NULL
                ORDER BY f.clientcode ASC;
                """
            )
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])
            return df

    except Exception as e:
        print("Error fetching unique client codes:", e)
        raise
    finally:
        conn.close()




def fetch_top_brokers_by_date(start_date, end_date) -> pd.DataFrame:
    """
    Fetches all columns from top_brokers table between given dates
    and returns the result as a Pandas DataFrame.
    """

    query = """
        SELECT *
        FROM top_brokers
        WHERE date::date BETWEEN %s AND %s
        ORDER BY date::date
    """

    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query, (start_date, end_date))
            rows = cur.fetchall()

            # Extract column names from cursor description
            columns = [desc.name for desc in cur.description]

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=columns)

    return df

def fetch_top_brokers(date):
    """
    Fetch top brokers for a given date as a pandas DataFrame without using pd.read_sql.
    """
    # Convert date to string
    if not isinstance(date, str):
        date_str = date.strftime('%Y-%m-%d')
    else:
        date_str = date

    query = '''
        SELECT *
        FROM top_brokers
        WHERE TO_DATE(date, 'YYYY-MM-DD') = %s
        ORDER BY "DT_Row_Index"
    '''

    # Open connection and fetch rows
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (date_str,))
            rows = cursor.fetchall()
            # Get column names from cursor
            columns = [desc[0] for desc in cursor.description]

    # Convert to DataFrame
    df = pd.DataFrame(rows, columns=columns)

    # Optional: convert numeric columns from string to float
    numeric_cols = df.select_dtypes(include='object').columns.difference(['name', 'number', 'date'])
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

    return df


def get_cbr_filename() -> str | None:
    """
    Fetches the filename from cbr_filepath table.
    Assumes single-row design with id = 1.
    Returns only the filename.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT filepath
                FROM cbr_filepath
                WHERE id = 1
            """)
            row = cur.fetchone()

            if not row or not row["filepath"]:
                return None

            return row["filepath"]

    except psycopg2.Error as e:
        raise RuntimeError(f"Failed to fetch filename: {e}") from e

    finally:
        if conn:
            conn.close()

def get_cbr_created_date() -> str | None:
    """
    Fetches the filename from cbr_filepath table.
    Assumes single-row design with id = 1.
    Returns only the filename.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT created_at
                FROM cbr_filepath
                WHERE id = 1
            """)
            row = cur.fetchone()

            if not row or not row["created_at"]:
                return None

            return row["created_at"]

    except psycopg2.Error as e:
        raise RuntimeError(f"Failed to fetch filename: {e}") from e

    finally:
        if conn:
            conn.close()


def get_cost_benefit_data():
    query = """
        SELECT *
        FROM cost_benefit
    """

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)

        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]   # ✅ get column names

        cur.close()
        conn.close()
        df = pd.DataFrame(rows, columns=cols)        # ✅ return DataFrame with columns
        # df.drop(columns=['uploaed_at'], inplace=True)
        # df.round(2)
        return df

    except Exception as e:
        print("DB Error:", e)
        return pd.DataFrame()
    
def update_manager_request(
    uarf_id,
    full_name,
    dob_bs,
    dob_ad,
    citizenship_number,
    citizenship_issued_place,
    personal_phone,
    personal_email,
    supervisor_name,
    selected_platforms,
    employee_type
):
    """
    Update a rejected UARF with new details from the Manager.
    Also updates the platforms selected by the Manager.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 1️⃣ Update uarf_request table
        cur.execute("""
            UPDATE uarf_request
            SET full_name = %s,
                dob_bs = %s,
                dob_ad = %s,
                citizenship_number = %s,
                citizenship_issued_place = %s,
                personal_phone = %s,
                personal_email = %s,
                supervisor_name = %s,
                status = 'PENDING',  -- reset status for HR review
                updated_at = NOW(),
                employee_type = %s,
                rejection_reason = NULL
            WHERE id = %s;
        """, (
            full_name,
            dob_bs,
            dob_ad,
            citizenship_number,
            citizenship_issued_place,
            personal_phone,
            personal_email,
            supervisor_name,
            employee_type,
            uarf_id
        ))

        # 2️⃣ Update uarf_platform_access table
        # First, reset all access_required flags to False
        cur.execute("""
            UPDATE uarf_platform_access
            SET access_required = FALSE,
                access_created = FALSE
            WHERE uarf_id = %s;
        """, (uarf_id,))

        # Then insert/update selected platforms
        for platform, required in selected_platforms.items():
            if required:
                # Check if platform row exists
                cur.execute("""
                    SELECT id FROM uarf_platform_access
                    WHERE uarf_id = %s AND platform_name = %s;
                """, (uarf_id, platform))
                row = cur.fetchone()
                if row:
                    cur.execute("""
                        UPDATE uarf_platform_access
                        SET access_required = TRUE,
                            access_created = FALSE
                        WHERE id = %s;
                    """, (row[0],))
                else:
                    cur.execute("""
                        INSERT INTO uarf_platform_access (
                            uarf_id, platform_name, access_required, access_created, created_at
                        ) VALUES (%s, %s, TRUE, FALSE, NOW());
                    """, (uarf_id, platform))

        conn.commit()
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        print("Error updating UARF:", e)
        return False

    finally:
        if conn:
            conn.close()


def update_it_platforms( uarf_id, platform_flags):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        # 1️⃣ Update platform flags
        for platform, created in platform_flags.items():
            cur.execute("""
                UPDATE uarf_platform_access
                SET access_created = %s
                WHERE uarf_id = %s AND platform_name = %s;
            """, (created, uarf_id, platform))

        # 2️⃣ Check if all required platforms are created
        cur.execute("""
            SELECT COUNT(*) FROM uarf_platform_access
            WHERE uarf_id = %s AND access_required = TRUE AND access_created = FALSE;
        """, (uarf_id,))
        remaining = cur.fetchone()[0]

        if remaining == 0:
            # Mark request as CREATED
            cur.execute("""
                UPDATE uarf_request
                SET status = 'CREATED', updated_at = NOW()
                WHERE id = %s;
            """, (uarf_id,))

        conn.commit()
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        return False

    finally:
        if conn:
            conn.close()



def approve_by_hr(
    uarf_id,
    employee_id,
    office_phone,
    office_email,
    department,
    designation,
    joining_date,
    work_location
):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        sql = """
            UPDATE uarf_request
            SET
                employee_id = %s,
                office_phone = %s,
                office_email = %s,
                department = %s,
                designation = %s,
                joining_date = %s,
                work_location = %s,
                status = 'APPROVED_BY_HR',
                updated_at = NOW()
            WHERE id = %s;
        """

        cur.execute(sql, (
            employee_id,
            office_phone,
            office_email,
            department,
            designation,
            joining_date,
            work_location,
            uarf_id
        ))

        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        return False

    finally:
        if conn:
            conn.close()

def reject_by_hr(uarf_id, rejection_reason="Not specified"):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE uarf_request
            SET status = 'REJECTED_BY_HR',
                rejection_reason = %s,
                updated_at = NOW()
            WHERE id = %s;
        """, (rejection_reason, uarf_id))

        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        return False

    finally:
        if conn:
            conn.close()

def reject_by_it(uarf_id, rejection_reason="Not specified"):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE uarf_request
            SET status = 'REJECTED_BY_IT',
                    rejection_reason = %s,
                updated_at = NOW(),
            WHERE id = %s;
        """, (rejection_reason, uarf_id))

        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        return False

    finally:
        if conn:
            conn.close()


def submit_manager_request(
        full_name,
        dob_bs,
        dob_ad,
        citizenship_number,
        citizenship_issued_place,
        personal_phone,
        personal_email,
        supervisor_name,
        selected_platforms,
        employee_type,
        username
    ):
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()

            # 1️⃣ Insert into uarf_request and fetch UUID
            insert_uarf_sql = """
                INSERT INTO uarf_request (
                    status,
                    full_name,
                    dob_bs,
                    dob_ad,
                    citizenship_number,
                    citizenship_issued_place,
                    personal_phone,
                    personal_email,
                    supervisor_name,
                    created_by,
                    employee_type
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id;
            """

            cur.execute(
                insert_uarf_sql,
                (
                    "PENDING",
                    full_name.upper(),
                    dob_bs,
                    dob_ad,
                    citizenship_number.upper(),
                    citizenship_issued_place.upper(),
                    personal_phone,
                    personal_email.lower(),
                    supervisor_name.upper(),
                    username.upper(),
                    employee_type.upper()
                )
            )

            uarf_id = cur.fetchone()["id"]

            # 2️⃣ Prepare platform rows
            platform_rows = [
                (uarf_id, platform, required)
                for platform, required in selected_platforms.items()
            ]

            insert_platform_sql = """
                INSERT INTO uarf_platform_access (
                    uarf_id,
                    platform_name,
                    access_required
                )
                VALUES %s;
            """

            execute_values(
                cur,
                insert_platform_sql,
                platform_rows
            )

            conn.commit()

            return True
            

        except Exception as e:
            if conn:
                conn.rollback()
            return False

        finally:
            if conn:
                conn.close()

def get_today_floorsheet(selected_date):
    query = """
        SELECT *
        FROM floorsheet
        WHERE uploaded_at LIKE %s
        ORDER BY uploaded_at DESC;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Format today's date as string (YYYY-MM-DD%)
        today_pattern = str(selected_date )+ "%"
        # today_pattern = date.today().strftime("%Y-%m-%d") + "%"
        cur.execute(query, (today_pattern,))
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        print("DB Error:", e)
        return pd.DataFrame()
    


def get_floorsheet_by_script_and_date_range(script, start_date, end_date):
    query = """
        SELECT *
        FROM floorsheet
        WHERE symbol = %s
          AND uploaded_at::date BETWEEN %s AND %s
    """
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute(query, (script, start_date, end_date))
        rows = cur.fetchall()
        columns = [desc.name for desc in cur.description]
        return pd.DataFrame(rows, columns=columns)


def get_floorsheet_by_scripts(scripts):
    query = """
    SELECT *
    FROM floorsheet
    WHERE uploaded_at LIKE CURRENT_DATE::text || '%%'
      AND symbol = ANY(%s);
"""
    conn = None
    df = pd.DataFrame()
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, (scripts,))  # ✅ wrap list in tuple
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=[desc.name for desc in cur.description])
    except Exception as e:
        print("Error fetching floorsheet:", e)
    finally:
        if conn:
            conn.close()
    return df


def get_floorsheet_data():
    query = """
    SELECT *
    FROM floorsheet
    ORDER BY uploaded_at DESC;
"""
    conn = None
    df = pd.DataFrame()
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query)  # ✅ wrap list in tuple
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=[desc.name for desc in cur.description])
    except Exception as e:
        print("Error fetching floorsheet:", e)
    finally:
        if conn:
            conn.close()
    return df

def get_floorsheet_summary():
    # We aggregate by Date, Branch, and Type to reduce data size significantly
    query = """
    SELECT 
        DATE(uploaded_at) AS date,
        branch,
        transaction_type,
        SUM(amount) AS total_amount
    FROM floorsheet
    GROUP BY DATE(uploaded_at), branch, transaction_type
    ORDER BY date DESC;
    """
    conn = None
    df = pd.DataFrame()
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=[desc.name for desc in cur.description])
    except Exception as e:
        print("Error fetching floorsheet summary:", e)
    finally:
        if conn:
            conn.close()
    return df


def get_today_floorsheet_range(from_selected_date, to_selected_date):
    query = """
       SELECT *
        FROM floorsheet
        WHERE to_date(substr(uploaded_at, 1, 10), 'YYYY-MM-DD') 
            BETWEEN %s AND %s;

            """

    conn = None
    df = pd.DataFrame()
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, (from_selected_date, to_selected_date))
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=[desc.name for desc in cur.description])
    except Exception as e:
        print("Error fetching floorsheet:", e)
    finally:
        if conn:
            conn.close()
    return df

def get_floorsheet_range_aml(from_selected_date, to_selected_date):
    query = """
       SELECT clientcode, clientname, symbol, tradetime
        FROM floorsheet
        WHERE to_date(substr(uploaded_at, 1, 10), 'YYYY-MM-DD') 
            BETWEEN %s AND %s;
            """

    conn = None
    df = pd.DataFrame()
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, (from_selected_date, to_selected_date))
            rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=[desc.name for desc in cur.description])
    except Exception as e:
        print("Error fetching floorsheet:", e)
    finally:
        if conn:
            conn.close()
    return df


def store_jwt_token(jwt_value: str):
    """
    Insert or replace the single JWT value in dg_api_token table.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO dg_api_token (id, jwt)
                VALUES (1, %s)
                ON CONFLICT (id)
                DO UPDATE SET jwt = EXCLUDED.jwt;
            """, (jwt_value,))
        conn.commit()
        helper.show_message("JWT updated successfully.", "green")
    except Exception as e:
        helper.show_message(f"Error updating JWT: {e}", "red")
    finally:
        if conn:
            conn.close()


def get_jwt_token() -> str | None:
    """
    Fetch the single JWT stored in dg_api_token.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT jwt FROM dg_api_token LIMIT 1;")
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        helper.show_message(f"Error fetching JWT: {e}", "red")
        return None
    finally:
        if conn:
            conn.close()



# def insert_book_closure_from_file(df: pd.DataFrame, username: str):
#     conn = get_connection()
#     cur = conn.cursor()

#     inserted = 0
#     now = datetime.now()

#     for _, row in df.iterrows():
#         cur.execute("""
#             INSERT INTO book_closure (
#                 id, script, start_date, end_date, t0, t1, t2,
#                 created_by, created_at, updated_by, updated_at
#             )
#             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
#         """, (
#             str(uuid.uuid4()),
#             row["script"],
#             row["start_date"],
#             row["end_date"],
#             row["t0"],
#             row["t1"],
#             row["t2"],
#             username,   # created_by
#             now,             # created_at
#             username,   # updated_by
#             now              # updated_at
#         ))

#         inserted += 1

#     conn.commit()
#     cur.close()
#     conn.close()

#     return inserted


def insert_book_closure_from_file(df: pd.DataFrame, username: str):
    conn = get_connection()
    cur = conn.cursor()

    # Fetch existing scripts from DB
    cur.execute("SELECT script FROM book_closure")
    existing_scripts = {row[0] for row in cur.fetchall()}

    inserted = 0
    now = datetime.now()

    for _, row in df.iterrows():
        script_name = row["script"]
        if script_name in existing_scripts:
            # Skip if script already exists
            continue

        cur.execute("""
            INSERT INTO book_closure (
                id, script, start_date, end_date, t0, t1, t2,
                created_by, created_at, updated_by, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()),
            script_name,
            row["start_date"],
            row["end_date"],
            row["t0"],
            row["t1"],
            row["t2"],
            username,
            now,
            username,
            now
        ))

        inserted += 1
        existing_scripts.add(script_name)  # Add to set to avoid duplicates within the same file

    conn.commit()
    cur.close()
    conn.close()

    return inserted


def process_bulk_tag(df: pd.DataFrame, assign_by: str):
    conn = get_connection()
    cur = conn.cursor()

    inserted = 0

    for _, row in df.iterrows():
        client_code = row["clientCode"]
        client_name = row["clientName"]
        rm_name = row["rmName"]

        # Fetch rmFullName from rm table
        cur.execute(
            'SELECT full_name FROM app_user WHERE alias = %s',
            (rm_name,)
        )
        result = cur.fetchone()
        rm_full_name = result[0] if result else None

        # UUID
        row_id = str(uuid.uuid4())

        # Timestamp
        assign_at = datetime.now()  # Python datetime → PostgreSQL timestamp

        # Insert
        insert_query = """
            INSERT INTO client_rm_map (
                id, "clientCode", "clientName", "rmName", "rmFullName",
                "assign_by", "assign_at"
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        cur.execute(insert_query, (
            row_id,
            client_code,
            client_name,
            rm_name,
            rm_full_name,
            assign_by,
            assign_at
        ))

        inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    return inserted




def process_tranfer_from_file(df, assign_by: str) -> int:
    """
    Bulk transfer RM for clients from uploaded Excel.
    Entire operation is transactional.
    """

    conn = None
    cur = None
    updated_count = 0

    try:
        conn = get_connection()
        cur = conn.cursor()

        update_sql = """
            UPDATE client_rm_map
            SET
                "rmName" = %s,
                "rmFullName" = (
                    SELECT "rmFullName"
                    FROM client_rm_map
                    WHERE "rmName" = %s
                    LIMIT 1
                ),
                "assign_by" = %s,
                "assign_at" = %s
            WHERE
                "clientCode" = %s
                AND "rmName" = %s
        """

        now = datetime.now()

        for _, row in df.iterrows():
            dest_rm = row["DEST_RM"]

            cur.execute(
                update_sql,
                (
                    dest_rm,                   # new rmName
                    dest_rm,                   # lookup rmFullName using DEST_RM
                    assign_by,                 # assigned by
                    now,                       # assigned at
                    str(row["CLIENT_CODE"]),   # client code
                    row["SOURCE_RM"]            # validate current RM
                )
            )

            updated_count += cur.rowcount

        conn.commit()
        return updated_count

    except Exception as e:
        if conn:
            conn.rollback()
        raise RuntimeError(f"RM transfer failed: {str(e)}")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()



def transfer_bulk_clients(from_rm: str, to_rm: str, to_rm_full_name: str):
    query = """
        UPDATE client_rm_map
        SET "rmName" = %s,
            "rmFullName" = %s
        WHERE "rmName" = %s;
    """

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, (to_rm, to_rm_full_name, from_rm))
        affected = cur.rowcount   # number of updated rows
        conn.commit()

        cur.close()
        conn.close()

        return affected  # return count instead of DataFrame

    except Exception as e:
        print("DB Error:", e)
        return 0


# def get_due_list(selected_date):
#     query = """
#         SELECT *
#         FROM due_list
#         WHERE to_timestamp(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM')::date = %s
#           AND to_char(to_timestamp(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM'), 'AM') = 'PM';
#     """

#     try:
#         conn = get_connection()
#         cur = conn.cursor()
#         cur.execute(query, (selected_date,))   # ✅ pass date here
#         rows = cur.fetchall()
#         cols = [desc[0] for desc in cur.description]
#         cur.close()
#         conn.close()

#         return pd.DataFrame(rows, columns=cols)

#     except Exception as e:
#         print("DB Error:", e)
#         return pd.DataFrame()


# def get_due_list_for_dpm3(target_date: date) -> pd.DataFrame:
#     query = """
#         SELECT "clientCode", "adjustedBalance"
#         FROM due_list
#         WHERE TO_TIMESTAMP(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM')::DATE = %s
#           AND RIGHT(uploaded_at, 2) = 'AM';
#     """

#     try:
#         conn = get_connection()
#         cur = conn.cursor()

#         # psycopg2 will safely map Python date -> PostgreSQL DATE
#         cur.execute(query, (target_date,))
#         rows = cur.fetchall()

#         columns = [desc[0] for desc in cur.description]

#     finally:
#         cur.close()
#         conn.close()

#     return pd.DataFrame(rows, columns=columns)
    


def get_due_list_for_dpm3(target_date: date) -> tuple[str, pd.DataFrame]:
    """
    Try fetching due list for PM first, fallback to AM if no rows.
    Returns (status, DataFrame).
    """
    base_query = """
        SELECT "clientCode", "adjustedBalance"
        FROM due_list
        WHERE TO_TIMESTAMP(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM')::DATE = %s
          AND RIGHT(uploaded_at, 2) = %s;
    """

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Try PM first
        cur.execute(base_query, (target_date, "PM"))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        if rows:  # found PM rows
            status = "PM rows"
            return status, pd.DataFrame(rows, columns=columns)

        # Fallback to AM
        cur.execute(base_query, (target_date, "AM"))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        if rows:
            status = "AM rows"
            return status, pd.DataFrame(rows, columns=columns)
        else:
            status = "No rows found for either PM or AM"
            return status, pd.DataFrame(columns=["clientCode", "adjustedBalance"])

    finally:
        cur.close()
        conn.close()



def get_due_list(selected_start_date: date, selected_end_date: date):
    query = """
        SELECT *
        FROM due_list
        WHERE to_timestamp(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM')::date BETWEEN %s AND %s
          AND to_char(to_timestamp(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM'), 'AM') = 'PM';
    """

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, (selected_start_date, selected_end_date))
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        return pd.DataFrame(rows, columns=cols)

    except Exception as e:
        print("DB Error:", e)
        return pd.DataFrame()



    




def insert_book_closure(script, start_date, end_date, t0, t1, t2, created_by,updated_by):
    query = """
        INSERT INTO book_closure (
            id,
            script,
            start_date,
            end_date,
            t0,
            t1,
            t2,
            created_by,
            created_at,
            updated_by
        )
        VALUES (
            %s,  -- id
            %s,  -- script
            %s,  -- start_date
            %s,  -- end_date
            %s,  -- t0
            %s,  -- t1
            %s,  -- t2
            %s,  -- created_by
            NOW(),
            %s
        )
    """

    params = (
        str(uuid.uuid4()),
        script,
        start_date,
        end_date,
        t0,
        t1,
        t2,
        created_by,
        updated_by
    )

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print("DB Error:", e)
        return False

def update_book_closure(id, script, start_date, end_date, t0, t1, t2, updated_by):
    query = """
        UPDATE book_closure
        SET 
            script = %s,
            start_date = %s,
            end_date = %s,
            t0 = %s,
            t1 = %s,
            t2 = %s,
            updated_by = %s,
            updated_at = NOW()
        WHERE id = %s
    """

    params = (script, start_date, end_date, t0, t1, t2, updated_by, id)

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print("DB Error:", e)
        return False

def get_all_book_closure():
    query = """
        SELECT 
            *
        FROM book_closure
        ORDER BY created_at DESC;
    """

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]  # ✅ column names
        cur.close()
        conn.close()

        return pd.DataFrame(rows, columns=cols)  # ✅ return DataFrame

    except Exception as e:
        print("DB Error:", e)
        return pd.DataFrame()


# def get_today_book_closure(selected_date):
#     query = """
#         SELECT *
#         FROM book_closure
#         WHERE start_date = %s
#         ORDER BY created_at DESC;
#     """
#     try:
#         conn = get_connection()
#         cur = conn.cursor()
#         cur.execute(query, (selected_date,))
#         rows = cur.fetchall()
#         cols = [desc[0] for desc in cur.description]
#         cur.close()
#         conn.close()
#         return pd.DataFrame(rows, columns=cols)
#     except Exception as e:
#         print("DB Error:", e)
#         return pd.DataFrame()


def get_today_book_closure_range(selected_date):
    query = """
        SELECT script
        FROM book_closure
        WHERE %s BETWEEN start_date AND end_date
        ORDER BY created_at DESC;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        today = selected_date # get today's date
        # today = date.today()   # get today's date
        cur.execute(query, (today,))
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        print("DB Error:", e)
        return pd.DataFrame()

def get_today_book_closure_only(selected_date):
    query = """
        SELECT *
        FROM book_closure
        WHERE t0 = %s
        ORDER BY created_at DESC;
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        today = selected_date   # get today's date
        # today = date.today()   # get today's date
        cur.execute(query, (today,))
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        print("DB Error:", e)
        return pd.DataFrame()




def get_all_holidays():
    query = """
        SELECT *
        FROM holidays
        ORDER BY holiday_date;
    """

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)

        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]   # ✅ get column names

        cur.close()
        conn.close()

        return pd.DataFrame(rows, columns=cols)        # ✅ return DataFrame with columns

    except Exception as e:
        print("DB Error:", e)
        return pd.DataFrame()

def delete_book_closure(id):
    query = "DELETE FROM book_closure WHERE id = %s"

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, (id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print("DB Error:", e)
        return False   

def holiday_exists(holiday_date):
    query = """
        SELECT 1
        FROM holidays
        WHERE holiday_date = %s
        LIMIT 1;
    """

    try:
        conn = get_connection()
        cur = conn.cursor()

        # ✅ Convert Python date → string (YYYY-MM-DD)
        holiday_date_str = holiday_date.strftime("%Y-%m-%d")

        cur.execute(query, (holiday_date_str,))
        row = cur.fetchone()

        cur.close()
        conn.close()

        return row is not None

    except Exception as e:
        print("DB Error:", e)
        return False

def get_t3_date(selected_date):
    """
    Calculate T+3 working date in Nepal:
    - Skip holidays listed in 'holiday' table (column: holiday_date)
    - Skip Saturdays
    Returns:
        datetime.date object of next valid working day
    """

    # 1️⃣ Initial T+3 date
    t3_date = selected_date + timedelta(days=3)
    # t3_date = datetime.now().date() + timedelta(days=3)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Fetch all holiday dates from table
            cur.execute("SELECT holiday_date FROM holidays;")
            holidays = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

    # Convert holidays to set for fast lookup
    holiday_set = set(holidays)

    # 2️⃣ Loop until we find a valid working day
    while t3_date in holiday_set or t3_date.weekday() == 5:  # 5 = Saturday
        t3_date += timedelta(days=1)

    return t3_date



def get_t3_back_date(selected_date):
    """
    Calculate T-3 working date in Nepal:
    - Skip holidays listed in 'holiday' table (column: holiday_date)
    - Skip Saturdays
    Returns:
        datetime.date object of previous valid working day
    """

    # 1️⃣ Initial T-3 date
    t3_date = selected_date - timedelta(days=3)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT holiday_date FROM holidays;")
            # Convert strings to datetime.date
            holidays = [row[0] if isinstance(row[0], datetime) else datetime.strptime(row[0], "%Y-%m-%d").date()
                        for row in cur.fetchall()]
    finally:
        conn.close()

    holiday_set = set(holidays)

    # 2️⃣ Loop until we find a valid working day
    while t3_date in holiday_set or t3_date.weekday() == 5:  # 5 = Saturday
        t3_date -= timedelta(days=1)  # move back 1 day

    return t3_date


def insert_holiday(holiday_date, holiday_description, created_by):
    query = """
        INSERT INTO holidays (
            id,
            holiday_date,
            holiday_description,
            created_by,
            created_at
        )
        VALUES (%s, %s, %s, %s, NOW())
    """
    holiday_date_str = holiday_date.strftime("%Y-%m-%d")
    params = (
        str(uuid.uuid4()),
        holiday_date_str,
        holiday_description,
        created_by
    )

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print("DB Error:", e)
        return False


# def get_last_sunday():
#     today = datetime.today()
#     # Monday=0 ... Sunday=6
#     if today.weekday() == 6:  
#         # Today is Sunday → return today
#         return today.date()

#     # Otherwise compute last Sunday
#     days_since_sunday = (today.weekday() + 1) % 7
#     last_sunday = today - timedelta(days=days_since_sunday)
#     return last_sunday.date()


# def is_sunday_file_uploaded():
#     sunday_date = get_last_sunday()
#     print(sunday_date)
#     query = """
#         SELECT 1
#         FROM dpm3
#         WHERE (uploaded_at::timestamp)::date = %s
#         LIMIT 1;
#     """

#     try:
#         conn = get_connection()
#         cur = conn.cursor()
#         cur.execute(query, (sunday_date,))
#         result = cur.fetchone()
#         cur.close()
#         conn.close()
#         return result is not None
#     except Exception as e:
#         print("DB Error:", e)
#         return False


def is_this_week_file_uploaded():
    today = datetime.now().date()
    days_since_sunday = (today.weekday() + 1) % 7
    week_start = today - timedelta(days=days_since_sunday)
    week_end   = week_start + timedelta(days=5)
    
    query = """
        SELECT uploaded_at::timestamp::date AS upload_date
        FROM dpm3
        WHERE uploaded_at::timestamp::date 
              BETWEEN %s AND %s
        LIMIT 1;
    """
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, (week_start, week_end))
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return True, result[0]
        return False, None
        
    except Exception as e:
        print("DB Error:", e)
        return False, None
    
    
def get_holidays():
    query = """
        SELECT holiday_date 
        FROM holidays
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()  
        cur.close()
        conn.close()

        # Convert to Python date objects
        holidays = {row[0] for row in rows}  
        return holidays

    except Exception as e:
        print("DB Error:", e)
        return set()

def get_dpm3():
    query = "SELECT * FROM dpm3;"   

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query)

        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]

        cur.close()
        conn.close()

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=col_names)
        return df

    except Exception as e:
        print("DB Error while fetching dpm3:", e)
        return pd.DataFrame()   





def get_user_roles():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT role_type FROM app_user_role ORDER BY role_type;")
            rows = cur.fetchall()
            # Extract just the role_type values into a list
            roles = [row["role_type"] for row in rows]
        return roles
    finally:
        conn.close()


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

def get_table_average_price():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT symbol, "closePrice" from average_price""")
    row = cur.fetchall()
    cur.close()
    conn.close()
    return row

def get_table_rm_child_map():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT "rmName", "clientCode" from client_rm_map""")
    row = cur.fetchall()
    cur.close()
    conn.close()
    return row


def get_table_rm_child_map_for_client_limit():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT "rmName", "rmFullName" ,"clientName", 
                "clientCode", "category" from client_rm_map  order by "rmName" ASC;""")
    row = cur.fetchall()
    cur.close()
    conn.close()
    return row


def get_table_rm_child_map_for_client_limit_by_bro(rm_name):
    conn = get_connection()
    query = """
        SELECT "rmName", "rmFullName", "clientName", 
               "clientCode", "category"
        FROM client_rm_map
        WHERE "rmName" = %s
        ORDER BY "rmName" ASC;
    """
    
    with conn.cursor() as cur:
        cur.execute(query, (rm_name,))
        rows = cur.fetchall()
    
    conn.close()
    return rows




def update_category_client_rm_map(client_code, new_category):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Perform the update
        cur.execute(
            """
            UPDATE client_rm_map
            SET "category" = %s
            WHERE "clientCode" = %s;
            """,
            (new_category, client_code)
        )
        conn.commit()

        # Return the count of rows updated
        updated_count = cur.rowcount
    finally:
        cur.close()
        conn.close()

    return updated_count

def get_category_client_rm_map(client_code):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Fetch the category for the given client_code
        cur.execute(
            """
            SELECT "category"
            FROM client_rm_map
            WHERE "clientCode" = %s;
            """,
            (client_code,)
        )
        row = cur.fetchone()
        # Return the category if found, else None
        return row[0] if row else None
    finally:
        cur.close()
        conn.close()





# def get_rm_name_from_client_rm_map_table(client_code: str):
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute(
#         """SELECT "rmName", "clientName", "clientCode"
#            FROM client_rm_map
#            WHERE "clientCode" = %s""",
#         (client_code.upper(),)
#     )
#     row = cur.fetchone()
#     cur.close()
#     conn.close()

#     # Return only rmName if row exists, else "N/A"
#     return row[0] if row else "N/A"


def get_table_rm_child_map_with_client_code(client_code: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT "rmName", "clientName"
           FROM client_rm_map
           WHERE "clientCode" = %s""",
        (client_code.upper(),)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    # Return (rmName, clientName) if row exists, else ("N/A", "N/A")
    return (row[0], row[1]) if row else ("N/A", "N/A")


def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, role, password, status, citizenship, phone, email, branch FROM app_user WHERE username = %s", (username.upper(),))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_user_by_username_for_login(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id,  username, role, password, status, citizenship, phone, email, branch FROM app_user WHERE username = %s", (username.upper(),))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_user_by_pin_for_login(pin):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id,  username, role, pin, status, citizenship, phone, email, branch FROM app_user WHERE pin = %s", (pin,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_all_app_user():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, full_name ,role, phone, password, email, branch FROM app_user")
    row = cur.fetchall()
    cur.close()
    conn.close()
    return row

def get_kyc():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT clientmembercode,clientfullname, clientbranch, boid from kyc")
    row = cur.fetchall()
    cur.close()
    conn.close()
    return row


def get_kyc_with_rm():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            k.clientmembercode,
            k.clientfullname,
            k.clientbranch,
            k.boid,
            COALESCE(crm."rmName", 'N/A') AS rmName
        FROM kyc k
        LEFT JOIN client_rm_map crm 
            ON k.clientmembercode = crm."clientCode"
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_isin_data():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT "ISIN", "SCRIP" FROM isin""")
    row = cur.fetchall()
    cur.close()
    conn.close()
    return row



def get_user_by_pin(pin:str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, role, password, status, citizenship, phone, email FROM app_user WHERE pin = %s", (pin.strip(),))
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

def assign_clients_to_rm(selected_codes, rm_username, assign_by, assign_at, updated_at, updated_by):
    """
    selected_codes : list[str]
    rm_username    : str
    """

    query = """
        UPDATE client_rm_map ck
        SET
            "rmName" = %s,
            "rmFullName" = au.full_name,
            "assign_by" = %s,
            "assign_at" = %s,
            "updated_at" = %s,
            "updated_by" = %s
        FROM app_user au
        WHERE
            au.username = %s
            AND ck."clientCode" = ANY(%s);
    """

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (
                    rm_username,   # rmName
                    assign_by,     # assignBy
                    assign_at,     # assignAt
                    updated_at,
                    updated_by,
                    rm_username,   # join with app_user
                    selected_codes # LIST → works with ANY()
                )
            )
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e

    finally:
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


def change_user_info(username: str, password:str, phone: str, email: str, citizenship:str) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Update the user information
        cur.execute(
            """
            UPDATE app_user
            SET password = %s, phone = %s, email = %s, citizenship = %s
            WHERE username = %s;
            """,
            (password.strip(), phone.strip(), email.lower().strip(), citizenship.lower().strip() ,username.upper().strip())
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

def update_login_status_by_pin(pin: str, success: bool) -> int:
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
                        WHERE pin = %s
                    """, (pin,))
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
                        WHERE pin = %s
                        RETURNING failed_attempts
                    """, (now, now, pin))
                    row = cur.fetchone()
                    if row:
                        remaining = MAX_ATTEMPTS - row["failed_attempts"]
                        remaining = max(remaining, 0)
    finally:
        conn.close()
    return remaining


# def create_session(username: str) -> str:
#     """
#     Create a new user session or update an existing session for the given username.
#     Returns the session UUID as a string.
#     """
#     session_id = None
#     conn = get_connection()
#     now = datetime.now()
#     # now = datetime.now().strftime("%Y-%m-%d %T:%H:%s %p")
#     ip_address = helper.get_client_ip()
#     user_agent = helper.get_user_agent()
    
#     try:
#         with conn:
#             with conn.cursor() as cur:
#                 # Check if a session exists for this username
#                 cur.execute("""
#                     SELECT id FROM user_session
#                     WHERE UPPER(username) = %s
#                     LIMIT 1
#                 """, (username.upper(),))
#                 row = cur.fetchone()
                
#                 if row:
#                     # Update existing session
#                     session_id = row[0]
#                     cur.execute("""
#                         UPDATE user_session
#                         SET login_time = %s,
#                             ip_address = %s,
#                             user_agent = %s,
#                             session_status = 'ACTIVE'
#                         WHERE id = %s
#                     """, (now, ip_address, user_agent, session_id))
#                 else:
#                     # Insert new session
#                     cur.execute("""
#                         INSERT INTO user_session (username, login_time, session_status, ip_address, user_agent)
#                         VALUES (%s, %s, 'ACTIVE', %s, %s)
#                         RETURNING id
#                     """, (username.upper(), now, ip_address, user_agent))
#                     row = cur.fetchone()
#                     if row:
#                         session_id = row[0]
#     finally:
#         conn.close()
    
#     return str(session_id)  # Return UUID as string


def create_session(username: str, sid:str):
    """
    Create or update a user session.
    Returns:
        ("EXISTS", row)  -> active session already exists
        ("UPDATED", session_id) -> username exists but was not active, so updated
        ("NEW", session_id) -> username did not exist, so new row created
    """
    conn = get_connection()
    now = datetime.now()
    ip_address = helper.get_client_ip()
    user_agent = helper.get_user_agent()

    try:
        with conn:
            with conn.cursor() as cur:

                # 1️⃣ Check for ACTIVE session
                cur.execute("""
                    SELECT id, login_time, session_status, ip_address, user_agent
                    FROM user_session
                    WHERE UPPER(username) = UPPER(%s)
                    AND session_status = 'ACTIVE'
                    LIMIT 1
                """, (username,))
                active_row = cur.fetchone()

                if active_row:
                    return ("EXISTS", active_row)

                # 2️⃣ Check if username exists at all (inactive session)
                cur.execute("""
                    SELECT id
                    FROM user_session
                    WHERE UPPER(username) = UPPER(%s)
                    LIMIT 1
                """, (username,))
                existing = cur.fetchone()

                if existing:
                    session_id = existing[0]

                    # ✅ Update existing inactive session
                    cur.execute("""
                        UPDATE user_session
                        SET login_time = %s,
                            session_status = 'ACTIVE',
                            ip_address = %s,
                            user_agent = %s,
                            session_id = %s
                        WHERE id = %s
                        RETURNING id
                    """, (now, ip_address, user_agent,sid ,session_id))

                    updated = cur.fetchone()
                    return ("UPDATED", updated[0])

                # 3️⃣ Username does NOT exist → create new row
                cur.execute("""
                    INSERT INTO user_session (username, login_time, session_status, ip_address, user_agent, session_id)
                    VALUES (UPPER(%s), %s, 'ACTIVE', %s, %s, %s)
                    RETURNING id
                """, (username, now, ip_address, user_agent, sid))

                new_row = cur.fetchone()
                return ("NEW", new_row[0])

    finally:
        conn.close()



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
                        session_status = 'LOGGED_OUT',
                        session_id = null
                    WHERE UPPER(username) = UPPER(%s)
                    RETURNING id
                """, (now, username))
                cur.fetchall()
    finally:
        conn.close()

