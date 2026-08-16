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

def compute_daily_branch_summary(df):
    if "branch" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    df = df.copy()
    dhangadhi_mask = df["branch"].astype(str).str.contains(r"Dhangadhi|^DHI$", case=False, na=False)
    if dhangadhi_mask.any():
        df.loc[dhangadhi_mask, "branch"] = "DHI"

    df["amount"] = pd.to_numeric(df["amount"], errors='coerce').fillna(0)
    df["trade_date"] = pd.to_datetime(df["uploaded_at"]).dt.date

    def daily_branch_func(g):
        buy = g["transaction_type"] == "Buy"
        sell = g["transaction_type"] == "Sell"
        return pd.Series({
            "buyer_count": g.loc[buy, "clientcode"].nunique(),
            "seller_count": g.loc[sell, "clientcode"].nunique(),
            "both_traders": g.groupby("clientcode")["transaction_type"].nunique().eq(2).sum(),
            "purchase_turnover": g.loc[buy, "amount"].sum(),
            "sales_turnover": g.loc[sell, "amount"].sum(),
            "total": g["amount"].sum(),
            "trade_count": len(g),
        })

    daily_df = (
        df.groupby(["trade_date", "branch"], group_keys=False, observed=True)
        .apply(lambda g: daily_branch_func(g), include_groups=False)
        .reset_index()
    )

    daily_df.rename(columns={
        "trade_date": "Date",
        "branch": "Branch",
        "buyer_count": "Buyers",
        "seller_count": "Sellers",
        "both_traders": "Both Traders",
        "purchase_turnover": "Purchase Turnover",
        "sales_turnover": "Sales Turnover",
        "total": "Total",
        "trade_count": "Trade Count",
    }, inplace=True)

    daily_df = daily_df.sort_values(by=["Date", "Total"], ascending=[True, False])
    daily_df = daily_df.round(4)
    daily_df.reset_index(drop=True, inplace=True)
    daily_df.index = daily_df.index + 1

    return daily_df

def compute_overall_branch_summary(daily_df):
    if daily_df.empty:
        return pd.DataFrame()

    agg_df = (
        daily_df.groupby("Branch", observed=True)
        .agg({
            "Buyers": "sum",
            "Sellers": "sum",
            "Both Traders": "sum",
            "Purchase Turnover": "sum",
            "Sales Turnover": "sum",
            "Total": "sum",
            "Trade Count": "sum",
            "Date": "nunique",
        })
        .reset_index()
    )

    agg_df.rename(columns={"Date": "Trading Days"}, inplace=True)

    if "DHI" not in agg_df["Branch"].values:
        zero_row = pd.DataFrame([{
            "Branch": "DHI",
            "Buyers": 0, "Sellers": 0, "Both Traders": 0,
            "Purchase Turnover": 0, "Sales Turnover": 0,
            "Total": 0, "Trade Count": 0, "Trading Days": 0,
        }])
        agg_df = pd.concat([agg_df, zero_row], ignore_index=True)

    total_turnover = agg_df["Total"].sum()
    if total_turnover > 0:
        agg_df["Branch Contribution %"] = (agg_df["Total"] / total_turnover * 100).round(4)
    else:
        agg_df["Branch Contribution %"] = 0.0

    agg_df = agg_df.sort_values(by="Total", ascending=False)
    agg_df = agg_df.round(4)

    numeric_cols = agg_df.select_dtypes(include=["int64", "float64"]).columns
    total_row = agg_df[numeric_cols].sum()
    total_row["Branch"] = "TOTAL"
    agg_df = pd.concat([agg_df, pd.DataFrame([total_row])], ignore_index=True)

    agg_df.loc[agg_df["Branch"] == "TOTAL", "Branch Contribution %"] = 100.0

    column_order = ["Branch", "Trading Days", "Buyers", "Sellers", "Both Traders",
                    "Purchase Turnover", "Sales Turnover", "Total", "Trade Count", "Branch Contribution %"]
    agg_df = agg_df[column_order]
    agg_df.reset_index(drop=True, inplace=True)
    agg_df.index = agg_df.index + 1

    return agg_df

def main():
    print(f"Fetching floorsheet data from {START_DATE} to {END_DATE}...")
    df = fetch_floorsheet_data(START_DATE, END_DATE)

    if df.empty:
        print("No data found.")
        return

    print(f"Total rows: {len(df)}")
    print("Computing daily branch summaries...")
    daily_df = compute_daily_branch_summary(df)

    print("Aggregating overall branch summary...")
    overall_df = compute_overall_branch_summary(daily_df)

    output_file = "Branch_Summary_2025-07-17_to_2026-07-16.xlsx"
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        overall_df.to_excel(writer, sheet_name="Branch Summary", index=True)
        daily_df.to_excel(writer, sheet_name="Daily Branch Breakdown", index=True)
    print(f"Branch summary exported to: {output_file}")

if __name__ == "__main__":
    main()
