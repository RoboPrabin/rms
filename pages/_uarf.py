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
class Uarf:
    def __init__(self):
        st.set_page_config("UARF", page_icon="🪪", layout='wide')

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")

        self.today_np_date = nepali_date.today()
        today_np = nepali_date.today()
        # Authentication & User Info
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()

        # DB Connection
        self.holding_engine = helper.get_holding_engine()

        st.header("🪪 User Access Request Form", anchor=False)
        st.info("Page is under construction.", icon="📢")

    def render_page(self):
        pass
if __name__ == "__main__":
    Uarf().render_page()