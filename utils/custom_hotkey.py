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
    print(resp.json())
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


# ---------------- HOTKEY + DIALOG ----------------
def activate_client_code_hotkey():


    # Add this early in every page script (before other widgets)

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

    if st.button("", shortcut="L", key="hidden_open_ledger", type='tertiary'):
        st.session_state.show_ledger_dialog = True

    # Decorated dialog function
    @st.dialog("Client Ledger", width='large')
    def client_ledger_dialog():
        with st.form("ledger_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                client_code = st.text_input("Client Code (NEPSE)").upper()

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
                        st.session_state['rm_name'] = db.get_rm_name_from_client_rm_map_table(client_code=client_code)
                    except Exception as e:
                        st.error(f"Client Code: '{client_code.upper()}' not found")
                        return

        if "ledger_dialog_data" in st.session_state:
            ledger = st.session_state["ledger_dialog_data"]
            # st.divider()
            st.subheader("📒 Opening Summary", anchor=False)
            ubilled = ledger.get("ubilledTransactions", [])

            adjusted_balance = 0.0
            if ubilled:
                df_ub = pd.DataFrame(ubilled)
                if "credit" in df_ub.columns:
                    total_credit = df_ub["credit"].sum()
                    adjusted_balance = total_credit - float(ledger.get('balance', '0.00'))


            
            c1, c2, c3 = st.columns(3)
            c1.metric("Opening", f"{float(ledger.get('opening', 0)):,.2f}", border=True, height=100)
            c2.metric("Balance", f"{float(ledger.get('balance', 0)):,.2f}", border=True)
            c3.metric("Type", ledger.get("balanceType", "-"), border=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Collateral", f"{float(ledger.get('collateral', 0)):,.2f}", border=True)
            c2.metric("Adjusted Balance", f"{adjusted_balance:,.2f}", border=True)
            c3.metric("BRO", f"{st.session_state.get('rm_name', 'N/A')}", border=True)
            st.divider()
            st.subheader("📖 Ledger Transactions", anchor=False)
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

                df.rename(columns={"Transactiondate": "Transaction Date", "Clearancedate": "Clearance Date", "Referenceno": "Reference No", "Balancetype": "Balance Type"}, inplace=True)

                styled_df = df.style.format(accounting_format, subset=number_cols).map(highlight_negative, subset=number_cols)
                st.dataframe(styled_df, use_container_width=True, height=300, hide_index=True)
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

                styled_df = df_ub.style.format(accounting_format, subset=num_cols).map(highlight_negative, subset=num_cols)
                st.dataframe(styled_df, use_container_width=True, height=200, hide_index=True)

    # Call dialog if triggered
    if st.session_state.get("show_ledger_dialog"):
        client_ledger_dialog()
        # Cleanup automatically when dialog closes (Esc or click outside)
        del st.session_state.show_ledger_dialog
        if "ledger_dialog_data" in st.session_state:
            del st.session_state["ledger_dialog_data"]
            del st.session_state['rm_name']
        # st.rerun()
