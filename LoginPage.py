import os
os.system('')
import time
import datetime
import streamlit as st
from utils import auth_utils
from config import config
from utils.security import decrypt_data, encrypt_data
from utils import page_url, security, helper
from db.db import get_user_by_username, update_login_status, create_session

class LoginPage:
    def __init__(self):
        # 1. Page config MUST be first
        st.set_page_config(page_title="Login", layout="centered", page_icon="🔐")
        helper.eliminate_top_margin("-4rem")

    def handle_unregistered_user(self):
        st.error("You are not registered yet. Contact IT Department.", icon="❌")

    def handle_role_not_assigned(self):
        st.warning("Your account is created but role is not assigned. Contact admin.", icon="⚠️")

    def handle_blocked_user(self):
        st.error("Your account is blocked! ❌")

    def handle_successful_login(self, user):
        """
        user is a TUPLE from SQL: 
        (0:username, 1:role, 2:password, 3:status, 4:citizenship, 5:phone, 6:email, 7:branch)
        """
        db_username = user[0]
        db_role = user[1]
        db_branch = user[7]

        update_login_status(db_username, success=True)
        st.success("Login successful! Loding your resources. \nPlease wait...", icon="✅")
        expiry_time = int(time.time()) + 60
       
        # expiry_time = int(time.time()) + config.session_expiry_time 
        payload = {
            "auth": True,
            "username": str(db_username).upper(),
            "role": str(db_role).upper(),
            "branch": str(db_branch).upper(),
            "expiry": expiry_time
        }
        encrypted_token = security.encrypt_data(payload)
        # st.query_params.update({"sid": encrypted_token})
        st.query_params["sid"] = encrypted_token
        st.session_state.update(payload)
        st.session_state.sid = encrypted_token

        create_session(db_username, sid=encrypted_token)
        helper.show_message(message=f"{user}", color='green')
        if payload["role"] == "USER":
            st.switch_page(page_url.book_closure_url)
        else:
            st.switch_page(page_url.dashbord_url)


    def handle_failed_login(self, username):
        remaining = update_login_status(username, success=False)
        if remaining <= 0:
            st.error("Account blocked. Contact admin.", icon="❌")
        else:
            st.warning(f"Invalid credentials! {remaining} attempts remaining.", icon="⚠️")

    def show_login_form(self):
        st.header("🔐 RMS Login", anchor=False)
        with st.form("login_form", clear_on_submit=False):
            username_input = st.text_input("Username",  placeholder="Enter username").upper()
            password_input = st.text_input("Password",  type="password", placeholder="Enter password")
            submitted = st.form_submit_button("➜ Login")

            if submitted:
                if not username_input or not password_input:
                    st.warning("Please enter both username and password.")
                    return
                
                user = get_user_by_username(username_input)
                
                if user is None:
                    self.handle_unregistered_user()
                else:
                    # Column Mapping for Tuple: 0:user, 1:role, 2:pass, 3:status
                    db_password = user[2]
                    db_status = user[3]
                    db_role = user[1]

                    if db_role is None:
                        self.handle_role_not_assigned()
                    elif db_status == "BLOCKED":
                        self.handle_blocked_user()
                    elif password_input == db_password:
                        self.handle_successful_login(user)
                    else:
                        self.handle_failed_login(username_input)

    def render_page(self):
        self.show_login_form()
        st.markdown(
            '<div style="position: fixed; bottom: 0; left: 0; width: 100%; text-align: center; padding: 15px; font-size: 14px; color: #555; z-index: 9999;">'
            '© Trishakti Securities Limited. All rights reserved.</div>',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    LoginPage().render_page()