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

filepath = "output_new_clients.xlsx"
df = pd.read_excel(filepath)

# Normalize to uppercase before sending to DB
df["company"] = df["company"].where(pd.notnull(df["company"]), None)
df["occupation"] = df["occupation"].where(pd.notnull(df["occupation"]), None)

# Uppercase non-null values
df["company"] = df["company"].apply(lambda x: x.upper() if x is not None else None)
df["occupation"] = df["occupation"].apply(lambda x: x.upper() if x is not None else None)
conn = get_connection()
cur = conn.cursor()

# 1. Create a temporary staging table
cur.execute("""
    CREATE TEMP TABLE tmp_updates (
        client_code TEXT,
        occupation TEXT,
        company TEXT
    )
""")

# 2. Bulk insert data into temp table
rows = df[["client_code", "occupation", "company"]].values.tolist()
psycopg2.extras.execute_values(
    cur,
    "INSERT INTO tmp_updates (client_code, occupation, company) VALUES %s",
    rows
)

# 3. Single bulk update using join
cur.execute("""
    UPDATE transaction_monitor t
    SET occupation = u.occupation,
        company = u.company
    FROM tmp_updates u
    WHERE t.client_code = u.client_code
""")

conn.commit()
cur.close()
conn.close()
