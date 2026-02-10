from decimal import Decimal
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from db import db
from utils import auth_utils, helper
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from utils.custom_hotkey import activate_client_code_hotkey

class TopBrokers:
    def __init__(self):
        # helper.eliminate_top_padding()
        helper.eliminate_top_margin(margin_top="-10rem")
        st.session_state.active_menu = "business"
        st.set_page_config(page_title="Top Brokers", layout='wide', page_icon="🏦")
        # app_state.restore_state_from_query_params()
        # app_state.sync_query_params_from_session()
        # app_state.check_authenticaiton_state()
        user = auth_utils.ensure_logged_in()
        self.username= user['username']
        self.role= user['role']
        self.branch = user['branch']

        activate_client_code_hotkey()
        helper.adjust_ui()
        render_sidebar()
        self.engine = create_engine(helper.get_holding_engine())
        st.title("🏦 Top Brokers", anchor=False)
        self.selected_date = st.date_input("Select Date", width=400)


    def get_data(self):
        if self.selected_date:
            # Convert the date to string, since your column is text
            date_str = self.selected_date.strftime('%Y-%m-%d')
            df = db.fetch_top_brokers(date=date_str)
            
            df.drop(columns=['date', 'DT_Row_Index'], inplace=True)
            df.rename(columns={"name":"Broker Name", "number": "Broker No.", "buyerAmount": "Buyer Amount (Rs.)", 
                               "sellerAmount": "Seller Amount (Rs.)", "totalAmount":"Total Amount (Rs.)",
                               "differ": "Difference (Rs.)", "matchingAmout": "Matching Amount (Rs.)"}, inplace=True)
            df.index = df.index + 1
            numeric_cols = df.columns.difference(['Broker Name', 'Broker No.'])
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            if not df.empty:
                idx = df.index[df['Broker Name'] == 'Trishakti Securities Public Limited'].tolist()
                st.badge(f"Trishakti's Rank: {idx[0]}", color='green')
                st.dataframe(df.style.format({col: "{:,.0f}" for col in numeric_cols}))
            else:
                st.info("No data available for selected date.", icon="📢")




if __name__ == "__main__":
    TopBrokers().get_data()