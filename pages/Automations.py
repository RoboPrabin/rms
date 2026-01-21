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


class Automation:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "user"
        activate_client_code_hotkey()


        st.set_page_config("Automations", page_icon="⚡", layout='wide')

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

        st.header("⚡ Automations", anchor=False)


    # ✅ Strong password generator
    def generate_strong_password(self, length=12):
        alphabet = string.ascii_letters + string.ascii_uppercase
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    # ✅ Reset ALL passwords in DB
    def reset_all_passwords(self):
        conn = db.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT username FROM app_user")
        users = cur.fetchall()

        updated = []

        for (username,) in users:
            new_pass = self.generate_strong_password()
            cur.execute(
                "UPDATE app_user SET password = %s WHERE username = %s",
                (new_pass, username)
            )
            updated.append((username, new_pass))

        conn.commit()
        cur.close()
        conn.close()

        return updated

    # ✅ Main UI
    def get_all_users(self):
        rows = db.get_all_app_user()
        df = pd.DataFrame(rows, columns=["username", "role", "phone", "password", "email"])
        df.columns = df.columns.str.upper()
        selection = st.dataframe(
            df,
            key="user_table",
            selection_mode="multi-row",
            on_select="rerun"
        )

        selected_df = df.iloc[selection.selection.rows] if selection.selection.rows else pd.DataFrame()


        # Initialize sending state
        if "sending" not in st.session_state:
            st.session_state.sending = False
        if "generating" not in st.session_state:
            st.session_state.generating = False

        col1, spcr, col2 = st.columns([1,1,1], gap="small")

        with col1:
            if st.session_state.sending:
                st.button("Sending…", icon="⏳", disabled=True, use_container_width=True)
            else:
                if st.button("Send credentials", icon="✈️", use_container_width=True):
                    st.session_state.sending = True
                    st.rerun()

        with col2:
            if st.session_state.generating:
                st.button("Generating…", icon="♻️", disabled=True, use_container_width=True)
            else:
                if st.button("Generate strong password", icon="♻️", use_container_width=True):
                    st.session_state.generating = True
                    st.rerun()

        # Generating process
        if st.session_state.generating:
            self.reset_all_passwords()
            st.session_state.generating = False
            sleep(1)
            st.rerun()

        # Email sending process
        if st.session_state.sending:
            if not selected_df.empty:
                with st.spinner("Sending credentials… please wait"):
                    results = send_bulk_email(
                        selected_df,
                        body="Your RMS login details:\n"
                    )
                for email, ok in results:
                    if ok:
                        st.success(f"Sent to {email}")
                    else:
                        st.error(f"Failed to send to {email}")
            st.session_state.sending = False
            sleep(1)
            st.rerun()

    def render_page(self):
        mode = st.radio("Mode", ['App users', "Others", "Next"], horizontal=True)
        if mode == "App users":
            self.get_all_users()


if __name__ == "__main__":
    Automation().render_page()    