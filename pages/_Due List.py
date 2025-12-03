import streamlit as st
import pandas as pd
from datetime import datetime
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils import helper


class DueList:
    def __init__(self):
        st.set_page_config(page_title="Floorsheet", page_icon="📋", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()

        # unified engine connection
        self.intranet_engine = helper.get_holding_engine()

    def render_page(self):
        st.title("📋 Due List", anchor=False)

        # --- Layout for filters at top ---
        col1, col2, col3 = st.columns([2, 2, 3])
        with col1:
            selected_date = st.date_input("Filter by date", datetime.today())
        with col2:
            branch_selected_placeholder = st.empty()
        with col3:
            search_query = st.text_input("Search", "", placeholder="Search anything . . .")
            # branch filter will be populated after loading data

        # --- Load data ---
        if self.role == "BRO":
            query = 'SELECT * FROM due_list WHERE "rmName" = %s'
            params = (self.username.upper(),)
        else:
            query = 'SELECT * FROM due_list'
            params = None

        df = pd.read_sql(query, self.intranet_engine, params=params)

        # --- Branch filter options ---
        unique_branches = df["branch"].dropna().unique().tolist()
        branch_selected = branch_selected_placeholder.selectbox(
            "Filter by branch", options=["All"] + sorted(unique_branches)
        )

        # --- Filter by uploaded_at containing selected date ---
        selected_date_str = selected_date.strftime("%Y-%m-%d")
        df_filtered = df[df["uploaded_at"].str.contains(selected_date_str, na=False)]

        # --- Apply branch filter ---
        if branch_selected != "All":
            df_filtered = df_filtered[df_filtered["branch"] == branch_selected]

        # --- Apply search filter ---
        if search_query:
            mask = df_filtered.apply(
                lambda row: row.astype(str).str.contains(search_query, case=False, na=False)
            ).any(axis=1)
            df_filtered = df_filtered[mask]

        # --- Format and calculate ---
        df_filtered = df_filtered.rename(columns={"rmName": "BRO"})
        df_filtered = helper.format_dataframe(df=df_filtered)

        # Clean Due Balance column
        df_filtered["Due Balance"] = (
            df_filtered["Due Balance"].str.replace(",", "", regex=True).astype(float)
        )

        # --- Display badges ---
        row_count = len(df_filtered)
        due_balance_sum = df_filtered["Due Balance"].sum()

        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom:20px;">
                <span style="background-color: rgba(61, 213, 109, 0.2); color: rgb(92, 228, 136); font-size: 0.875rem; padding:5px; border-radius:6px;">
                    Total rows : {row_count}
                </span>
                <span style="background-color: rgba(255, 108, 108, 0.2); color: rgb(255, 108, 108); font-size: 0.875rem; padding:5px; border-radius:6px;">
                    Total Due Balance : {due_balance_sum:,.2f}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        df_filtered.reset_index(inplace=True, drop=True)
        df_filtered.index = df_filtered.index + 1
        st.dataframe(df_filtered, width='stretch')


if __name__ == "__main__":
    DueList().render_page()