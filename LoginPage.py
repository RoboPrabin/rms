import os
os.system('')
import time
import datetime
import streamlit as st
from utils import auth_utils
from config import config
from utils.security import decrypt_data, encrypt_data
from utils import page_url, security, helper
from db.db import get_user_by_username_for_login, update_login_status, create_session, get_user_by_pin_for_login, update_login_status_by_pin
from pages.BasePage import BasePage

def check_loggedin():
    sid = st.query_params.get("sid") or st.session_state.get("sid")
    if sid:
        payload = decrypt_data(sid)
        remaining = st.session_state.get("expiry", 0) - int(time.time())
        if remaining <= 0:
            st.query_params.clear()
            st.session_state.clear()
        else:
            if payload["role"] == "USER":
                st.switch_page(page_url.book_closure_url)
            else:
                st.switch_page(page_url.dashbord_url)

class LoginPage(BasePage):
    def __init__(self):


        # 1. Page config MUST be first
        st.set_page_config(page_title="Login", layout="centered", page_icon="🔐")
        helper.eliminate_top_margin("-4rem")
        check_loggedin()


    def handle_unregistered_user(self):
        st.error("You are not registered yet. Contact IT Department.", icon="❌")

    def handle_role_not_assigned(self):
        st.warning("Your account is created but role is not assigned. Contact admin.", icon="⚠️")

    def handle_blocked_user(self):
        st.error("Your account is blocked! ❌")

    def handle_successful_login(self, user, gateway=None):
        """
        user is a TUPLE from SQL: 
        (0:username, 1:role, 2:password, 3:status, 4:citizenship, 5:phone, 6:email, 7:branch)
        """
        db_id = user[0]
        db_username = user[1]
        db_role = user[2]
        db_branch = user[8]

        update_login_status(db_username, success=True)
        # expiry_time = int(time.time()) + 60
       
        expiry_time = int(time.time()) + config.session_expiry_time 
        payload = {
            "auth": True,
            "username": str(db_username).upper(),
            "role": str(db_role).upper(),
            "branch": str(db_branch).upper(),
            "expiry": expiry_time,
            'id': db_id
        }
        encrypted_token = security.encrypt_data(payload)
        # st.query_params.update({"sid": encrypted_token})
        st.query_params["sid"] = encrypted_token
        time.sleep(0.2)
        st.session_state.update(payload)
        st.session_state.sid = encrypted_token

        st.success("Login successful! Loding your resources. \nPlease wait...", icon="✅")
        create_session(db_username, sid=encrypted_token)
        if gateway == "pin":
            helper.show_message(message=f"{user}", color='cyan')
        else:
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
    def handle_failed_login_by_pin(self, pin):
        remaining = update_login_status_by_pin(pin, success=False)
        if remaining <= 0:
            st.error("Account blocked. Contact admin.", icon="❌")
        else:
            st.warning(f"Invalid credentials! {remaining} attempts remaining.", icon="⚠️")


    def login_up_ui(self):
        with st.form("login_form", clear_on_submit=False):
            username_input = st.text_input("Username",  placeholder="Enter username", icon="🔒").upper()
            password_input = st.text_input("Password",  type="password", placeholder="Enter password", icon="🔑")
            submitted = st.form_submit_button("➜ Login")

            if submitted:
                if not username_input or not password_input:
                    st.warning("Please enter both username and password.")
                    return
                
                user = get_user_by_username_for_login(username_input)
                if user is None:
                    self.handle_unregistered_user()
                else:
                    db_password = user[3]
                    db_status = user[4]
                    db_role = user[2]

                    if db_role is None:
                        self.handle_role_not_assigned()
                    elif db_status == "BLOCKED":
                        self.handle_blocked_user()
                    elif password_input == db_password:
                        self.handle_successful_login(user)
                    else:
                        self.handle_failed_login(username_input)

    def login_pin_ui(self):
        pin_pass = st.text_input("Enter your PIN", key="pin_input", icon="🔐")

        if pin_pass:  # Only validate if something is entered
            # Check if numeric
            if not pin_pass.isdigit():
                st.error("PIN must be numeric.", icon="❌")
                st.stop()

            # Check length
            elif len(pin_pass) != 6:
                st.error("Invalid PIN length.", icon="❌")
                st.stop()
            user = get_user_by_pin_for_login(pin_pass)
            if user is None:
                self.handle_unregistered_user()
            else:
                db_pin = user[3]
                db_status = user[4]
                db_role = user[2]

                if db_role is None:
                    self.handle_role_not_assigned()
                elif db_status == "BLOCKED":
                    self.handle_blocked_user()
                elif pin_pass == db_pin:
                    self.handle_successful_login(user, gateway="pin")
                else:
                    self.handle_failed_login_by_pin(pin_pass)
           
    def show_login_form(self):
        st.header("🔐 RMS Login", anchor=False)
        tabs = st.tabs(["Username & Password", "PIN"], default="PIN")
        with tabs[0]:
            st.markdown("Please enter your username and password to access the RMS.")
            self.login_up_ui()
        with tabs[1]:
            st.markdown("Please enter your secure PIN to access the RMS.")
            self.login_pin_ui()



    def render_page(self):
        self.show_login_form()
        st.markdown(
            '<div style="position: fixed; bottom: 0; left: 0; width: 100%; text-align: center; padding: 15px; font-size: 14px; color: #555; z-index: 9999;">'
            '© Trishakti Securities Limited. All rights reserved.</div>',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    LoginPage().render_page()