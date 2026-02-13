import asyncio
import os
import time
import datetime
import streamlit as st
from assets.lottie_anim import show_login_animation
# Custom imports - ensuring these match your project structure
from service.otp_service import create_user_otp
from config import config
from utils.security import decrypt_data, encrypt_data
from utils import page_url, security, helper
from db.db import (
    get_user_by_username_for_login, 
    update_login_status, 
    create_session, 
    get_user_by_pin_for_login, 
    update_login_status_by_pin
)
from pages.BasePage import BasePage


class LoginPage(BasePage):
    def __init__(self):
        helper.eliminate_top_margin("-4rem")
        # 1. Page config MUST be first
        st.set_page_config(page_title="Login", layout="centered", page_icon="🔐")

        # Initialize session state only if it doesn't exist.
        if "has_sent_otp" not in st.session_state:
            st.session_state.has_sent_otp = False
        
        # Immediate redirect if OTP was already successfully sent in this session
        if st.session_state.has_sent_otp:
            st.switch_page(page_url.otp_url)
            st.stop()

    def handle_unregistered_user(self):
        st.error("You are not registered yet. Contact IT Department.", icon="❌")

    def handle_role_not_assigned(self):
        st.warning("Your account is created but role is not assigned. Contact admin.", icon="⚠️")

    def handle_blocked_user(self):
        st.error("Your account is blocked! ❌")

    def handle_successful_login(self, user, gateway=None):
        """
        Processes successful auth and redirects to OTP using st.status for feedback.
        user mapping: (0:id, 1:username, 2:role, 3:pin/pass, 4:status, ..., 7:email, 8:branch)
        """
        db_id = user[0]
        db_username = user[1]
        db_role = user[2]
        db_email = user[7]
        db_branch = user[8]

        # Use a placeholder to contain the status box so we can clear it later
        status_placeholder = st.empty()

        with status_placeholder.container():
            with st.status("Authenticating...", expanded=True) as status:
                # Step 1: Authentication Logic
                st.write("✅ User authenticated successfully...")
                update_login_status(db_username, success=True)
                expiry_time = int(time.time()) + config.session_expiry_time 
                payload = {
                    "auth": True,
                    "username": str(db_username).upper(),
                    "role": str(db_role).upper(),
                    "branch": str(db_branch).upper(),
                    "expiry": expiry_time,
                    'id': db_id,
                    'email': db_email
                }
                
                encrypted_token = security.encrypt_data(payload)
                st.query_params["sid"] = encrypted_token
                
                # Update Session State
                st.session_state.update(payload)
                st.session_state.sid = encrypted_token
                st.session_state.email = db_email
                time.sleep(0.5)

                # Step 2: Sending OTP
                status.update(label="Sending OTP...", state="running")
                st.write("✅ OTP is being sent to your registered email. Please wait...")

                try:
                    asyncio.run(create_user_otp(db_username, db_email))
                    st.session_state.has_sent_otp = True
                    st.write(f"✅ OTP successfully sent to `{db_email}`")
                except Exception as e:
                    status.update(label="Failed to send OTP", state="error")
                    st.error(f"Error: {e}")
                    st.stop()
                
                # Step 3: Session Creation
                st.write("✅ Redirecting...")
                # st.write("✅ Creating secure session...")
                create_session(db_username, sid=encrypted_token)
                # Step 4: Finalize
                time.sleep(0.8)

        # Clear the status UI and move to OTP page
        # status_placeholder.empty()
        st.switch_page(page_url.otp_url)
        st.stop()

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
            show_login_animation()
            username_input = st.text_input("Username", placeholder="Enter username", icon="🔒").upper().strip()
            password_input = st.text_input("Password", type="password", placeholder="Enter password", icon="🔑").strip()
            submitted = st.form_submit_button(" ➜ Login ")

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
        with st.form("pin_form", clear_on_submit=True):
            show_login_animation()
            pin_pass = st.text_input("Enter your secure PIN", type='password', icon="🔐")
            pin_submitted = st.form_submit_button("Unlock 🔓")

            if pin_submitted:
                if not pin_pass.isdigit():
                    st.error("PIN must be numeric.", icon="❌")
                elif len(pin_pass) != 8:
                    st.error("PIN length not matched.", icon="❌")
                else:
                    user = get_user_by_pin_for_login(pin_pass)
                    if user is None:
                        self.handle_unregistered_user()
                    else:
                        db_status = user[4]
                        db_role = user[2]

                        if db_role is None:
                            self.handle_role_not_assigned()
                        elif db_status == "BLOCKED":
                            self.handle_blocked_user()
                        elif pin_pass == user[3]:
                            self.handle_successful_login(user, gateway="pin")
                        else:
                            self.handle_failed_login_by_pin(pin_pass)
           
    # def show_login_form(self):
    #     col1, col2, col3 = st.columns([1, 2, 1])
    #     with col2:
    #         st.header("🔐 RMS Login", anchor=False)
    #         tabs = st.tabs(["PIN Access", "Username & Password"], width=600)
            
    #         with tabs[0]:
    #             st.markdown("Enter your secure PIN to access the RMS.")
    #             self.login_pin_ui()
    #         with tabs[1]:
    #             st.markdown("Enter your username and password to access the RMS.")
    #             self.login_up_ui()


    def show_login_form(self):
        # CSS to lock the width and center the box
        st.markdown("""
            <style>
            /* 1. Create a fixed-width 'Card' for the login */
            .login-card {
                max-width: 100px;
                margin: 0 auto; /* This is the magic for centering fixed elements */
            }

            /* 2. Force headers and tab-labels to center within that card */
            .login-card h2 {
                text-align: center !important;
            }
            </style>
        """, unsafe_allow_html=True)

        # Wrap the entire form in the 'login-card' div
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        
        st.header("🔐 RMS Login", anchor=False)
        
        tabs = st.tabs(["PIN Access", "Username & Password"])
        
        with tabs[0]:
            st.markdown("Enter your secure PIN to access the RMS.")
            self.login_pin_ui()
            
        with tabs[1]:
            st.markdown("Enter your username and password to access the RMS.")
            self.login_up_ui()
            
        st.markdown('</div>', unsafe_allow_html=True)


    # def show_login_form(self):
    #     # We use a 3-column layout to center the entire block on the screen
    #     # [Left Spacer, Animation Column, Form Column, Right Spacer]
    #     # Adjust [1, 1, 2, 1] to [0.5, 1, 2, 0.5] if you want it wider
    #     col_anim, _, col_form, _ = st.columns([3, 1, 3, 1])

    #     with col_anim:
    #         # This keeps the animation vertically aligned with the form header
    #         st.write("##") # Add a small spacer to push the animation down slightly
    #         show_login_animation()

    #     with col_form:
    #         st.header("🔐 RMS Login", anchor=False)
            
    #         # Using a container with a border makes the form look like a distinct card
    #         tabs = st.tabs(["PIN Access", "Username & Password"])
            
    #         with tabs[0]:
    #             st.caption("Enter your secure PIN to access the RMS.")
    #             self.login_pin_ui()
                
    #         with tabs[1]:
    #             st.caption("Enter credentials to access the RMS.")
    #             self.login_up_ui()


    def render_page(self):
        self.show_login_form()
        st.markdown(
            '<div style="width: 100%; text-align: center; margin-top: 0px; font-size: 14px; color: #555;">'
            '© Trishakti Securities Limited. All rights reserved.</div>',
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    LoginPage().render_page()

