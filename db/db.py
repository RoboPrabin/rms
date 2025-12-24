#db.py
import uuid
from psycopg2 import sql
import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_batch, execute_values
import pandas as pd
from utils import helper
from datetime import datetime, timedelta


def get_connection():
    return psycopg2.connect(
        host="172.17.26.6",
        # host="localhost",
        dbname="client_holdings",
        user="postgres",
        password="admin",
        cursor_factory=psycopg2.extras.DictCursor
    )



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
                    "SUBMITTED",
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




def get_today_floorsheet():
    query = """
        SELECT *
        FROM floorsheet
        WHERE uploaded_at LIKE CURRENT_DATE::text || '%';
    """
    conn = None
    df = pd.DataFrame()
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            # Convert to DataFrame with column names
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



def insert_book_closure_from_file(df: pd.DataFrame, username: str):
    conn = get_connection()
    cur = conn.cursor()

    inserted = 0
    now = datetime.now()

    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO book_closure (
                id, script, start_date, end_date, t0, t1, t2,
                created_by, created_at, updated_by, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()),
            row["script"],
            row["start_date"],
            row["end_date"],
            row["t0"],
            row["t1"],
            row["t2"],
            username,   # created_by
            now,             # created_at
            username,   # updated_by
            now              # updated_at
        ))

        inserted += 1

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
                "assignBy", "assignAt"
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


def get_due_list(selected_date):
    query = """
        SELECT *
        FROM due_list
        WHERE to_timestamp(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM')::date = %s
          AND to_char(to_timestamp(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM'), 'AM') = 'PM';
    """

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, (selected_date,))   # ✅ pass date here
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

def get_today_book_closure():
    query = """
        SELECT script, start_date
        FROM book_closure
        WHERE start_date = CURRENT_DATE
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


def get_last_sunday():
    today = datetime.today()
    # Monday=0 ... Sunday=6
    if today.weekday() == 6:  
        # Today is Sunday → return today
        return today.date()

    # Otherwise compute last Sunday
    days_since_sunday = (today.weekday() + 1) % 7
    last_sunday = today - timedelta(days=days_since_sunday)
    return last_sunday.date()


def is_sunday_file_uploaded():
    sunday_date = get_last_sunday()
    query = """
        SELECT 1
        FROM dpm3
        WHERE (uploaded_at::timestamp)::date = %s
        LIMIT 1;
    """

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(query, (sunday_date,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result is not None
    except Exception as e:
        print("DB Error:", e)
        return False

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
    cur.execute("""SELECT "rmName", "clientName" from client_rm_map""")
    row = cur.fetchall()
    cur.close()
    conn.close()
    return row

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
    cur.execute("SELECT username, role, password, status, citizenship, phone, email FROM app_user WHERE username = %s", (username.upper(),))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def get_all_app_user():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, role, phone, password, email FROM app_user")
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

def assign_clients_to_rm(selected_codes, rm_username, assign_by, assign_at):
    """
    selected_codes : list[str]
    rm_username    : str
    """

    query = """
        UPDATE client_rm_map ck
        SET
            "rmName" = %s,
            "rmFullName" = au.full_name,
            "assignBy" = %s,
            "assignAt" = %s
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
            (password.strip(), phone.strip(), email.strip(), citizenship.lower().strip() ,username.lower().strip())
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

