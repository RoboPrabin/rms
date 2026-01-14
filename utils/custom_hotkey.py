# custom_hotkey.py
from db import db
from utils import helper
from utils.formatting import *
from datetime import date
import streamlit as st
import streamlit_hotkeys as hotkeys
import requests
import pandas as pd

# ---------------- CONFIG ----------------
BASE_API = "https://dgtrade.trishakti.com.np:8080/bom/"
LOGIN_API = BASE_API + "tp-data/authenticate"
AC_CODE_API = BASE_API + "tp-data/account/by-nepse"
LEDGER_API = BASE_API + "tp-data/account/ledger"

# st.set_page_config(page_title="Custom Hotkeys", layout="wide")
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
    resp.raise_for_status()
    return resp.json()


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


@st.cache_data(ttl=3200)
def get_rm_and_client_name(client_code):
    rm_name, client_name = db.get_table_rm_child_map_with_client_code(client_code=client_code)
    return rm_name, client_name

# ---------------- HOTKEY + DIALOG ----------------
def activate_client_code_hotkey():
    # Completely invisible hidden button with shortcut
    st.markdown("""
    <style>
        div[data-testid="stButton"] > button[kind="tertiary"] {
            visibility: hidden;
            height: 0px;
            padding: 0;
            margin: 0;
            min-height: 0;
        }
    </style>
    """, unsafe_allow_html=True)

    if st.button("", shortcut="Ctrl+L", key="hidden_open_ledger", type='tertiary'):
        st.session_state.show_ledger_dialog = True

    # Decorated dialog function
    @st.dialog("Client Ledger", width='large')
    def client_ledger_dialog():
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

                        token = db.get_jwt_token()
                        ac_code = get_account_code(token, client_code)
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
            <div style="display: flex;font-weight: bold;justify-content: space-between; font-size: 1rem; color: #6b7280; line-height: 2; margin-bottom: 15px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
                <div>
                    <div>Adjusted Balance: {adjusted_balance}</div>
                    <div>Collateral: {float(ledger.get('collateral', 0)):,.2f}</div>
                </div>
                <div style="text-align: right;">
                    <br>
                    <div>Balance: {float(ledger.get('balance', 0)):,.2f} {ledger.get('balanceType', '-')}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

            # st.subheader("📖 Ledger Transactions", anchor=False)
            data_rows = ledger.get("data", [])
            if data_rows:
                df = pd.DataFrame(data_rows)
                ordered_cols = [
                    "transactionDate", "clearanceDate", "referenceNo",
                    "voucherNo", "particulars", "dr", "cr", "balance", "balanceType"
                ]
                number_cols = ["Dr", "Cr", "Balance"]
                df = df[[c for c in ordered_cols if c in df.columns]]
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
                st.dataframe(styled_df, width='content', hide_index=True)
            else:
                st.warning("No ledger transactions found.")

            if ubilled:
                st.divider()
                st.subheader("📌 Unbilled Transactions", anchor=False)
                df_ub = pd.DataFrame(ubilled)
                ub_cols = ["transactionDate", "particulars", "debit", "credit", "balance", "tr"]
                num_cols = ["Debit", "Credit", "Balance"]
                df_ub = df_ub[[c for c in ub_cols if c in df_ub.columns]]
                df_ub.columns = df_ub.columns.str.upper()
                df_ub.rename(columns=lambda x: helper.camel_to_title(x), inplace=True)
                df_ub = coerce_numeric_columns(df_ub, num_cols)
                df_ub.rename(columns={"Transactiondate": "Transaction Date"}, inplace=True)
                df_ub.sort_values(by="Balance", ascending=False, inplace=True)
                styled_df = df_ub.style.format(accounting_format, subset=num_cols).map(highlight_negative, subset=num_cols)
                total_unbilled_transactions = df_ub['Balance'].sum()
                st.badge(f"Unbilled Amount: {total_unbilled_transactions:,.2f}", color="blue")
                st.dataframe(styled_df, use_container_width=True,  hide_index=True)

    # Call dialog if triggered
    if st.session_state.get("show_ledger_dialog"):
        client_ledger_dialog()
        # Cleanup automatically when dialog closes (Esc or click outside)
        del st.session_state.show_ledger_dialog
        if "ledger_dialog_data" in st.session_state:
            del st.session_state["ledger_dialog_data"]
            # del st.session_state['rm_name']
            # del st.session_state['client_name']
        # st.rerun()
