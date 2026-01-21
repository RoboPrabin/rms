from utils.custom_hotkey import activate_client_code_hotkey
from time import sleep
import secrets
import string
from utils.mailer import *

from db import db
from nepali_datetime import date as nepali_date
from datetime import date

import numpy as np
import streamlit as st
import pandas as pd
from utils import helper
from datetime import datetime, timedelta
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config
from db import db
import requests

class TransactionMonitoring:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "aml"
        activate_client_code_hotkey()

        st.set_page_config("AML - Transaction Monitoring", page_icon="🕵🏻", layout='wide')

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()

        # Authentication
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role, self.branch = app_state.get_current_user_info()
        navigation.render_sidebar()


        # DB
        self.holding_engine = helper.get_holding_engine()

        st.header("🕵🏻 AML - Transaction Monitoring", anchor=False)
        st.header("⚠️ Page under construction", anchor=False)

    # st.set_page_config(page_title="Custom Hotkeys", layout="wide")
    # ---------------- API HELPERS ----------------
    def get_token(username, password):
        resp = requests.post(
            config.LOGIN_API,
            json={"userName": username, "password": password},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json().get("token")

    def render_page(self):
        mode = st.radio("Mode", ['Traders Info', 'Populate Traders Info'], horizontal=True, index=1)
        if mode == 'Populate Traders Info':
            df = db.get_unique_client_code_from_floorsheet()
            df.rename(columns={'clientcode':'Client Code'}, inplace=True)
            df['Client Name']=''
            df['Occupation']=''
            df['Company'] = ''
            st.badge(f"Remaining data: {len(df):,.0f}", color='red')
            df.index = df.index + 1
            st.dataframe(df)
            st.button("Start fetching info", icon="🧲")

if __name__ == "__main__":
    TransactionMonitoring().render_page()    