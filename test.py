import uuid
from utils.helper import get_holding_engine
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(get_holding_engine())

# 1. Load Excel
df = pd.read_excel(
    r"C:\Users\Prabin\Downloads\onenepalstock.xlsx"
)

# Normalize column names
df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]
order = ['id', 'holiday_date', 'holiday_description']
df = df[order]
# 6. Insert into DB
df.to_sql(
    "holidays",
    engine,
    if_exists="append",
    index=False
)

print("Inserted rows:", len(df))





# import pandas as pd
# from sqlalchemy import create_engine
# from utils.helper import get_holding_engine

# engine = create_engine(get_holding_engine())

# # 1. Load Excel
# df = pd.read_excel(
#     r"C:\Users\Prabin\Downloads\BN 48 client_report - Copy.xlsx"
# )

# # Normalize Excel column names
# df.columns = df.columns.str.strip().str.upper()

# excel_codes = df["CLIENT_MEMBER_CODE"].astype(str).str.strip()

# # 2. Load only required columns from DB
# query = """
# SELECT clientmembercode
# FROM kyc
# """
# db_df = pd.read_sql(query, engine)

# db_codes = db_df["clientmembercode"].astype(str).str.strip()

# # 3. Find which codes are NOT in DB table
# missing_codes = excel_codes[~excel_codes.isin(db_codes)]

# print("CLIENT_MEMBER_CODE not found in table:")
# print(missing_codes.unique())
# total_missing = missing_codes.shape[0]
# print("Total missing (including duplicates):", total_missing)