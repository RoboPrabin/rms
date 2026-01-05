import streamlit as st
import pandas as pd
from datetime import datetime, date
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils import helper
from utils.formatting import *
from utils.custom_hotkey import activate_client_code_hotkey, get_account_code, get_ledger, get_rm_and_client_name

class DueList:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        st.set_page_config(page_title="Due List", page_icon="📋", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()

        activate_client_code_hotkey()
        
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()

        # unified engine connection
        self.intranet_engine = helper.get_holding_engine()


    # @st.cache_data(ttl=120)
    # def load_due_list_data_all(_self, username):
    #      # --- Load data ---
    #     query = 'SELECT * FROM due_list'
    #     params = None
    #     df = pd.read_sql(query, _self.intranet_engine, params=params)
    #     return df

    @st.cache_data(ttl=120)
    def load_due_list_data_all(_self, username):
        query = """
            SELECT d.*,
                COALESCE(m."rmName", 'N/A') AS "rmName"
            FROM due_list d
            LEFT JOIN client_rm_map m ON d."clientCode" = m."clientCode"
        """
        df = pd.read_sql(query, _self.intranet_engine)
        return df
    
    
    # def load_due_list_data_bro(_self):
    #     # --- Load data ---
    #     alias = helper.get_alias_name(_self.username.upper())
    #     query = 'SELECT * FROM due_list WHERE "rmName" = %s'
    #     params = (alias,)
    #     df = pd.read_sql(query, _self.intranet_engine, params=params)
    #     return df

    # @st.cache_data(ttl=120)
    def load_due_list_data_bro(_self):
        alias = helper.get_alias_name(_self.username.upper())
        query = """
            SELECT d.*,
                COALESCE(m."rmName", 'N/A') AS "rmName"
            FROM due_list d
            LEFT JOIN client_rm_map m ON d."clientCode" = m."clientCode"
            WHERE COALESCE(m."rmName", 'N/A') = %s
        """
        params = (alias,)
        df = pd.read_sql(query, _self.intranet_engine, params=params)
        return df

    def render_page(_self):
        st.title("📋 Due List", anchor=False)

        # --- Load data based on role ---
        if _self.role == "BRO":
            if 'due_bro' not in st.session_state:
                st.session_state['due_bro'] = _self.load_due_list_data_bro()
            df: pd.DataFrame =st.session_state['due_bro']
        else:
            if 'bro' not in st.session_state:
                st.session_state['bro'] = _self.load_due_list_data_all(username = _self.username)
            df: pd.DataFrame = st.session_state['bro']

        # --- Layout for filters at top ---
        col1, col2, col3, col4 = st.columns(4)
        
        # df = df.iloc[:, 1:]
        with col1:
            selected_date = st.date_input("Filter by date", datetime.today())

        with col2:
            by_status = st.selectbox("Select Session", ["Morning", "Evening"], index=0)

        with col3:
            filter_by = st.selectbox(
                "Filter By",
                ["Bro", "Client Code", "Branch"],
                index=2
            )

        # with col4:
        #     search_query = st.text_input("Search", "", placeholder="Search anything . . .")

        # --- Prepare unique lists ---
        unique_bros = df["rmName"].dropna().unique().tolist()
        unique_branches = df["branch"].dropna().unique().tolist()

        # --- Dynamic filter input ---
        with col4:
            if filter_by == "Bro":
                filter_value = st.selectbox(
                    "Select Bro",
                    options=["All"] + sorted(unique_bros)
                )

            elif filter_by == "Branch":
                filter_value = st.selectbox(
                    "Select Branch",
                    options=["All"] + sorted(unique_branches)
                )

            elif filter_by == "Client Code":
                filter_value = st.text_input(
                    "Enter Client Code",
                    placeholder="Type client code..."
                )

        # --- Filter by date ---
        selected_date_str = selected_date.strftime("%Y-%m-%d")
        df_filtered = df[df["uploaded_at"].str.contains(selected_date_str, na=False)]

        # --- Filter by AM/PM ---
        if by_status == "Morning":
            df_filtered = df_filtered[df_filtered["uploaded_at"].str.endswith("AM")]
        else:
            df_filtered = df_filtered[df_filtered["uploaded_at"].str.endswith("PM")]

        # --- Apply selected filter ---
        if filter_by == "Bro" and filter_value != "All":
            df_filtered = df_filtered[df_filtered["rmName"] == filter_value]
            if len(df_filtered)==0:
                st.info(f"No dues for {filter_value}.", icon="ℹ️")
                st.stop()

        elif filter_by == "Branch" and filter_value != "All":
            df_filtered = df_filtered[df_filtered["branch"] == filter_value]

        elif filter_by == "Client Code" and filter_value.strip():
            df_filtered = df_filtered[
                df_filtered["clientCode"]
                .astype(str)
                .str.contains(filter_value, case=False, na=False)
            ]

        # # --- Apply search filter ---
        # if search_query:
        #     mask = df_filtered.apply(
        #         lambda row: row.astype(str).str.contains(search_query, case=False, na=False)
        #     ).any(axis=1)
        #     df_filtered = df_filtered[mask]

        # --- Empty check ---
        if df_filtered.empty:
            st.warning(f"Due list not found as of date {selected_date_str}", icon="⚠️")
            return

        # --- Rename for display ---
        df_filtered = df_filtered.rename(columns={"rmName": "Bro"})
        cols = ["Bro"] + [col for col in df_filtered.columns if col != "Bro" and col != "rmName"]
        df_filtered = df_filtered.rename(columns={"rmName": "Bro"})[cols]
        # --- Display badges ---
        row_count = len(df_filtered)
        due_balance_sum = df_filtered["adjustedBalance"].sum()

        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom:20px;">
                <span style="background-color: rgba(61, 213, 109, 0.2); color: rgb(92, 228, 136); font-size: 0.875rem; padding:5px; border-radius:6px;">
                    Total rows : {row_count}
                </span>
                <span style="background-color: rgba(255, 108, 108, 0.2); color: rgb(255, 108, 108); font-size: 0.875rem; padding:5px; border-radius:6px;">
                    Total Adjusted Balance : {due_balance_sum:,.2f}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Prepare for display ---
        df_filtered.reset_index(drop=True, inplace=True)
        df_filtered = df_filtered.rename(columns=helper.camel_to_title)

        numeric_cols = [
            "Due Balance", "Unbilled Amount", "Adjusted Balance", "Collateral",
            "Bill Age In Days", "Due Since Last Stl Date In Days", "Due Since In Days"
        ]

        # --- Coerce numeric columns ---
        df_filtered = coerce_numeric_columns(df_filtered, numeric_cols)

        # --- Reset index to start at 1 ---
        df_filtered.index = df_filtered.index + 1

        # --- Styling ---
        styled_df = (
            df_filtered.style
                .format(accounting_format, subset=numeric_cols)
                .map(highlight_negative, subset=numeric_cols)
        )

        # --- Display styled dataframe ---
        selection_row = st.dataframe(styled_df, width='stretch', selection_mode='single-row', key='selected_client', on_select='rerun')
        # print(selection_row.get('clientCode'))
        if selection_row.selection.rows:
            row_idx = selection_row.selection.rows[0]
            value = df_filtered.iloc[row_idx]["Client Code"]  # Access by position then column name
            try:
                _self.client_ledger_dialog(client_code=value)
            except Exception as e:
                pass


    # Decorated dialog function
    @st.dialog("Client Ledger", width='large')
    def client_ledger_dialog(self, client_code):
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                client_code = st.text_input("Client Code (NEPSE)", value=client_code).upper()

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

                df.rename(columns={"Transactiondate": "Transaction Date", "Clearancedate": "Clearance Date", "Referenceno": "Reference No", "Balancetype": "Balance Type"}, inplace=True)
                
                styled_df = df.style.format(accounting_format, subset=number_cols).map(highlight_negative, subset=number_cols)
                st.dataframe(styled_df, width='stretch', hide_index=True)
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



if __name__ == "__main__":
    DueList().render_page()