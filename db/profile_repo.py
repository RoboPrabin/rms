from db.db import get_connection
import random
def update_pin(username: str, new_pin: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Update the pin for the given username
        cur.execute("""
            UPDATE app_user
            SET pin = %s
            WHERE username = %s;
        """, (new_pin, username))
        
        conn.commit()
    finally:
        cur.close()
        conn.close()


def generate_pin() -> str:
    conn = get_connection()
    cur = conn.cursor()

    # Fetch all existing pins
    cur.execute("SELECT pin FROM app_user;")
    existing_pins = {row[0] for row in cur.fetchall() if row[0]}

    cur.close()
    conn.close()

    # Ensure uniqueness
    while True:
        # Generate 5 random digits
        random_digits = ''.join(random.choices("0123456789", k=6))
        # Append first letter of username in uppercase
        new_pin = random_digits

        if new_pin not in existing_pins:
            return new_pin
