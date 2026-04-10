from datetime import date, datetime, timedelta
import re
from time import sleep
import pandas as pd
import psycopg2
import requests
import streamlit as st
from config import config
from pages.BasePage import BasePage
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import auth_utils, helper
import psycopg2.extras


@st.cache_data(ttl=3600)
def get_nepse_trade_days(from_date: str = None, to_date: str = None) -> int:
    conn = db.get_connection()
    cur = conn.cursor()

    query = "SELECT COUNT(DISTINCT CAST(tradetime AS DATE)) FROM floorsheet"
    params = []
    if from_date and to_date:
        query += " WHERE CAST(tradetime AS DATE) BETWEEN %s AND %s"
        params.extend([from_date, to_date])

    cur.execute(query, params)
    total_nepse_trade_days = cur.fetchone()[0]

    cur.close()
    conn.close()
    return total_nepse_trade_days


def get_all_floorsheet_with_days(client_code: str, from_date: str = None, to_date: str = None):
    conn = db.get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Query client data
    query_client = """
        SELECT clientname, clientcode, symbol, quantity, rate, amount, branch, transaction_type, tradetime
        FROM floorsheet
        WHERE clientcode = %s
    """
    params_client = [client_code]
    if from_date and to_date:
        query_client += " AND CAST(tradetime AS DATE) BETWEEN %s AND %s"
        params_client.extend([from_date, to_date])

    cur.execute(query_client, params_client)
    rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])

    # Convert tradetime text → datetime
    df["tradetime"] = pd.to_datetime(df["tradetime"], errors="coerce")

    # Compute total amount
    df["Total Amount"] = df["quantity"] * df["rate"]

    # Extract trade date
    df["trade_date"] = df["tradetime"].dt.date

    # Count client trade days
    total_client_trade_days = df["trade_date"].nunique()

    cur.close()
    conn.close()

    # Get cached NEPSE trade days
    total_nepse_trade_days = get_nepse_trade_days(from_date, to_date)

    return df, total_nepse_trade_days, total_client_trade_days


class TradeHistory(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin("-4rem")
        st.session_state.active_menu = "aml"
        st.set_page_config(page_title="Trade History", page_icon="🔎", layout="wide")
        st.header("🔎 Trade History", anchor=False)

        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())
        self.session_ids = None


    def show_expander_with_date_range(self):
        ready_to_find = False
        with st.expander("Filter Date Range", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                client_code = st.text_input("Client Code").upper()
            with col2:
                default_from = date(2025, 1, 17)
                default_from = datetime.strptime("2025-01-17", "%Y-%m-%d").date()
                from_date = st.date_input("From Date", value=default_from)
            with col3:
                to_date = st.date_input("To Date", value=datetime.today().date())

            if st.button("Fetch Data", icon="🧲"):
                if not client_code:
                    st.error("Please provide client Code", icon="❌")
                    st.stop()
                else:
                    ready_to_find = True

        if ready_to_find:
            df, nepse_days, client_days = get_all_floorsheet_with_days(client_code, from_date, to_date)
            if df.empty:
                st.info(f"Data not found", icon="ℹ️")
                st.stop()
            with st.container(border=True):
                # Metrics: total buy / total sell
                total_buy = df.loc[df["transaction_type"].str.lower() == "buy", "Total Amount"].sum()
                total_sell = df.loc[df["transaction_type"].str.lower() == "sell", "Total Amount"].sum()
                colm1, colm2 = st.columns(2)
                with colm1:
                    st.metric("🔴 Total Buy", f"Rs. {total_buy:,.2f}", border=True)
                with colm2:
                    st.metric("🟢 Total Sell", f"Rs. {total_sell:,.2f}",border=True)


                col1, col2 = st.columns(2)
                with col1:
                    st.metric("🔵 Total NEPSE Trade Days", nepse_days, border=True)
                with col2:
                    st.metric("🔵 Client Trade Days", client_days, border=True)

                # Format dataframe for display
                df_display = df.copy()
                df_display["Total Amount"] = df_display["Total Amount"].map(lambda x: f"{x:,.2f}")
                df_display["amount"] = df_display["amount"].map(lambda x: f"{x:,.2f}")
                df_display["rate"] = df_display["rate"].map(lambda x: f"{x:,.2f}")
                df_display["quantity"] = df_display["quantity"].map(lambda x: f"{x:,.2f}")
                df_display["tradetime"] = df_display["tradetime"].dt.strftime("%Y-%m-%d %I:%M:%S")
                df_display.reset_index(inplace=True, drop=True)
                df_display.index += 1
                df_display.rename(columns={
                    "clientname":"Client Name",
                    "clientcode":"Client Code",
                    "symbol":"Symbol",
                    "quantity":"Quantity",
                    "rate":"Rate",
                    "transaction_type": "Transaction Type",
                    "tradetime":"Trade Date/Time"
                }, inplace=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.badge(f"Total rows: {len(df_display):,.2f}")
                with col2:
                    unique_scripts = df_display['Symbol'].unique()
                    st.badge(f"Total Unique Scripts: {len(unique_scripts)}")
                st.dataframe(
                    df_display[["Client Name", "Client Code", "Symbol","Transaction Type", "Quantity", "Rate", "Total Amount",  "Trade Date/Time"]],
                    width='stretch'
                )
                st.toast(f"Data fetched successfully.", icon="✅")

    def render_page(self):
        self.show_expander_with_date_range()

if __name__ == "__main__":
    TradeHistory().render_page()