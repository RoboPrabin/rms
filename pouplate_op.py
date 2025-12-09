import pandas as pd

# Load both files
open_df = pd.read_excel(r"D:\Trishakti\Projects\RPA\track_stock_price\open.xlsx")
completed_df = pd.read_excel(r"D:\Trishakti\Projects\RPA\track_stock_price\completed.xlsx")

# Step 1: Compute average tradePrice per clientMemberCode + symbol in completed file
avg_prices = (
    completed_df.groupby(["clientMemberCode", "symbol"])["tradePrice"]
    .mean()
    .reset_index()
    .rename(columns={"tradePrice": "avgOrderPrice"})
)

# Step 2: Merge avg prices into open_df
merged = open_df.merge(avg_prices, on=["clientMemberCode", "symbol"], how="left")

# Step 3: Replace orderPrice = 0.00 with avgOrderPrice (if available)
merged["orderPrice"] = merged.apply(
    lambda row: row["avgOrderPrice"] if row["orderPrice"] == 0 and pd.notnull(row["avgOrderPrice"]) else row["orderPrice"],
    axis=1
)

# Step 4: Round the entire column to 2 decimals
merged["orderPrice"] = merged["orderPrice"].round(2)

# Step 5: Drop helper column
merged = merged.drop(columns=["avgOrderPrice"])

open_df = merged

# Mapping dictionary: completed_df column → open_df column
column_mapping = {
    "id": "id",
    "clientMemberCode": "clientMemberCode",
    "symbol": "symbol",
    "securityName": "securityName",
    "tradeTime": "orderTime",
    "exchangeOrderId": "exchangeOrderId",
    "buyOrSell": "buyOrSell",
    "tradePrice": "orderPrice",
    "tradedQuantity": "orderQuantity",
    "displayName": "displayName",
    "activeStatus": "activeStatus",
}

# Rename completed_df columns
completed_df = completed_df.rename(columns=column_mapping)

# Keep only the mapped columns that exist in completed_df
available_cols = [col for col in column_mapping.values() if col in completed_df.columns]
completed_df = completed_df[available_cols]

# Step 3: Concatenate row-wise (append)
combined_df = pd.concat([open_df, completed_df], ignore_index=True)
combined_df.drop(columns=['id', 'exchangeOrderId', 'displayActiveStatus', 'orderPlacedBy', 'displayName'], inplace=True)
# completed_df.loc[completed_df['activeStatus'] == "COMPLETED", 'totalTradedQuantity'] = completed_df['orderQuantity']
combined_df['amount'] = combined_df['buyOrSell'].astype(float) * combined_df['orderPrice'].astype(float)  
combined_df.loc[combined_df['activeStatus'] == "COMPLETED", 'totalTradedQuantity'] = combined_df['orderQuantity']


combined_df.to_excel(r"D:\Trishakti\Projects\RPA\track_stock_price\open_and_completed.xlsx", index=False)