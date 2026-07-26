import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from datetime import date
from db import db
from sqlalchemy import create_engine
from utils import helper

intranet_engine = helper.get_holding_engine()

START_DATE = date(2025, 7, 17)
END_DATE = date(2026, 7, 16)

def fetch_floorsheet_data(start_date, end_date):
    query = """
        SELECT f.*,
            COALESCE(m."rmName", 'N/A') AS "rmName"
        FROM floorsheet f
        LEFT JOIN client_rm_map m ON f.clientcode = m."clientCode"
        WHERE DATE(f.uploaded_at) BETWEEN %s AND %s
        ORDER BY f.uploaded_at DESC;
    """
    return pd.read_sql(query, intranet_engine, params=(start_date, end_date))

def compute_bro_summary(df, nepse_turnover):
    df["is_buyer"] = (df["transaction_type"] == "Buy").astype(int)
    df["is_seller"] = (df["transaction_type"] == "Sell").astype(int)
    df["purchase_turnover"] = df.apply(lambda row: row["amount"] if row["transaction_type"] == "Buy" else 0, axis=1)
    df["sales_turnover"] = df.apply(lambda row: row["amount"] if row["transaction_type"] == "Sell" else 0, axis=1)
    df["total"] = df["purchase_turnover"] + df["sales_turnover"]

    grouped = df.groupby("rmName").agg(
        buyer_count=("is_buyer", "sum"),
        seller_count=("is_seller", "sum"),
        purchase_turnover=("purchase_turnover", "sum"),
        sales_turnover=("sales_turnover", "sum"),
        total=("total", "sum")
    ).reset_index()

    buyers = df[df["is_buyer"] == 1].groupby("rmName")["clientcode"].nunique()
    sellers = df[df["is_seller"] == 1].groupby("rmName")["clientcode"].nunique()
    both = df.groupby("rmName")["clientcode"].apply(
        lambda x: len(
            set(df[(df["rmName"] == x.name) & (df["is_buyer"] == 1)]["clientcode"]) &
            set(df[(df["rmName"] == x.name) & (df["is_seller"] == 1)]["clientcode"])
        )
    )

    grouped = grouped.merge(buyers.rename("unique_buyers"), on="rmName", how="left")
    grouped = grouped.merge(sellers.rename("unique_sellers"), on="rmName", how="left")
    grouped["both_traders"] = both.values

    grouped.drop(columns=['buyer_count', 'seller_count'], inplace=True)
    grouped.rename(columns={
        "rmName": "BRO",
        "unique_buyers": "Total Buyers",
        "unique_sellers": "Total Sellers",
        "both_traders": "Both Traders",
        "purchase_turnover": "Purchase Turnover",
        "sales_turnover": "Sales Turnover",
        "total": "Total"
    }, inplace=True)

    grouped["Contribution to NEPSE"] = ((grouped["Total"] / nepse_turnover) * 100 / 2 / 2).round(4)

    grouped = grouped.sort_values(by="Total", ascending=False)
    grouped = grouped.round(2)

    # Add total row before formatting
    total_row = pd.DataFrame([{
        "BRO": "TOTAL",
        "Total Buyers": grouped["Total Buyers"].sum(),
        "Total Sellers": grouped["Total Sellers"].sum(),
        "Both Traders": grouped["Both Traders"].sum(),
        "Purchase Turnover": grouped["Purchase Turnover"].sum(),
        "Sales Turnover": grouped["Sales Turnover"].sum(),
        "Total": grouped["Total"].sum(),
        "Contribution to NEPSE": 100.0
    }])
    grouped = pd.concat([grouped, total_row], ignore_index=True)

    # Format Contribution to NEPSE as percentage string
    grouped["Contribution to NEPSE"] = grouped["Contribution to NEPSE"].map(lambda x: f"{x:.4f} %")

    column_order = ['BRO', 'Total Buyers', 'Total Sellers', 'Both Traders', 'Purchase Turnover', 'Sales Turnover', 'Total', 'Contribution to NEPSE']
    grouped = grouped[column_order]
    grouped.index = grouped.index + 1

    return grouped

def main():
    print(f"Fetching top brokers data from {START_DATE} to {END_DATE}...")
    top_brokers_df = db.fetch_top_brokers_by_date(START_DATE, END_DATE)

    if top_brokers_df.empty:
        print("No top brokers data found.")
        return

    cols_to_convert = ["totalAmount", "buyerAmount", "sellerAmount", "matchingAmount"]
    for col in cols_to_convert:
        top_brokers_df[col] = pd.to_numeric(top_brokers_df[col].astype(str).str.replace(",", "", regex=False), errors='coerce')

    nepse_turnover = top_brokers_df["totalAmount"].sum() / 2
    print(f"NEPSE Total Turnover (BUY/SELL): {nepse_turnover:,.2f}")

    tri_row = top_brokers_df[top_brokers_df["name"].str.strip().str.lower() == "trishakti securities public limited"]
    trishakti_code = str(int(tri_row["number"].iloc[0])) if not tri_row.empty else None
    print(f"Trishakti Code: {trishakti_code}")

    print(f"Fetching floorsheet data from {START_DATE} to {END_DATE}...")
    df = fetch_floorsheet_data(START_DATE, END_DATE)

    if df.empty:
        print("No floorsheet data found.")
        return

    print(f"Total rows fetched: {len(df)}")

    trishakti_market_share = 0
    if trishakti_code:
        df["buyerbrokingfirmcode"] = df["buyerbrokingfirmcode"].astype(str)
        df["sellerbrokingfirmcode"] = df["sellerbrokingfirmcode"].astype(str)
        df["amount"] = pd.to_numeric(df["amount"], errors='coerce').fillna(0)
        trishakti_floor = df[(df["buyerbrokingfirmcode"] == trishakti_code) | (df["sellerbrokingfirmcode"] == trishakti_code)]
        trishakti_turnover = trishakti_floor["amount"].sum()
        trishakti_market_share = ((trishakti_turnover / nepse_turnover) * 100) / 2
        print(f"Trishakti Turnover: {trishakti_turnover:,.2f}")
        print(f"Trishakti Market Share: {trishakti_market_share:.4f} %")

    print("Computing BRO summary...")
    bro_summary = compute_bro_summary(df, nepse_turnover)

    output_file = "BRO_Summary_2025-07-17_to_2026-07-16.xlsx"
    bro_summary.to_excel(output_file, index=True)
    print(f"BRO summary exported to: {output_file}")

if __name__ == "__main__":
    main()
