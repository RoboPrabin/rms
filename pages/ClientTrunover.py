import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from utils.custom_hotkey import activate_client_code_hotkey
from utils import auth_utils, helper
from db import db
from nepali_datetime import date as nepali_date
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from pages.BasePage import BasePage

class ClientTurnover(BasePage):
    def __init__(self):
        super().__init__()

        helper.eliminate_top_padding()
        st.session_state.active_menu = "aml"
        activate_client_code_hotkey()
        st.set_page_config("Client turnover", page_icon="🅱️", layout='wide')

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()

        navigation.render_sidebar()
        st.header("🅱️ Client Turnover", anchor=False)

if __name__ == "__main__":
    ClientTurnover()