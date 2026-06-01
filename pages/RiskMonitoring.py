from time import sleep
from nepali_datetime import date as nepali_date
from datetime import date
from psycopg2.extras import execute_values

import numpy as np
import streamlit as st
import pandas as pd
from utils import auth_utils, helper
from datetime import datetime, timedelta
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config
from utils.custom_hotkey import activate_client_code_hotkey
from db import db
from pages.BasePage import BasePage

class RiskMonitoring(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "aml"
        st.set_page_config("Risk Monitoring", page_icon="🚨", layout='wide')

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")

        self.today_np_date = nepali_date.today()
        today_np = nepali_date.today()


        activate_client_code_hotkey()
        # user = auth_utils.ensure_logged_in()
        # self.username= user['username']
        # self.role= user['role']
        # self.branch = user['branch']
        navigation.render_sidebar()

        # DB Connection
        self.holding_engine = helper.get_holding_engine()
        st.header("🚨 Risk Monitoring ", anchor=False)

if __name__ == "__main__":
    page = RiskMonitoring()