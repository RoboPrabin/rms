
#db.py

import psycopg2
import psycopg2.extras
import pandas as pd


def get_connection():
    return psycopg2.connect(
        host="localhost",
        dbname="client_holdings",
        user="postgres",
        password="admin",
        cursor_factory=psycopg2.extras.DictCursor
    )


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


