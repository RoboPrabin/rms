from datetime import date, timedelta
import re
import pandas as pd
import requests
import streamlit as st
from config import config
from pages.BasePage import BasePage
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import auth_utils, helper


@st.cache_data(ttl=3600)
def fetch_client_rm_map_cached():
    query = """SELECT "clientName", "clientCode", "rmName" FROM client_rm_map"""
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
            return pd.DataFrame(results, columns=["Client Name", "Client Code", "BRO"])
        conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")


@st.cache_data(ttl=3600)
def fetch_kyc_cached():
    query = """SELECT clientfullname, clientmembercode, clientbranch from kyc"""
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
            return pd.DataFrame(results, columns=["Client Name", "Client Code", "Branch"])
        conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")


@st.cache_data(ttl=600)
def get_jwt_token_cached():
    return db.get_jwt_token()


@st.cache_data(ttl=3600)
def get_ledger_cached(token, ac_code, date_from, date_to):
    resp = requests.get(
        config.LEDGER_API,
        headers={"Authorization": f"Bearer {token}"},
        params={"acCode": ac_code, "dateFrom": date_from, "dateTo": date_to},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()


def extract_entries(entries, keyword):
    extracted = []
    total = 0
    with_code = 0
    for entry in entries:
        particulars = entry.get("particulars", "")
        if keyword in particulars.lower():
            total += 1
            m = re.search(r'\[(.*?)\]', particulars)
            code = m.group(1) if m else None
            if code:
                with_code += 1
                extracted.append({
                    "Client Code": code,
                    "drAmount": entry.get("drAmount"),
                    "Clearance Date": entry.get("clearanceDate"),
                    "Transaction Date": entry.get("transactionDate")
                })
    return extracted, total, with_code


def build_summary(df, df_kyc, df_rm_map, amount_label):
    df = df.merge(df_rm_map[['Client Code', 'Client Name', 'BRO']], on="Client Code", how="left")
    df[['Client Name', 'BRO']] = df[['Client Name', 'BRO']].fillna("N/A")
    df = df.drop(columns=['Client Name']).merge(
        df_kyc[['Client Code', 'Client Name', 'Branch']], on="Client Code", how="left"
    )
    df['BRO'] = df['BRO'].fillna("N/A")
    df['Branch'] = df['Branch'].str.upper().str.strip()
    df['Client Name'] = df['Client Name'].str.upper().str.strip()
    df.rename(columns={'drAmount': amount_label}, inplace=True)
    df.drop(columns=['Clearance Date', 'Transaction Date'], inplace=True)
    cols = ['BRO', 'Client Code', 'Client Name', 'Branch', amount_label]
    df = df[cols].sort_values(by="BRO")

    bro = df.groupby('BRO')[amount_label].sum().reset_index().sort_values(by=amount_label, ascending=False)
    branch = df.groupby('Branch')[amount_label].sum().reset_index().sort_values(by=amount_label, ascending=False)
    return df, bro, branch


class CashInOut(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin("-4rem")
        st.session_state.active_menu = "account"
        st.set_page_config(page_title="Cash In/Out", page_icon="📖", layout="wide")
        st.header("📖 Cash In/Out", anchor=False)
        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())

    def show_expander_with_date_range(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        with st.expander("Filter Date Range", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("From Date", value=yesterday)
            with col2:
                to_date = st.date_input("To Date", value=today)

            if st.button("Fetch Data", icon="🧲"):
                from_str = from_date.strftime("%Y-%m-%d")
                to_str = to_date.strftime("%Y-%m-%d")
                with st.container(border=True):
                    self.fetch_data_logic(from_date=from_str, to_date=to_str)
                st.toast("Data fetched successfully.", icon="✅")

    def fetch_data_logic(self, from_date, to_date):
        token = get_jwt_token_cached()
        ledger_data = get_ledger_cached(token=token, ac_code="1020201", date_from=from_date, date_to=to_date)
        entries = ledger_data.get("data", [])

        df_kyc = fetch_kyc_cached()
        df_rm_map = fetch_client_rm_map_cached()

        cash_entries, _, _ = extract_entries(entries, "received")
        if cash_entries:
            df_cash, bro_cash, branch_cash = build_summary(
                pd.DataFrame(cash_entries), df_kyc, df_rm_map, "Cash In Amount"
            )
            self.show_tabbed_dataframes(df_cash, bro_cash, branch_cash, "Cash In", "Cash In Amount")

        st.markdown("---")
        cheque_entries, total_cheque, with_code = extract_entries(entries, "cheque")
        st.info(
            f"Total entries with 'cheque': {total_cheque} | "
            f"With client code: {with_code} | Without client code: {total_cheque - with_code}"
        )
        if cheque_entries:
            df_cheque, bro_cheque, branch_cheque = build_summary(
                pd.DataFrame(cheque_entries), df_kyc, df_rm_map, "Cheque Amount"
            )
            self.show_tabbed_dataframes(df_cheque, bro_cheque, branch_cheque, "Cheque Clearing", "Cheque Amount")
        else:
            st.info("No cheque clearing entries found for the selected date range.", icon="ℹ️")

    def show_tabbed_dataframes(self, df_final, bro_summary, branch_summary, label, amount_col):
        st.metric(f"Total {label}", value=f"Rs. {df_final[amount_col].sum():,.2f}")
        tabs = st.tabs(["BRANCH", "BRO", "ALL"])

        with tabs[0]:
            branch_summary = branch_summary.reset_index(drop=True)
            branch_summary.index += 1
            st.dataframe(branch_summary.style.format({amount_col: "{:,.2f}"}), use_container_width=True)

        with tabs[1]:
            bro_summary = bro_summary.reset_index(drop=True)
            bro_summary.index += 1
            st.dataframe(bro_summary.style.format({amount_col: "{:,.2f}"}), use_container_width=True)

        with tabs[2]:
            df_final = df_final.reset_index(drop=True)
            df_final.index += 1
            st.dataframe(df_final.style.format({amount_col: "{:,.2f}"}), use_container_width=True)

    def render_page(self):
        self.show_expander_with_date_range()


if __name__ == "__main__":
    CashInOut().render_page()
