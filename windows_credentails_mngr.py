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

def get_connection():
    return psycopg2.connect(
        host="172.17.26.6",
        dbname="rms",
        user="postgres",
        password="admin"
    )

filepath = r"C:\Users\Prabin\Desktop\test.xlsx"

df = pd.read_excel(filepath)
ids = df['id'].tolist()

conn = get_connection()
cur = conn.cursor()

cur.execute(
    "DELETE FROM demat_records WHERE id = ANY(%s::uuid[])",
    (ids,)
)

conn.commit()
cur.close()
conn.close()