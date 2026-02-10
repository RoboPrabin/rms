import os
import time
import datetime
import streamlit as st
import extra_streamlit_components as stx
from utils import auth_utils
# Your custom imports
from config import config
from utils.security import decrypt_data, encrypt_data
from utils import page_url, security, helper
from db.db import get_user_by_username, update_login_status, create_session
class LoginPage:
    def __init__(self):
        # 1. This MUST be at the top of your login page script
        # auth_utils.ensure_logged_in()
        st.set_page_config(page_title="Login", layout="centered", page_icon="🔐")
        helper.eliminate_top_margin("-4rem")


    def handle_unregistered_user(self):
        st.error("You are not registered yet. Contact IT Department.", icon="❌")

    def handle_role_not_assigned(self):
        st.warning("Your account is created but role is not assigned. Contact admin.", icon="⚠️")

    def handle_blocked_user(self):
        st.error("Your account is blocked! ❌")

    def handle_successful_login(self, user):
        update_login_status(user["username"], success=True)
        # 1. Create the Payload
        # expiry_time = int(time.time()) + 10
        expiry_time = int(time.time()) + config.session_expiry_time 
        payload = {
            "auth": True,
            "username": user["username"].upper(),
            "role": user["role"].upper(),
            "branch": user['branch'].upper(),
            "expiry": expiry_time
        }
        # 2. Encrypt
        encrypted_token = security.encrypt_data(payload)

        auth_utils.set_cookie_instantly("auth_token", encrypted_token)        
        # 4. Update Session State (Immediate access)
        st.session_state.auth = True
        st.session_state.username = payload["username"]
        st.session_state.role = payload["role"]
        st.session_state.branch = payload["branch"]
        st.session_state.expiry = payload["expiry"]
        
        create_session(user['username'], sid=encrypted_token)
        # helper.show_message(message=user, color='green')
        st.success("Login successful! Redirecting...", icon="✅")
        
        # # # CRITICAL: Allow JS to finish writing the cookie before killing the script
        # time.sleep(0.4) 
        
        if st.session_state.role == "USER":
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
            username = st.text_input("Username",  placeholder="Enter username").upper()
            password = st.text_input("Password",  type="password", placeholder="Enter password")
            submitted = st.form_submit_button("➜] ‎ ‎‎ ‎  Login ‎ ‎ ‎ ‎ ")

            if submitted:
                if not username or not password:
                    st.warning("Please enter both username and password.")
                    return
                
                user = get_user_by_username(username)
                if user is None:
                    self.handle_unregistered_user()
                elif user.get("role") is None:
                    self.handle_role_not_assigned()
                elif user.get("status") == "BLOCKED":
                    self.handle_blocked_user()
                elif password == user.get("password"):
                    self.handle_successful_login(user)
                else:
                    self.handle_failed_login(username)


    def render_page(self):
        # self.check_logged_in()
            # return
        # else:
        self.show_login_form()
        st.markdown(
            '<div style="position: fixed; bottom: 0; left: 0; width: 100%; text-align: center; padding: 15px; font-size: 14px; color: #555; z-index: 9999;">'
            '© Trishakti Securities Limited. All rights reserved.</div>',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    LoginPage().render_page()