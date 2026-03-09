# import keyring



# def set_password(service_name, username, password):
#     keyring.set_password(
#         service_name=service_name,
#         username=username,
#         password=password
#     )


# def get_password():
#     password = keyring.get_password(service_name="MyApp",username="api_user")
#     return password

# def delete_password():
#     keyring.delete_password(service_name="MyApp",username="api_user")


from db import db
import pandas as pd
import psycopg2
import psycopg2.extras
import pandas as pd

def get_connection():
    return psycopg2.connect(
        host="172.17.26.6",
        dbname="client_holdings",
        user="postgres",
        password="admin"
    )

import pandas as pd
from datetime import datetime
import nepali_datetime

def convert_ad_to_bs(ad_date: str) -> str:
    try:
        ad_dt = datetime.strptime(ad_date, "%Y-%m-%d")
        bs_date = nepali_datetime.date.from_datetime_date(ad_dt.date())
        return bs_date.strftime("%Y-%m-%d")
    except Exception as e:
        return ""

def update_created_at_bs():
    conn = get_connection()
    try:
        # Load the relevant columns
        df = pd.read_sql("SELECT id, created_at FROM demat_records", conn)

        # Convert to BS
        df["created_at_bs"] = df["created_at"].apply(lambda x: convert_ad_to_bs(x.strftime("%Y-%m-%d")) if pd.notnull(x) else "")

        # Update the database in batch
        with conn.cursor() as cur:
            for index, row in df.iterrows():
                cur.execute("""
                    UPDATE demat_records
                    SET created_at_bs = %s
                    WHERE id = %s
                """, (row["created_at_bs"], row["id"]))
        conn.commit()
        print(f"Updated {len(df)} rows successfully.")
    finally:
        conn.close()

if __name__ == "__main__":
    update_created_at_bs()