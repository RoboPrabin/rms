from time import sleep
import streamlit as st
import pandas as pd
from datetime import datetime, date
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils import helper
from utils.formatting import *
from utils.custom_hotkey import activate_client_code_hotkey, get_account_code, get_ledger, get_rm_and_client_name
from streamlit_autorefresh import st_autorefresh

# Engine
intranet_engine = helper.get_holding_engine()


def get_due_list_last_updated_ts_all():
    query = "SELECT MAX(updated_at) FROM due_list"
    return pd.read_sql(query, intranet_engine).iloc[0, 0]


def get_due_list_last_updated_ts_bro(bro_name):
    query = """
        SELECT MAX(d.updated_at)
        FROM due_list d
        LEFT JOIN client_rm_map m ON d."clientCode" = m."clientCode"
        WHERE COALESCE(m."rmName", 'N/A') = %s
    """
    return pd.read_sql(query, intranet_engine, params=(bro_name,)).iloc[0, 0]


# --- Load functions ---
def load_due_list_data_all():
    query = """
        SELECT d.*,
               COALESCE(m."rmName", 'N/A') AS "rmName"
        FROM due_list d
        LEFT JOIN client_rm_map m ON d."clientCode" = m."clientCode"
    """
    df = pd.read_sql(query, intranet_engine)
    return df

def load_due_list_data_bro(alias):
    query = """
        SELECT d.*,
               COALESCE(m."rmName", 'N/A') AS "rmName"
        FROM due_list d
        LEFT JOIN client_rm_map m ON d."clientCode" = m."clientCode"
        WHERE COALESCE(m."rmName", 'N/A') = %s
    """
    params = (alias,)
    df = pd.read_sql(query, intranet_engine, params=params)
    return df

