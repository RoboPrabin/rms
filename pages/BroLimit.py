from pages.BasePage import BasePage
import uuid
from time import sleep
from db import bro_limit_repo
from decimal import Decimal
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from utils import auth_utils, helper
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from utils.custom_hotkey import activate_client_code_hotkey
from config.config import credentials_tms_for_collateral_only
from api.tms import api_collateral
# ... (imports remain the same)

@st.cache_data(ttl=300)
def get_client_list_cached():
    rows = bro_limit_repo.get_bros()
    df = pd.DataFrame(rows, columns=['id', 'username', 'full_name'])
    df['full_name'] = df['full_name'].str.upper()
    df.sort_values(by='full_name', inplace=True)
    df['display'] = df['username'] + " - " + df['full_name']
    return df[['id', 'display']]

def get_bro_limits_cached():
    # Force fetch from DB if not in state
    if 'bro_limits_df' not in st.session_state:
        st.session_state.bro_limits_df = bro_limit_repo.get_all_bro_limits()
    return st.session_state.bro_limits_df

class BroLimit(BasePage):
    def __init__(self):
        super().__init__()
        st.set_page_config(page_title="BRO Limit Manager", layout='wide', page_icon="🧮")
        helper.eliminate_top_margin("-8rem")
        st.session_state.active_menu = "rm"
        activate_client_code_hotkey()
        helper.adjust_ui()
        render_sidebar()
        self.engine = create_engine(helper.get_holding_engine())
        st.header("🧮 BRO Limit Manager", anchor=False)

    def set_limit_threshold(self):
        col1, col2 = st.columns(2)
        with col1:
            client_df = get_client_list_cached()
            bro_display = st.selectbox(
                "Select Client",
                options=client_df['display'],
                key="client_code_select"
            )
            bro_code = str(bro_display).split("-")[0].strip() if bro_display else None
        
        with col2:
            limit_amount = st.number_input("Limit Threshold", min_value=0, step=1000, key="limit_amount_input")
        
        if st.button("Set Limit Threshold", icon="✅"):
            if not bro_code:
                st.warning("Please select a client.", icon="⚠️")
                return
            
            manager_id = st.session_state.get('id', 'system')
            
            # 1. Update Database
            bro_limit_repo.update_bro_limit(bro_code, limit_amount, manager_id)
            
            # 2. IMMEDIATE STATE UPDATE (The "Lightning" Part)
            # Fetch fresh data from DB immediately to sync the UI without waiting for cache TTL
            st.session_state.bro_limits_df = bro_limit_repo.get_all_bro_limits()
            
            st.toast(f"Limit for {bro_code} updated!", icon="🚀")
            sleep(0.6) # Minimal pause for UX feedback
            st.rerun() # Trigger immediate UI refresh

    def show_bro_limit_ui(self):
        st.subheader("📊 All BROs Limit", anchor=False)
        df = get_bro_limits_cached()
        
        # Calculate totals dynamically from the current dataframe
        total_bros = len(df)
        total_limit = df['TOTAL LIMIT'].sum() if not df.empty else 0

        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom:20px;">
                <span style="background-color: rgba(61, 213, 109, 0.2); color: rgb(92, 228, 136); font-size: 0.875rem; padding:5px; border-radius:6px;">
                    Total BROs : {total_bros}
                </span>
                <span style="background-color: rgba(255, 108, 108, 0.2); color: rgb(255, 108, 108); font-size: 0.875rem; padding:5px; border-radius:6px;">
                    Total Limit Issued : {total_limit:,.0f}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.dataframe(df, use_container_width=True)

    def render_page(self):
        self.set_limit_threshold()
        st.divider()
        self.show_bro_limit_ui()

if __name__ == "__main__":
    BroLimit().render_page()