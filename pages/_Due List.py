import streamlit as st
import pandas as pd
from datetime import datetime
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils import helper
from utils.formatting import *
from utils.custom_hotkey import activate_client_code_hotkey

class DueList:
    def __init__(self):
        st.set_page_config(page_title="Floorsheet", page_icon="📋", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        activate_client_code_hotkey()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()

        # unified engine connection
        self.intranet_engine = helper.get_holding_engine()


    @st.cache_data(ttl=120)
    def load_due_list_data_all(_self, username):
         # --- Load data ---
        query = 'SELECT * FROM due_list'
        params = None
        df = pd.read_sql(query, _self.intranet_engine, params=params)
        return df
    
    
    # @st.cache_data(ttl=6000)
    def load_due_list_data_bro(_self):
         # --- Load data ---
        if _self.role == "BRO":
            alias = helper.get_alias_name(_self.username.upper())
            query = 'SELECT * FROM due_list WHERE "rmName" = %s'
            params = (alias,)
        df = pd.read_sql(query, _self.intranet_engine, params=params)
        return df

    def render_page(_self):
        st.title("📋 Due List", anchor=False)

        # --- Load data based on role ---
        if _self.role == "BRO":
            df: pd.DataFrame = _self.load_due_list_data_bro()
        else:
            df: pd.DataFrame = _self.load_due_list_data_all(username = _self.username)

        # --- Layout for filters at top ---
        col1, col2, col3, col4 = st.columns(4)

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
        st.dataframe(styled_df, use_container_width=True)



if __name__ == "__main__":
    DueList().render_page()