# --- Main Class ---
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

    # def load_data(self):
    #     """Load due list only once into session_state"""
    #     if "due_list_data" not in st.session_state:
    #         if self.role == "BRO":
    #             alias = helper.get_alias_name(self.username.upper())
    #             st.session_state["due_list_data"] = load_due_list_data_bro(alias)
    #         else:
    #             st.session_state["due_list_data"] = load_due_list_data_all()

    def load_data(self):
        if self.role == "BRO":
            alias = helper.get_alias_name(self.username.upper())
            latest_ts = get_due_list_last_updated_ts_bro(alias)

            if (
                "due_list_data" not in st.session_state
                or st.session_state.get("due_list_last_ts") != latest_ts
            ):
                st.session_state["due_list_data"] = load_due_list_data_bro(alias)
                st.session_state["due_list_last_ts"] = latest_ts

        else:
            latest_ts = get_due_list_last_updated_ts_all()

            if (
                "due_list_data" not in st.session_state
                or st.session_state.get("due_list_last_ts") != latest_ts
            ):
                st.session_state["due_list_data"] = load_due_list_data_all()
                st.session_state["due_list_last_ts"] = latest_ts


    



    def render_page(self):
        self.load_data()
        df: pd.DataFrame = st.session_state["due_list_data"]
        st.title("📋 Due List", anchor=False)

        # --- Layout for filters ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            selected_date = st.date_input("Filter by date", datetime.today())
        with col2:
            by_status = st.selectbox("Select Session", ["Morning", "Evening"], index=0)
        with col3:
            filter_by = st.selectbox("Filter By", ["Bro", "Client Code", "Branch", ">=", "<="], index=2)

        with col4:
            unique_bros = df["rmName"].dropna().unique().tolist()
            unique_branches = df["branch"].dropna().unique().tolist()

            if filter_by == "Bro":
                filter_value = st.selectbox("Select Bro", options=["All"] + sorted(unique_bros))
            elif filter_by == "Branch":
                filter_value = st.selectbox("Select Branch", options=["All"] + sorted(unique_branches))
            elif filter_by == "Client Code":
                filter_value = st.text_input("Enter Client Code", placeholder="Type client code...")
            elif filter_by == ">=":
                filter_value = st.number_input(
                        "Enter Greater or Equals value",
                        min_value=0,
                        step=1,
                        format="%d"
                    )
            elif filter_by == "<=":
                filter_value = st.number_input(
                    "Enter Less or Equals value",
                    min_value=0,
                    step=1,
                    format="%d"
                )


        search_by_clients = False
        if filter_by == "Client Code" and filter_value.strip():
            search_by_clients = True
            cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=30)
            df["uploaded_at_dt"] = pd.to_datetime(
                df["uploaded_at"],
                errors="coerce",
                format="%Y-%m-%d %I:%M:%S %p",  
            )

            df_filtered = df[
                (df["clientCode"].astype(str).str.contains(filter_value, case=False, na=False)) &
                (df["uploaded_at_dt"].notna()) &
                (df["uploaded_at_dt"] >= cutoff_date)
            ]

            if df_filtered.empty:
                st.info(
                    f"No data found for Client Code: {filter_value} in the last 30 days.",
                    icon="ℹ️"
                )
                st.stop()

        else:
            # --- Filter by date ---
            selected_date_str = selected_date.strftime("%Y-%m-%d")
            df_filtered = df[df["uploaded_at"].str.contains(selected_date_str, na=False)]

            # --- Filter by AM/PM ---
            if by_status == "Morning":
                df_filtered = df_filtered[df_filtered["uploaded_at"].str.endswith("AM")]
            else:
                df_filtered = df_filtered[df_filtered["uploaded_at"].str.endswith("PM")]

            # --- Apply Bro / Branch filters ---
            if filter_by == "Bro" and filter_value != "All":
                df_filtered = df_filtered[df_filtered["rmName"] == filter_value]
                if df_filtered.empty:
                    st.info(f"No dues for {filter_value}.", icon="ℹ️")
                    st.stop()

            elif filter_by == "Branch" and filter_value != "All":
                df_filtered = df_filtered[df_filtered["branch"] == filter_value]

            elif filter_by == ">=":
                df_filtered = df_filtered[
                    pd.to_numeric(df_filtered["adjustedBalance"], errors="coerce") >= filter_value
                ]

            elif filter_by == "<=":
                df_filtered = df_filtered[
                    pd.to_numeric(df_filtered["adjustedBalance"], errors="coerce") <= filter_value
                ]     

        # --- Empty check ---
        if df_filtered.empty:
            st.warning(f"Due list not found as of date {selected_date_str}", icon="⚠️")
            return

        # --- Display badges ---
        df_filtered = df_filtered.rename(columns={"rmName": "Bro"})
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

        # --- Prepare display ---
        # Drop unnecessary columns including uploaded_at
        df_filtered.drop(columns=[
            'category', 'dueDate', 'dueSinceLastStlDateInDays',
            'lastSettlementDate', 'lastCrDate', 'billAgeInDays'
        ], inplace=True, errors='ignore')
        df["Session"] = df["uploaded_at"].astype(str).str.endswith("AM").map(
            {True: "Morning", False: "Evening"}
        )

        # Move Bro column to first position
        if "Bro" in df_filtered.columns:
            cols = ["Bro"] + [c for c in df_filtered.columns if c != "Bro"]
            df_filtered = df_filtered[cols]

        if search_by_clients:
            df_filtered.sort_values(by="uploaded_at", ascending=False, inplace=True)
        else:
            df_filtered.sort_values(by="adjustedBalance", ascending=False, inplace=True)

        df_filtered.reset_index(drop=True, inplace=True)

        # Rename and format columns
        df_filtered.rename(columns={"dueSinceInDays": "Due Days"}, inplace=True)
        df_filtered['boid'] = df_filtered['boid'].apply(lambda x: "IN" if str(x).startswith("13011400") else "OUT")
        # df_filtered.drop(columns=['uploaded_at_dt'], inplace=True)
        try:
            cols = list(df_filtered.columns)
            # Remove 'Session' from current position
            cols.remove("Session")
            # Insert 'Session' at 2nd last position
            cols.insert(len(cols)-3, "Session")
        except Exception as e:
            pass
        # Reorder dataframe
        df_filtered = df_filtered[cols]
        df_filtered = df_filtered.rename(columns=helper.camel_to_title)


        # print(df_filtered.columns)

        # print(df.columns)
        # df_filtered.rename(columns={"rmName":"Bro"}, inplace=True)
        numeric_cols = ["Due Balance", "Unbilled Amount", "Adjusted Balance", "Collateral"]
        df_filtered = coerce_numeric_columns(df_filtered, numeric_cols)
        df_filtered.index = df_filtered.index + 1

        # --- Styling ---
        styled_df = df_filtered.style.format(accounting_format, subset=numeric_cols).map(highlight_negative, subset=numeric_cols)

        # Move "Bro" to the front, keep others as they are
        cols = ["Bro"] + [col for col in df_filtered.columns if col != "Bro"]
        df_filtered = df_filtered[cols]

        # --- Display DataFrame with single-row selection ---
        selection_row = st.dataframe(styled_df, width='stretch', selection_mode='single-row', key='selected_client', on_select='rerun')

        # --- Open Client Ledger Dialog ---
        if selection_row.selection.rows:
            row_idx = selection_row.selection.rows[0]
            value = df_filtered.iloc[row_idx]["Client Code"]
            remarks = df_filtered.iloc[row_idx]["Remarks"]
            try:
                self.client_ledger_dialog(client_code=value, selected_date=selected_date, session=by_status, remarks=remarks)
            except Exception:
                pass

    @st.dialog("Client Ledger", width='large')
    def client_ledger_dialog(self, client_code, selected_date, session, remarks):
        st.badge(str(selected_date) + " " + session)
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                client_code = st.text_input("Client Code (NEPSE)", value=client_code).upper()
            with col2:
                from_date = st.date_input("From Date", value=date(2025, 7, 17), max_value=date.today())
            with col3:
                to_date = st.date_input("To Date", value=date.today(), min_value=from_date, max_value=date.today())
            remarks_input = st.text_input("Remarks", value=remarks)

            if st.button("Update Remarks", icon="💾"):
                if remarks_input.strip() == "":
                    st.warning("Please provide remarks.", icon="⚠️")
                    st.stop()
                session_filter = "AM" if session.lower() == "morning" else "PM"
                selected_date_str = selected_date.strftime("%Y-%m-%d")

                try:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    update_query = """
                       UPDATE due_list
                            SET remarks = %s,
                                updated_at = now(),
                                updated_by = %s
                            WHERE "clientCode" = %s
                            AND uploaded_at LIKE %s
                            AND uploaded_at LIKE %s

                    """
                    # update_query = """
                    #     UPDATE due_list
                    #     SET remarks = %s
                    #     WHERE "clientCode" = %s
                    #     AND uploaded_at LIKE %s
                    #     AND uploaded_at LIKE %s
                    # """
                    cursor.execute(update_query, (remarks_input, self.username.upper() ,client_code, f"{selected_date_str}%", f"%{session_filter}"))
                    conn.commit()

                    # --- Update in-memory dataframe ---
                    df = st.session_state["due_list_data"]
                    mask = (
                        (df["clientCode"] == client_code) &
                        (df["uploaded_at"].str.contains(selected_date_str)) &
                        (df["uploaded_at"].str.contains(session_filter))
                    )
                    df.loc[mask, "remarks"] = remarks_input
                    st.session_state["due_list_data"] = df

                    st.success(f"Remarks updated for {cursor.rowcount} row(s): {remarks_input}")
                    sleep(0.3)
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to update remarks: {e}")
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()

        # --- Ledger display logic here ---
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

        # --- Ledger display formatting ---
        if "ledger_dialog_data" in st.session_state:
            ledger = st.session_state["ledger_dialog_data"]
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

            data_rows = ledger.get("data", [])
            if data_rows:
                df = pd.DataFrame(data_rows)

                # --- Keep only desired columns ---
                ordered_cols = ["transactionDate", "clearanceDate", "referenceNo",
                                "voucherNo", "particulars", "dr", "cr", "balance", "balanceType"]
                df = df[[c for c in ordered_cols if c in df.columns]]

                # --- Uppercase and rename columns ---
                df.columns = df.columns.str.upper()
                df.rename(columns=lambda x: helper.camel_to_title(x), inplace=True)
                df = coerce_numeric_columns(df, ["Dr", "Cr", "Balance"])
                df.rename(columns={
                    "Transactiondate": "Transaction Date",
                    "Clearancedate": "Clearance Date",
                    "Referenceno": "Reference No",
                    "Balancetype": "Balance Type"
                }, inplace=True)

                has_search= False
                # --- Search filter ---
                search_query = st.text_input("Search by Particulars", width=400).strip()
                if search_query:
                    df = df[df["Particulars"].str.contains(search_query, case=False, na=False)]
                    has_search = True
                # --- Styling ---
                number_cols = ["Dr", "Cr", "Balance"]
                styled_df = df.style.format(accounting_format, subset=number_cols).map(highlight_negative, subset=number_cols)
                if has_search:
                    total_cr = df['Cr'].sum()
                    st.badge(f"Total Cr Amount: {total_cr:,.2f}")
                # --- Display ---
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

            else:
                st.warning("No ledger transactions found.")


            # --- Unbilled Transactions ---
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
                st.dataframe(styled_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    DueList().render_page()
