from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from utils import helper   # assuming you already have helper.get_holding_engine()

# File path
filepath = r"C:\Users\Administrator\Desktop\RM Client Due List with Ageing_2025-12-05_Friday.xlsx"

# Read Excel
df = pd.read_excel(filepath)

# Add uploaded_at column
df['uploaded_at'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

# Create SQLAlchemy engine
engine = create_engine(helper.get_holding_engine())

# Dump into table due_list
df.to_sql("due_list", con=engine, if_exists="append", index=False)

print("Data dumped successfully into due_list!")
