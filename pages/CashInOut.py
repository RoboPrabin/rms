from datetime import date, timedelta
import re
from time import sleep
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
        # Establish connection
        conn = db.get_connection()
        
        with conn.cursor() as cur:
            cur.execute(query)
            # Fetch all rows as a list of DictRow objects
            results = cur.fetchall()
            df = pd.DataFrame(results, columns=["Client Name", "Client Code", "BRO"])
            return df
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
@st.cache_data(ttl=3600)
def fetch_kyc_cached():
    query = """SELECT clientfullname, clientmembercode, clientbranch from kyc"""
    
    try:
        # Establish connection
        conn = db.get_connection()
        
        with conn.cursor() as cur:
            cur.execute(query)
            # Fetch all rows as a list of DictRow objects
            results = cur.fetchall()
            df = pd.DataFrame(results, columns=["Client Name", "Client Code", "Branch"])
            return df
           
                
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to database: {e}")


def get_ledger(token, ac_code, date_from, date_to):
    resp = requests.get(
        config.LEDGER_API,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "acCode": ac_code,
            "dateFrom": date_from,
            "dateTo": date_to
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=3600)
def get_jwt_token_cached():
    token = db.get_jwt_token()
    return token



class CashInOut(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin("-4rem")
        st.session_state.active_menu = "account"
        st.set_page_config(page_title="Cash In/Out", page_icon="📖", layout="wide")
        st.header("📖 Cash In/Out", anchor=False)

        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())
        self.session_ids = None


    def show_expander_with_date_range(self):
        st.session_state.from_str =   date.today() - timedelta(days=1)
        st.session_state.to_str = date.today()
        with st.expander("Filter Date Range", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                # Default from_date = yesterday
                default_from = date.today() - timedelta(days=1)
                from_date = st.date_input("From Date", value=default_from)
            with col2:
                # Default to_date = today
                default_to = date.today()
                to_date = st.date_input("To Date", value=default_to)

            if st.button("Fetch Data", icon="🧲"):
                # Format dates as YYYY-MM-DD
                from_str = from_date.strftime("%Y-%m-%d")
                to_str = to_date.strftime("%Y-%m-%d")
                st.session_state.from_str = from_str
                st.session_state.to_str = to_str
        with st.container(border=True):
            self.fetch_data_logic(from_date=st.session_state.from_str, to_date=st.session_state.to_str)
        st.toast("Data fetched successfully.", icon="✅")

    
    def fetch_data_logic(self, from_date, to_date):
        token = get_jwt_token_cached()
        ledger_data = get_ledger(token=token, ac_code="1020201", date_from=from_date, date_to=to_date)
                
        extracted_list = []

        for entry in ledger_data.get("data", []):
            particulars = entry.get("particulars", "")
            
            # Check for keyword 'received' (case-insensitive)
            if "received" in particulars.lower():
                # Regex to extract content inside square brackets
                client_code_match = re.search(r'\[(.*?)\]', particulars)
                client_code = client_code_match.group(1) if client_code_match else None
                
                extracted_list.append({
                    "Client Code": client_code,
                    "drAmount": entry.get("drAmount"),
                    "Clearance Date": entry.get("clearanceDate"),
                    "Transaction Date": entry.get("transactionDate")
                })
        # Create DataFrame and save to Excel
        df_client_transaction = pd.DataFrame(extracted_list)
        # get Client Code which is not null
        # 1. Filter to ensure we only have rows where 'Client Code' is not null
        df_client_transaction = df_client_transaction[df_client_transaction['Client Code'].notna()]

        # 2. If you want to ensure it's not an empty string (common in messy data)
        df_client_transaction = df_client_transaction[df_client_transaction['Client Code'] != ""]

        df_kyc = fetch_kyc_cached()
        df_client_rm_map = fetch_client_rm_map_cached()


        # 2. Perform the merge
        # We specify only the necessary columns from df_rm_map to keep the dataframe clean
        df_merged = df_client_transaction.merge(
            df_client_rm_map[['Client Code', 'Client Name', 'BRO']], 
            on="Client Code", 
            how="left"
        )
        # 3. Fill missing matches with "N/A"
        df_merged[['Client Name', 'BRO']] = df_merged[['Client Name', 'BRO']].fillna("N/A")

        # 4. Optional: Reorder columns for a cleaner look
        cols = ["Client Code", "Client Name", "BRO", "drAmount", "Clearance Date", "Transaction Date"]
        df_final = df_merged[cols]

        # Drop Client Name before merge to avoid duplicates
        df_final = df_final.drop(columns=['Client Name'])

        df_final = df_final.merge(
            df_kyc[['Client Code', 'Client Name', 'Branch']],
            on="Client Code",
            how="left"
        )
        df_final['BRO'] = df_final['BRO'].fillna("N/A")
        df_final.sort_values(by="BRO", inplace=True)
        df_final['Branch'] = df_final['Branch'].str.upper().str.strip()
        df_final['Client Name'] = df_final['Client Name'].str.upper().str.strip()
        column_order = ['BRO', 'Client Code', 'Client Name', 'Branch', 'drAmount', 'Clearance Date', 'Transaction Date']
        df_final = df_final[column_order]
        df_final.rename(columns={'drAmount': 'Cash In Amount'}, inplace=True)
        df_final.drop(columns=['Clearance Date', 'Transaction Date'], inplace=True)
        bro_summary = df_final.groupby('BRO')['Cash In Amount'].sum().reset_index()
        bro_summary.sort_values(by='Cash In Amount', ascending=False, inplace=True)
        branch_summary = df_final.groupby('Branch')['Cash In Amount'].sum().reset_index()
        branch_summary.sort_values(by='Cash In Amount', ascending=False, inplace=True)

        self.show_tabbed_dataframes(df_final, bro_summary, branch_summary)



    def show_tabbed_dataframes(self, df_final: pd.DataFrame, bro_summary: pd.DataFrame, branch_summary: pd.DataFrame):
        # Metric with formatted sum
        st.metric("Total Cash In:", value=f"Rs. {df_final['Cash In Amount'].sum():,.2f}")

        tabs = st.tabs(["All", "BRO", "Branch"])

        with tabs[0]:
            df_final = df_final.reset_index(drop=True)
            df_final.index += 1
            st.dataframe(
                df_final.style.format({"Cash In Amount": "{:,.2f}"}),
                use_container_width=True
            )

        with tabs[1]:
            bro_summary = bro_summary.reset_index(drop=True)
            bro_summary.index += 1
            st.dataframe(
                bro_summary.style.format({"Cash In Amount": "{:,.2f}"}),
                use_container_width=True
            )

        with tabs[2]:
            branch_summary = branch_summary.reset_index(drop=True)
            branch_summary.index += 1
            st.dataframe(
                branch_summary.style.format({"Cash In Amount": "{:,.2f}"}),
                use_container_width=True
            )

    def render_page(self):
        self.show_expander_with_date_range()

if __name__ == "__main__":
    CashInOut().render_page()