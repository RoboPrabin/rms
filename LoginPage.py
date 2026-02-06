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
from utils import auth_utils
class LoginPage:
    def __init__(self):
        # helper.eliminate_top_margin("-8rem")
        st.set_page_config(page_title="Login", layout="centered", page_icon="🔐")
        self.manager = stx.CookieManager(key="trishakti_auth_manager")
        # try:
        #     self.manager.delete("auth_token")
        # except Exception:
        #     pass

    # def get_manager(self):
    #     """
    #     Ensures CookieManager is created once per script run to avoid 
    #     DuplicateElementKey error while remaining refresh-proof.
    #     """
    #     if self.cookie_manager is None:
    #         self.cookie_manager = stx.CookieManager(key="trishakti_auth_manager")
    #     return self.cookie_manager

    def check_logged_in(self):
        auth_utils.ensure_logged_in()
        # """Try to auto-login using the cookie if session state is empty."""
        # manager = self.get_manager()
        
        # # Give the browser a moment to send the cookie data
        # token = manager.get("auth_token")
        # if not token:
        #     time.sleep(0.4)
        #     token = manager.get("auth_token")

        # if token:
        #     try:
        #         payload = decrypt_data(token)
        #         if payload and payload.get('auth'):
        #             current_time = int(time.time())
        #             expiry = payload.get('expiry', 0)

        #             if current_time < expiry:
        #                 # Re-hydrate session state
        #                 st.session_state.authenticated = True
        #                 st.session_state.username = payload.get("user")
        #                 st.session_state.role = payload.get("role")
        #                 st.session_state.branch = payload.get("branch")
        #                 st.session_state.expiry = expiry
                        
        #                 st.success("Welcome back! Redirecting...")
        #                 time.sleep(0.5)
                        
        #                 # Route based on role
        #                 if st.session_state.role == "USER":
        #                     st.switch_page(page_url.book_closure_url)
        #                 else:
        #                     st.switch_page(page_url.dashbord_url)
        #     except Exception as e:
        #         # Log error silently
        #         print(f"Cookie auto-login failed: {e}")

    def handle_unregistered_user(self):
        st.error("Please enter your credentials.", icon="❌")

    def handle_role_not_assigned(self):
        st.warning("Your account is created but role is not assigned. Contact admin.", icon="⚠️")

    def handle_blocked_user(self):
        st.error("Your account is blocked! ❌")

    def handle_successful_login(self, user):
        update_login_status(user["username"], success=True)
        # 1. Create the Payload
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
        # 3. SET THE COOKIE
        self.manager.set(
            "auth_token", 
            encrypted_token, 
            expires_at=datetime.datetime.now() + datetime.timedelta(days=7)
        )

        # 4. Update Session State (Immediate access)
        st.session_state.authenticated = True
        st.session_state.username = payload["username"]
        st.session_state.role = payload["role"]
        st.session_state.branch = payload["branch"]
        
        create_session(user['username'], sid=encrypted_token)

        st.success("Login successful! Redirecting...", icon="✅")
        
        # # CRITICAL: Allow JS to finish writing the cookie before killing the script
        time.sleep(0.4) 
        
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

    # def show_login_form(self):
    #     st.header("🔐 RMS Login", anchor=False)
    #     with st.form("login_form", clear_on_submit=False):
    #         username = st.text_input("Username", value="admin", placeholder="Enter username").upper()
    #         password = st.text_input("Password", value="Prabin@123", type="password", placeholder="Enter password")
    #         submitted = st.form_submit_button("➜] ‎ ‎‎ ‎  Login ‎ ‎ ‎ ‎ ")

    #         if submitted:
    #             if not username or not password:
    #                 st.warning("Please enter both username and password.")
    #                 return
                
    #             user = get_user_by_username(username)
    #             if user is None:
    #                 self.handle_unregistered_user()
    #             elif user.get("role") is None:
    #                 self.handle_role_not_assigned()
    #             elif user.get("status") == "BLOCKED":
    #                 self.handle_blocked_user()
    #             elif password == user.get("password"):
    #                 self.handle_successful_login(user)
    #             else:
    #                 self.handle_failed_login(username)


    def show_login_form(self):
        st.header("🔐 RMS Login", anchor=False)
        
        # Initialize the loading state if it doesn't exist
        if "login_loading" not in st.session_state:
            st.session_state.login_loading = False

        container = st.container(border=True)
        with container:
            username = st.text_input(
                "Username", 
                value="admin", 
                placeholder="Enter username",
                disabled=st.session_state.login_loading # Disable inputs while processing
            ).upper()
            
            password = st.text_input(
                "Password", 
                value="Prabin@123", 
                type="password", 
                placeholder="Enter password",
                disabled=st.session_state.login_loading
            )

            # The Button
            button_label = "Authenticating. Please wait..." if st.session_state.login_loading else "‎ ‎‎ ‎ ➜] ‎ ‎ Login ‎ ‎ ‎ ‎ "
            
            if st.button(
                button_label, 
                disabled=st.session_state.login_loading, 
            ):
                # Start the loading state and rerun to update UI
                st.session_state.login_loading = True
                st.rerun()

        # This part runs ONLY after the rerun triggered by the click
        if st.session_state.login_loading:
            if not username or not password:
                st.warning("Please enter both username and password.")
                st.session_state.login_loading = False
                st.rerun()
                return
            
            user = get_user_by_username(username)
            if user is None:
                self.handle_unregistered_user()
                st.session_state.login_loading = False
                st.rerun()
            elif user.get("password") == password:
                # On success, keep it disabled and proceed
                self.handle_successful_login(user)
                # Note: handle_successful_login will handle the redirect
            else:
                self.handle_failed_login(username)
                st.session_state.login_loading = False
                st.rerun()


    def render_page(self):
        # self.check_logged_in()
        self.show_login_form()
        
        st.markdown(
            '<div style="position: fixed; bottom: 0; left: 0; width: 100%; text-align: center; padding: 15px; font-size: 14px; color: #555; z-index: 9999;">'
            '© Trishakti Securities Limited. All rights reserved.</div>',
            unsafe_allow_html=True
        )

if __name__ == "__main__":
    LoginPage().render_page()