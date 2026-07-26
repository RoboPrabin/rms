import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from datetime import date
from sqlalchemy import create_engine
from utils import helper

intranet_engine = helper.get_holding_engine()

START_DATE = date(2025, 7, 17)
END_DATE = date(2026, 7, 16)

def fetch_floorsheet_data(start_date, end_date):
    query = """
        SELECT f.*
        FROM new_floorsheet f
        WHERE DATE(f.uploaded_at) BETWEEN %s AND %s
        ORDER BY f.uploaded_at DESC;
    """
    return pd.read_sql(query, intranet_engine, params=(start_date, end_date))

def compute_branch_summary(df):
    if "branch" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    dhangadhi_mask = df["branch"].astype(str).str.contains(r"Dhangadhi|^DHI$", case=False, na=False)
    if dhangadhi_mask.any():
        df.loc[dhangadhi_mask, "branch"] = "DHI"

    df["amount"] = pd.to_numeric(df["amount"], errors='coerce').fillna(0)

    def branch_summary_func(g):
        buy = g["transaction_type"] == "Buy"
        sell = g["transaction_type"] == "Sell"
        return pd.Series({
            "buyer_count": g.loc[buy, "clientcode"].nunique(),
            "seller_count": g.loc[sell, "clientcode"].nunique(),
            "both_traders": g.groupby("clientcode")["transaction_type"].nunique().eq(2).sum(),
            "purchase_turnover": g.loc[buy, "amount"].sum(),
            "sales_turnover": g.loc[sell, "amount"].sum(),
            "total": g["amount"].sum(),
        })

    df2 = (
        df.groupby("branch", group_keys=False, observed=True)
        .apply(lambda g: branch_summary_func(g), include_groups=False)
        .reset_index()
    )

    if "DHI" not in df2["branch"].values:
        zero_row = pd.DataFrame([{
            "branch": "DHI",
            "buyer_count": 0, "seller_count": 0, "both_traders": 0,
            "purchase_turnover": 0, "sales_turnover": 0, "total": 0,
        }])
        df2 = pd.concat([df2, zero_row], ignore_index=True)

    total_turnover = df2["total"].sum()
    df2["%"] = (df2["total"] / total_turnover * 100).round(2)

    df2.rename(columns={
        "total": "Total",
        "sales_turnover": "Sales Turnover",
        "purchase_turnover": "Purchase Turnover",
        "both_traders": "Both Traders",
        "seller_count": "Total Sellers",
        "buyer_count": "Total Buyers",
        "branch": "Branch",
        "%": "Branch Contribution %"
    }, inplace=True)

    df2 = df2.sort_values(by="Total", ascending=False)
    df2 = df2.round(2)

    numeric_cols = df2.select_dtypes(include=["int64", "float64"]).columns
    total_row = df2[numeric_cols].sum()
    total_row["Branch"] = "TOTAL"
    df2 = pd.concat([df2, pd.DataFrame([total_row])], ignore_index=True)

    df2.loc[df2["Branch"] == "TOTAL", "Branch Contribution %"] = 100.0

    column_order = ["Branch", "Total Buyers", "Total Sellers", "Both Traders", "Purchase Turnover", "Sales Turnover", "Total", "Branch Contribution %"]
    df2 = df2[column_order]
    df2.reset_index(drop=True, inplace=True)
    df2.index = df2.index + 1

    return df2

def main():
    print(f"Fetching floorsheet data from {START_DATE} to {END_DATE}...")
    df = fetch_floorsheet_data(START_DATE, END_DATE)

    if df.empty:
        print("No data found.")
        return

    print(f"Total rows: {len(df)}")
    print("Computing branch summary...")
    branch_summary = compute_branch_summary(df)

    output_file = "Branch_Summary_2025-07-17_to_2026-07-16.xlsx"
    branch_summary.to_excel(output_file, index=True)
    print(f"Branch summary exported to: {output_file}")

if __name__ == "__main__":
    main()
