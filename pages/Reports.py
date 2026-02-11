import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
from db import db
from utils import auth_utils
from pages.BasePage import BasePage

class Reports(BasePage):
    def __init__(self):
        super().__init__()
        if 'page_config_set' not in st.session_state:
            st.set_page_config(page_title="Reports", page_icon="📂", layout="wide")
            st.session_state.page_config_set = True
            
        st.session_state.active_menu = "utility"
        # user = auth_utils.ensure_logged_in()
        # self.username = user['username']
        # self.role = user['role']
        # self.branch = user['branch']
        
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
        
        # Ensure Ledger Balance is numeric for formatting and summing
        df['Ledger Balance'] = pd.to_numeric(df['Ledger Balance'], errors='coerce').fillna(0)
        
        cols = ['BRO'] + [c for c in df.columns if c != 'BRO']
        return df[cols]

    def render_page(self):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_type = st.selectbox("Report Type", ['None', 'TMS Limit', 'EDIS Call', 'Others'])

        if selected_type == 'TMS Limit':
            df = self.get_cached_tms_report()
            # Convert to proper datetime
            df['Created Date Time'] = pd.to_datetime(df['Created Date Time'], errors='coerce')
            # Optional: format for display (e.g., YYYY-MM-DD HH:MM:SS)
            df['Created Date Time'] = df['Created Date Time'].dt.strftime('%Y-%m-%d')

            if not df.empty:
                # Calculate Sum for "Success" badge using vectorization (lightning speed)
                # We do this BEFORE the UI filtering so the badge reflects total success 
                # OR move it after if you want the badge to filter too.
                success_sum = df[df['Status'].str.upper() == 'SUCCESS']['Ledger Balance'].sum()
                col5, spacer ,col6 = st.columns([1,0.1,6])
                with col5:
                    st.badge(f"Total clients: {len(df):,.0f}", color='green')
                with col6:
                    st.badge(f"Total Limit Issued: {success_sum:,.2f}", color='orange')

                excluded_filters = ['Reason', 'Ledger Balance']
                filter_options = [c for c in df.columns if c not in excluded_filters]
                
                with col2:
                    filter_col = st.selectbox('Filter By', ['None'] + filter_options)
                
                if filter_col != 'None':
                    with col3:
                        unique_values = sorted(df[filter_col].dropna().unique().tolist())
                        selected_value = st.selectbox(f"Select {filter_col}", unique_values)
                        df = df[df[filter_col] == selected_value]

                df.reset_index(drop=True, inplace=True)
                df.index += 1

                # Display with Comma Formatting in the column
                st.dataframe(
                    df, 
                    use_container_width=True,
                    column_config={
                        "Ledger Balance": st.column_config.NumberColumn(
                            "Ledger Balance",
                            # format="%.2f", 
                        )
                    }
                )
            else:
                st.info("No data found for TMS Limit.")

if __name__ == "__main__":
    Reports().render_page()