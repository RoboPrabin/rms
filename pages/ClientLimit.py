from time import sleep
import pandas as pd
import streamlit as st
from db import client_limit_repo
from pages.BasePage import BasePage
from streamlit_bridge.navigation import render_sidebar
from utils import helper
from utils.custom_hotkey import activate_client_code_hotkey

@st.cache_data(ttl=300)
def get_client_list_cached(rm_name):
    """Cached list for the dropdown only"""
    rows = client_limit_repo.get_clients_by_rm(rm_name=rm_name)
    df = pd.DataFrame(rows, columns=['BRO','Client Code','Client Name','Category', 'Credit Limit', 'Trading Limit'])
    df.sort_values(by='Client Name', inplace=True)
    df['display'] = df['Client Code'] + " - " + df['Client Name']
    return df['display']

@st.cache_data(ttl=300)
def get_client_list_cached_admin():
    """Cached list for the dropdown only"""
    rows = client_limit_repo.get_all_clients()
    df = pd.DataFrame(rows, columns=['BRO','Client Code','Client Name','Category', 'Credit Limit', 'Trading Limit'])
    df.sort_values(by='Client Name', inplace=True)
    df['display'] = df['Client Code'] + " - " + df['Client Name']
    return df['display']

def refresh_client_data():
    """Fetches fresh data and updates session state immediately"""
    rows = client_limit_repo.get_clients_by_rm(rm_name=st.session_state.username)
    df = pd.DataFrame(rows, columns=['BRO','Client Code','Client Name','Category', 'Credit Limit', 'Trading Limit (Threshold)'])
    
    # Pre-formatting for display
    df.sort_values(by='Client Name', inplace=True)
    df_display = df.drop(columns=['BRO', 'Credit Limit']).copy()
    df_display['Trading Limit (Threshold)'] = df_display['Trading Limit (Threshold)'].apply(lambda x: f"{x:,}" if x is not None else 0)
    df_display.reset_index(inplace=True, drop=True)
    df_display.index += 1
    
    st.session_state.my_clients_df = df_display

class ClientLimit(BasePage):
    def __init__(self):
        helper.eliminate_top_margin("-8rem")
        st.set_page_config(page_title="Client Limit Setup", layout='wide', page_icon="🧮")
        super().__init__()
        st.session_state.active_menu = "rm"
        activate_client_code_hotkey()
        helper.adjust_ui()
        render_sidebar()
        st.header("🧮 Client Limit Manager", anchor=False)
        
        # Initialize data in state if not present
        if 'my_clients_df' not in st.session_state:
            refresh_client_data()

    def set_limit_threshold(self):
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.session_state.role == "ADMIN":
                client_options = get_client_list_cached_admin()
            else:
                client_options = get_client_list_cached(st.session_state.username)
            client_display = st.selectbox("Select Client", options=client_options, key="client_code_select")
            client_code = str(client_display).split("-")[0].strip() if client_display else None
        with col2:
            category = st.selectbox("Category", options=helper.default_category_list(), key="category_input")
        with col3:
            limit_amount = st.number_input("Trading Limit (Threshold)", min_value=0, step=1000, key="limit_amount_input")

        if st.button("Set Limit Threshold", icon="✅"):
            if not client_code:
                st.warning("Please select a client.", icon="⚠️")
                return

            # 1. Fetch bro limits
            bro_limits_df = client_limit_repo.get_loggedin_bro_limits(bro_id=st.session_state.id)
            total_limit = int(str(bro_limits_df['TOTAL LIMIT'].iloc[0]).replace(",", "") or 0)
            # used_limit = int(str(bro_limits_df['USED LIMIT'].iloc[0]).replace(",", "") or 0)

            # 2. Check if new limit exceeds available capacity
            if limit_amount > total_limit:
                remaining = total_limit
                st.error(f"Insufficient BRO limit.", icon="⚠️")
                # return
            else:
                # 3. Update Database
                client_limit_repo.update_client_limit(client_code, limit_amount, category, st.session_state.username)
                # 4. Refresh Local State
                refresh_client_data()
                # 5. User Feedback
                st.toast(f"Limit for {client_code} updated!", icon="🚀")
                sleep(0.6)
                st.rerun()

        st.divider()
        self.my_limit_ui()
        st.divider()
        self.show_my_clients_limits()

    def show_my_clients_limits(self):
        st.subheader("🍁 My Clients Limit Details", anchor=False)
        # Pull directly from state
        df = st.session_state.my_clients_df
        st.dataframe(df, width='stretch')
    
    def my_limit_ui(self):
        st.subheader("📊 My Current Limit ", anchor=False)
        df = client_limit_repo.get_loggedin_bro_limits(bro_id=st.session_state.id)
        st.dataframe(df, width='stretch')

    def render(self):
        action = st.radio("Select an action", ["Set Limit Threshold", "Set Limit on TMS"], horizontal=True, key="client_limit_action")
        if action == "Set Limit Threshold":
            self.set_limit_threshold()
        elif action == "Set Limit on TMS":
            st.info("This feature is coming soon! Stay tuned. 🚀", icon="⏳")

if __name__ == "__main__":
    ClientLimit().render()