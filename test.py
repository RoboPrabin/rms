from datetime import datetime
import pandas as pd
import uuid
from sqlalchemy import create_engine

# Step 1: Read CSV
csv_path = r"C:\Users\Prabin\Downloads\rm_table.csv"
df = pd.read_csv(csv_path)

# Step 2: Add UUID column
df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]

# Step 3: Add password column
# Assuming your CSV has a column named "username"
df["password"] = df["username"].str.title() + "@123"
df["created_at"] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
df["created_by"] = "SYSTEM"
# Step 4: PostgreSQL connection
postgresql_config = {
    "db_user": "postgres",
    "db_password": "admin",
    "db_host": "localhost",
    "db_port": "5432",
    "db_name": "client_holdings"
}

engine = create_engine(
    f'postgresql+psycopg2://{postgresql_config["db_user"]}:{postgresql_config["db_password"]}'
    f'@{postgresql_config["db_host"]}:{postgresql_config["db_port"]}/{postgresql_config["db_name"]}'
)

# # Step 3.5: Reorder columns so 'id' comes first
# cols = ["id"] + [col for col in df.columns if col != "id"]
# df = df[cols]

# # df.to_excel("output.xlsx", index=False)
# df.to_sql("app_user", engine, if_exists="replace", index=False)

# print("Data successfully inserted into PostgreSQL!")



file_path = r"C:\Users\Prabin\Desktop\RM Client Due List with Ageing_2025-12-02_Tuesday.xlsx"
df = pd.read_excel(file_path)

# --- Step 3: Append to table (create if not exists) ---
df['uploaded_at'] =  datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
# to_sql will create the table if it doesn’t exist, and append otherwise
df.to_sql("due_list", con=engine, if_exists="replace", index=False)

print("Data successfully appended to 'due_list' table.")
