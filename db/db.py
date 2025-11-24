#db.py

import psycopg2
import psycopg2.extras

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