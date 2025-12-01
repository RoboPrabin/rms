from db.db import get_connection

import uuid
import pandas as pd


create_table_sql = """
CREATE TABLE IF NOT EXISTS bro_yearly_target (
    id UUID PRIMARY KEY,
    bro_code VARCHAR(255),
    target_amt NUMERIC,
    demat_target NUMERIC
);
"""



filepath = r"C:\Users\Prabin\Downloads\target.csv"
df = pd.read_csv(filepath_or_buffer=filepath)

df = df.drop(columns=['id', 'rm_id', 'created_at'])

# Vectorized assignment: guarantees unique UUIDs
df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]

df.rename(columns={"rm_name":"bro_code"}, inplace=True)

col_order = ['id', 'bro_code', 'target_amt', 'demat_target']
df = df[col_order]

print(df)


def insert_dataframe(df):
    conn = get_connection()
    cur = conn.cursor()

    # Create table if not exists
    cur.execute(create_table_sql)

    # Insert rows
    insert_sql = """
        INSERT INTO bro_yearly_target (id, bro_code, target_amt, demat_target)
        VALUES (%s, %s, %s, %s)
    """
    data = [tuple(row) for row in df.to_numpy()]
    cur.executemany(insert_sql, data)

    conn.commit()
    cur.close()
    conn.close()


insert_dataframe(df=df)