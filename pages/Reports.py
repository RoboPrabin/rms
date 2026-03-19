import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
from db import db
from utils import auth_utils, helper
from pages.BasePage import BasePage


@st.cache_data(ttl=3600)
def get_cached_categorized_client_data():
    df = db.fetch_category_client_data()
    return df

class Reports(BasePage):
    def __init__(self):
        super().__init__()
        if 'page_config_set' not in st.session_state:
            st.set_page_config(page_title="Reports", page_icon="📂", layout="wide")
            st.session_state.page_config_set = True
            
        st.session_state.active_menu = "business"        
        helper.eliminate_top_margin("-4rem")
        st.header("📂 Reports", anchor=False)
        render_sidebar()

    @st.cache_data(ttl=600)
    def get_cached_tms_report(_self):
        df = db.get_tms_limit_report()
        if df is None or df.empty:
            return pd.DataFrame()
            
        df = df.drop(columns=['id'], errors='ignore').rename(columns={
            'client_code': 'Client Code',
            'client_name': 'Client Name',
            'category': 'Category',
            'bro': 'BRO',
            'status': 'Status',
            'reason': 'Reason',
            'ledger_type': 'Ledger Type',
            'ledger_balance': 'Ledger Balance',
            'created_date_time': 'Created Date Time'
        })
        
        # Ensure Ledger Balance is numeric
        df['Ledger Balance'] = pd.to_numeric(df['Ledger Balance'], errors='coerce').fillna(0)
        
        # Convert to proper datetime objects for logical sorting/filtering
        df['Created Date Time'] = pd.to_datetime(df['Created Date Time'], errors='coerce')
        
        cols = ['BRO'] + [c for c in df.columns if c != 'BRO']
        return df[cols]



    def tms_limit_ui(self, col2, col3):
        df = self.get_cached_tms_report()

        if not df.empty:
            # Prepare Date options: "All" + sorted unique dates
            unique_dates = sorted(df['Created Date Time'].dt.strftime('%Y-%m-%d').unique(), reverse=True)
            date_options = ["All"] + unique_dates
            
            # 2. Date Filter (Defaults to Latest Date)
            with col2:
                selected_date = st.selectbox("Select Date", date_options, index=1) # Index 1 is the latest date
            
            if selected_date != "All":
                df = df[df['Created Date Time'].dt.strftime('%Y-%m-%d') == selected_date]

            # 3. Secondary Filter (Specific columns only)
            filter_columns = ['None', 'BRO', 'Client Code', 'Client Name', 'Category', 'Status', 'Ledger Type']
            
            with col3:
                filter_col = st.selectbox("Filter By", filter_columns)
                if filter_col != 'None':
                    unique_values = sorted(df[filter_col].dropna().unique().tolist())
                    selected_val = st.selectbox(f"Select {filter_col}", unique_values)
                    df = df[df[filter_col] == selected_val]

            # --- Data Processing for Display ---
            
            # Calculate sums BEFORE string conversion
            success_sum = df[df['Status'].str.upper() == 'SUCCESS']['Ledger Balance'].sum()
            
            # Format for display
            display_df = df.copy()
            display_df['Ledger Balance'] = display_df['Ledger Balance'].apply(lambda x: f"{x:,.2f}")
            display_df['Created Date Time'] = display_df['Created Date Time'].dt.strftime('%Y-%m-%d')
            
            display_df.reset_index(drop=True, inplace=True)
            display_df.index += 1

            # Display Badges
            col_b1, spacer, col_b2 = st.columns([1, 0.1, 6])
            with col_b1:
                st.badge(f"Total clients: {len(display_df):,.0f}", color='green')
            with col_b2:
                st.badge(f"Total Limit Issued: {success_sum:,.2f}", color='orange')

            # Render Table
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No data found for TMS Limit.")




    @st.cache_data(ttl=600)
    def get_cached_floorsheet_report(_self):
        df = db.get_floorsheet_summary()
        if df.empty:
            return pd.DataFrame()
            
        df.rename(columns={
            'date': 'Date', 
            'branch': 'Branch', 
            'transaction_type': 'Transaction Type', 
            'total_amount': 'Total Amount'
        }, inplace=True)
        
        # --- Update Branch Codes to Full Names ---
        mapping = helper.get_branch_code_mapping()
        # .map() replaces the code with the name; .fillna() keeps the original if not found in dict
        df['Branch'] = df['Branch'].map(mapping).fillna(df['Branch'])
        
        df['Transaction Type'] = df['Transaction Type'].str.upper()
        df['Date'] = df['Date'].astype(str)
        return df

    def branch_turnover_ui(self, col2, col3):
        df = self.get_cached_floorsheet_report()
        
        if df.empty:
            st.info("No floorsheet data found.")
            return

        # col2, col3 = st.columns(2)

        # 1. Date Filter (Latest Date as default is index 1, "All" is index 0)
        unique_dates = sorted(df['Date'].unique().tolist(), reverse=True)
        date_options = ["All"] + unique_dates
        with col2:
            selected_date = st.selectbox("Filter by Date", date_options, index=0)
            if selected_date != "All":
                df = df[df['Date'] == selected_date]

        # 2. Branch Filter (Now shows Full Names)
        unique_branches = sorted(df['Branch'].unique().tolist())
        branch_options = ["All"] + unique_branches
        with col3:
            selected_branch = st.selectbox("Filter by Branch", branch_options, index=0)
            if selected_branch != "All":
                df = df[df['Branch'] == selected_branch]

        # --- Calculations (Numeric) ---
        total_sum = df['Total Amount'].sum()
        buy_sum = df[df['Transaction Type'] == 'BUY']['Total Amount'].sum()
        sell_sum = df[df['Transaction Type'] == 'SELL']['Total Amount'].sum()
        st.divider()
        # --- UI Metrics ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Turnover", f"Rs. {total_sum:,.2f}", border=True)
        m2.metric("Total Buy", f"Rs. {buy_sum:,.2f}", border=True)
        m3.metric("Total Sell", f"Rs. {sell_sum:,.2f}", border=True,)

        # st.divider()

        # --- Display Formatting for Table ---
        display_df = df.copy()
        display_df['Total Amount'] = display_df['Total Amount'].apply(lambda x: f"{x:,.2f}")
        
        display_df.reset_index(drop=True, inplace=True)
        display_df.index += 1

        st.dataframe(display_df, use_container_width=True)

    def render_page(self):
        col1, col2, col3 = st.columns(3)
        report_options = ['Categorized Adjusted Balance' ,
                          'TMS Limit','Branch Turnover' , 
                          'EDIS Call', 'Others', 'None']
        with col1:
            selected_type = st.selectbox("Report Type", report_options, index=0)
        with st.spinner(f"Loading {selected_type} report...", show_time=True):
            if selected_type == 'TMS Limit':
                self.tms_limit_ui(col2, col3)
            elif selected_type == 'Branch Turnover':
                self.branch_turnover_ui(col2, col3)
            elif selected_type == 'Categorized Adjusted Balance':
                df_raw = get_cached_categorized_client_data()
                df_raw.columns = df_raw.columns.str.upper()
                df_raw.rename(columns={'RM': 'BRO'}, inplace=True)

                # Calculate totals for all numeric columns except BRO
                totals = {}
                for col in df_raw.columns:
                    if col != "BRO":
                        if pd.api.types.is_numeric_dtype(df_raw[col]):
                            totals[col] = df_raw[col].sum()
                        else:
                            totals[col] = None
                    else:
                        totals[col] = "Total"

                # Append the totals row
                df_raw = pd.concat([df_raw, pd.DataFrame([totals])], ignore_index=True)

                # Now apply formatting (commas, decimals) to all except BRO
                for col in df_raw.columns:
                    if col != "BRO":
                        df_raw[col] = df_raw[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) and isinstance(x,(int,float)) else x)

                # Reset index for display
                df_raw.index += 1

                # Show in Streamlit 
                df_raw.index = df_raw.index[:-1].tolist() + [""]
                st.dataframe(df_raw, width='stretch')

                # st.write("### Totals")
                # st.table(df_raw.tail(1))   # show only the last row separately



if __name__ == "__main__":
    Reports().render_page()