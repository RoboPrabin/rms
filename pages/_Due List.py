import streamlit as st
import pandas as pd
from datetime import datetime
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils import helper
from utils.formatting import *

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


    @st.cache_data(ttl=6000)
    def load_due_list_data(_self):
         # --- Load data ---
        if _self.role == "BRO":
            query = 'SELECT * FROM due_list WHERE "rmName" = %s'
            params = (_self.username.upper(),)
        else:
            query = 'SELECT * FROM due_list'
            params = None


        df = pd.read_sql(query, _self.intranet_engine, params=params)
        return df

    def render_page(_self):
        st.title("📋 Due List", anchor=False)
       
        df : pd.DataFrame = _self.load_due_list_data()
        # --- Layout for filters at top ---
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            selected_date = st.date_input("Filter by date", datetime.today())
        with col2:
            by_status = st.selectbox("Select Session", ["Morning", "Evening"], index=0)
        with col3:
            branch_selected_placeholder = st.empty()
        with col4:
            search_query = st.text_input("Search", "", placeholder="Search anything . . .")
            # branch filter will be populated after loading data



        # --- Branch filter options ---
        unique_branches = df["branch"].dropna().unique().tolist()
        branch_selected = branch_selected_placeholder.selectbox(
            "Filter by branch", options=["All"] + sorted(unique_branches)
        )

        # --- Filter by uploaded_at containing selected date ---
        selected_date_str = selected_date.strftime("%Y-%m-%d")
        df_filtered = df[df["uploaded_at"].str.contains(selected_date_str, na=False)]
        

        if by_status == "Morning":
            df_filtered = df_filtered[df_filtered["uploaded_at"].str.endswith("AM")]
        else:  # Evening
            df_filtered = df_filtered[df_filtered["uploaded_at"].str.endswith("PM")]


        # --- Apply branch filter ---
        if branch_selected != "All":
            df_filtered = df_filtered[df_filtered["branch"] == branch_selected]

        # --- Apply search filter ---
        if search_query:
            mask = df_filtered.apply(
                lambda row: row.astype(str).str.contains(search_query, case=False, na=False)
            ).any(axis=1)
            df_filtered = df_filtered[mask]

        if df_filtered.empty:
            st.warning(f"Due list not found as of date {selected_date_str}", icon="⚠️")
            return
        
        # --- Format and calculate ---
        df_filtered = df_filtered.rename(columns={"rmName": "Bro"})
        # --- Display badges ---
        row_count = len(df_filtered)
        due_balance_sum = df_filtered["dueBalance"].sum()

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
        # df_filtered.index = df_filtered.index + 1
        # st.dataframe(df_filtered, width='stretch')



        df_filtered = df_filtered.rename(columns=helper.camel_to_title)
        numeric_cols = ["Due Balance", "Unbilled Amount", "Adjusted Balance", "Collateral", "Bill Age In Days", "Due Since Last Stl Date In Days", "Due Since In Days" ]   # add more if needed

        # --- Coerce numeric columns ---
        df_filtered = coerce_numeric_columns(df_filtered, numeric_cols)

        # --- Reset index to start at 1 ---
        df_filtered.reset_index(drop=True, inplace=True)
        df_filtered.index = df_filtered.index + 1

        # --- Apply styling: accounting format + highlight negatives ---
        styled_df = (
            df_filtered.style
                .format(accounting_format, subset=numeric_cols)
                .map(highlight_negative, subset=numeric_cols)
        )

        # --- Display styled dataframe ---
        st.dataframe(styled_df, use_container_width=True)



if __name__ == "__main__":
    DueList().render_page()