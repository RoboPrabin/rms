# import test_copy
from calculation import interest_calculation
from utils.formatting import *
from datetime import date
from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import helper
import requests
from config import config
# ---------------- CONFIG ----------------
BASE_API = "https://dgtrade.trishakti.com.np:8080/bom/"
LOGIN_API = BASE_API + "tp-data/authenticate"
AC_CODE_API = BASE_API + "tp-data/account/by-nepse"
LEDGER_API = BASE_API + "tp-data/account/ledger"

@st.cache_data(ttl=3200)
def get_rm_and_client_name(client_code):
    rm_name, client_name = db.get_table_rm_child_map_with_client_code(client_code=client_code)
    return rm_name, client_name

# ---------------- API HELPERS ----------------
def get_token(username, password):
    resp = requests.post(
        LOGIN_API,
        json={"userName": username, "password": password},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json().get("token")


def get_account_code(token, nepse_code):
    resp = requests.get(
        AC_CODE_API,
        headers={"Authorization": f"Bearer {token}"},
        params={"nepseCode": nepse_code},
        timeout=30
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        return resp.status_code

def get_ledger(token, ac_code, date_from, date_to):
    resp = requests.get(
        LEDGER_API,
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


class InterestCalculation:
    
    def __init__(self):
        # helper.eliminate_top_padding()
        st.session_state.active_menu = ""
        st.set_page_config(page_title="Interest Calculation", page_icon="🧩", layout="wide")
        # app_state.restore_state_from_query_params()
        # app_state.sync_query_params_from_session()
        # app_state.check_authenticaiton_state()
        # THE GATEKEEPER - Must be the first line of code after imports
        app_state.enforce_authentication()
        app_state.sync_local_storage_to_session()
        self.username, self.role, self.branch = app_state.get_current_user_info()
        st.header("🧩 Interest Calculation", anchor=False)

        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())
        self.dg_api_token = db.get_jwt_token()

    def render_page(self):
        with st.form("ledger_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                client_code = st.text_input("Client Code (NEPSE)", value=st.session_state.get('client_code', '')).upper()
                

            with col2:
                from_date = st.date_input(
                    "From Date",
                    value=date(2025, 7, 17),
                    max_value=date.today()
                )

            with col3:
                to_date = st.date_input(
                    "To Date",
                    value=date.today(),
                    min_value=from_date,
                    max_value=date.today()
                )

            if st.form_submit_button("Fetch Ledger", type="primary"):
                if not client_code:
                    st.error("Client code is required.")
                    return

                with st.spinner("Fetching ledger…"):
                    try:
                        from_date_str = from_date.strftime("%Y-%m-%d")
                        to_date_str = to_date.strftime("%Y-%m-%d")

                        while True:
                            token = db.get_jwt_token()
                            ac_code = get_account_code(token, client_code)
                            if ac_code == 401:
                                new_token = get_token(username=config.dg_api_userName, password=config.dg_api_password)
                                db.store_jwt_token(jwt_value=new_token)
                            elif ac_code != 401:
                                break
                          
                        ledger = get_ledger(token, ac_code, from_date_str, to_date_str)
                        st.session_state["ledger_dialog_data"] = ledger
                        rm_name, client_name = get_rm_and_client_name(client_code)
                        st.session_state['rm_name'] = rm_name
                        st.session_state['client_name'] = client_name
                        st.session_state['client_code'] = client_code
                    except Exception as e:
                        st.error(f"Client Code: '{client_code.upper()}' not found")
                        return

        if "ledger_dialog_data" in st.session_state:
            ledger = st.session_state["ledger_dialog_data"]
            # st.divider()
            # st.subheader(f"📒 Opening Summary", anchor=False)
            st.badge(f"{st.session_state['client_name']} [{st.session_state.get('client_code', '')}] || {st.session_state.get('rm_name', 'N/A')}", color="green")
        
            ubilled = ledger.get("ubilledTransactions", [])

            adjusted_balance = 0.0
            if ubilled:
                df_ub = pd.DataFrame(ubilled)
                if "credit" in df_ub.columns:
                    total_credit = df_ub["credit"].sum()
                    if ledger.get('balanceType', '-') == 'CR':
                        adjusted_balance = "{:,.2f} CR".format(float(ledger.get('balance', '0.00')) + total_credit)
                    else:
                        adjusted_balance = "{:,.2f} DR".format(float(ledger.get('balance', '0.00')) - total_credit)

                    # adjusted_balance = total_credit - float(ledger.get('balance', '0.00'))

                    # <div>BRO: {st.session_state.get('rm_name', 'N/A')}</div>
            st.markdown(
            f"""
            <div style="display: flex;font-weight: normal;justify-content: space-between; font-size: 1rem; color: #6b7280; line-height: 2; margin-bottom: 15px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
                <div>
                    <div>Adjusted Balance: {adjusted_balance}</div>
                    <div>Collateral: {float(ledger.get('collateral', 0)):,.2f}</div>
                </div>
                <div style="text-align: right; color:#32a852;">
                    <br>
                    <div>Balance: {float(ledger.get('balance', 0)):,.2f} {ledger.get('balanceType', '-')}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

            data_rows = ledger.get("data", [])
            if data_rows:
                df = pd.DataFrame(data_rows)
                ordered_cols = [
                    "transactionDate", "clearanceDate", "referenceNo",
                    "voucherNo", "particulars", "dr", "cr", "balance", "balanceType"
                ]
                number_cols = ["Dr", "Cr", "Balance"]
                df = df[[c for c in ordered_cols if c in df.columns]]
                df_for_ageing = df
                df.columns = df.columns.str.upper()
                df.rename(columns=lambda x: helper.camel_to_title(x), inplace=True)
                df = coerce_numeric_columns(df, number_cols)
                has_searched = False
                df.rename(columns={"Transactiondate": "Transaction Date", "Clearancedate": "Clearance Date", "Referenceno": "Reference No", "Balancetype": "Balance Type"}, inplace=True)
                search_query = st.text_input("Search by Particulars", width=400).strip()
                if search_query:
                    has_searched = True
                    df = df[df["Particulars"].str.contains(search_query, case=False, na=False)]
                if has_searched:
                    total_cr = df['Cr'].sum()
                    st.badge(f"Total Cr Amount: {total_cr:,.2f}")
                styled_df = df.style.format(accounting_format, subset=number_cols).map(highlight_negative, subset=number_cols)
                st.subheader("📒 Main Ledger", anchor=False)
                st.dataframe(styled_df, width='stretch', hide_index=True)
                
                
                st.divider()
                st.subheader("📄 Bill Ageing", anchor=False)
                with st.spinner(text="Calculating bill ageing",show_time=True):
                    df_new = interest_calculation.calculate(df=df_for_ageing)
                    df_new["Ageing"] = pd.to_timedelta(df_new["Ageing"], errors="coerce")
                    df_new["Ageing"] = df_new["Ageing"].dt.days.where(df_new["Ageing"].notna(), df_new["Ageing"])

                    # Extract only the number of days
                    
                    df_new.index = df_new.index + 1
                    # print(df_new.columns)
                    number_cols = ["Dr", "Cr"]

                    # Force conversion to numeric, invalid parsing becomes NaN
                    df_new[number_cols] = df_new[number_cols].apply(pd.to_numeric, errors="coerce")
                    df_new['Interest Rate'] = None
                    df_new['Interest Amount'] = None
                    df_new["Action"] = None
                    df_new['Particulars'] = df_new['Particulars'].fillna("None")

                    # Apply slabs
                    # df_new.loc[df_new["Ageing"].between(0, 7, inclusive="both"), "Interest Rate"] = 10
                    # df_new.loc[df_new["Ageing"].between(8, 15, inclusive="both"), "Interest Rate"] = 12
                    # df_new.loc[df_new["Ageing"].between(16, 30, inclusive="both"), "Interest Rate"] = 18
                    # 0–7 days
                    df_new.loc[df_new["Ageing"].between(0, 7, inclusive="both"),["Interest Rate", "Action"]] = [10, "Interest Zone"]
                    # 8–15 days
                    df_new.loc[df_new["Ageing"].between(8, 15, inclusive="both"),["Interest Rate", "Action"]] = [12, "Interest Zone"]
                    # 16–30 days
                    df_new.loc[df_new["Ageing"].between(16, 30, inclusive="both"),["Interest Rate", "Action"]] = [18, "Interest Zone"]

                    df_new.loc[df_new["Ageing"] > 30, "Action"] = "Need Cash / Sell Stocks"
                    df_new["Interest Amount"] = (df_new["Dr"].fillna(0) * df_new["Interest Rate"] / 100)

                    styled_df = df_new.style.format({
                        "Ageing": lambda x: "-" if pd.isna(x) else f"{int(x)}",
                        "Interest Amount": lambda x: "-" if pd.isna(x) else f"{float(x):,.2f}",
                        "Dr": accounting_format,
                        "Cr": accounting_format
                    })
                    st.dataframe(styled_df)
            else:
                st.warning("No ledger transactions found.")
    
    
    
    # def render_page(self):
    #     col1, col2, col3 = st.columns(3)
    #     with col1:
    #         client_code = st.text_input("Client Code")
    #     with col2:
    #         date_from = st.date_input("From Date", value='2025-07-17')
    #     with col3:
    #         date_to = st.date_input("To Date", value='today')
    #     submit_btn = st.button("Submit")
    #     if submit_btn:
    #         acc_code = get_account_code(token=self.dg_api_token, nepse_code=client_code.upper())
    #         response = get_ledger(token=self.dg_api_token, ac_code=acc_code, date_from=date_from, date_to=date_to)
    #         df = pd.DataFrame(response['data'])
    #         st.dataframe(df)
    #         st.json(response)
   



if __name__ == "__main__":
    InterestCalculation().render_page()