from utils.helper import show_message, show_message_box, get_holding_engine
from sqlalchemy import create_engine
import pandas as pd

# Load Excel file
order_book_df = pd.read_excel(
    r"D:\Trishakti\Projects\RPA\track_stock_price\open_and_completed.xlsx"
)

# Create DB engine
engine = create_engine(get_holding_engine())

# Query DB
with engine.connect() as conn:
    df = pd.read_sql_query("SELECT * FROM client_rm_map", con=conn)

# Merge: match clientMemberCode (Excel) with clientCode (DB)
merge_df = order_book_df.merge(
    df[['clientCode', 'rmName']], 
    left_on='clientMemberCode', 
    right_on='clientCode', 
    how='left'   # keep all rows from Excel
)

# Optional: drop clientCode if you don’t need duplicate
merge_df = merge_df.drop(columns=['clientCode'])
merge_df['rmName'] = merge_df['rmName'].fillna("N/A")

preferred_order = [
    'rmName',
    'clientMemberCode',
    'symbol',
    'securityName',
    'buyOrSell',
    'orderQuantity',
    'orderPrice',
    'amount'
]

# Add any other columns that exist but aren’t in preferred_order
cols = preferred_order + [col for col in merge_df.columns if col not in preferred_order]

# Reorder DataFrame
merge_df = merge_df[cols]


# Save to Excel
merge_df.to_excel(
    r"D:\Trishakti\Projects\RPA\track_stock_price\open_and_completed_with_rmName.xlsx", 
    index=False
)