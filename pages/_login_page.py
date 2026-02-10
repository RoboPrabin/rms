
# Login.py
from utils import page_url
import time
import streamlit as st
import streamlit_bridge.app_state as app_state
from db.db import get_user_by_username, update_login_status, create_session
from utils import security, helper


class LoginPage:
    def __init__(self):
        st.set_page_config(page_title="Login", layout="centered", page_icon="🔐")

    # ---------------------------
    # State checks
    # ---------------------------
    def check_logged_in(self):
        app_state.restore_state_from_query_params()
        app_state.check_authentication_state_login_page()

    # ---------------------------
    # Validation helpers
    # ---------------------------
    def handle_unregistered_user(self):
        st.error("You are not registered yet. Please contact your admin.", icon="❌")
        st.stop()

    def handle_role_not_assigned(self):
        st.warning(
            "Your account has already been created but role has not been assigned yet.  \n"
            "Please contact your admin.",
            icon="⚠️"
        )
        st.stop()

    def handle_blocked_user(self):
        st.error("Your account is blocked after multiple failed login attempts! ❌")

    def handle_successful_login(self, user, password):
        # reset failed_attempts on success
        update_login_status(user["username"], success=True)

        payload = {
            "auth": True,
            "user": user["username"].upper(),
            "role": user["role"].upper()
        }
        encrypted = security.encrypt_data(payload)

        st.session_state.authenticated = True
        st.session_state.username = payload["user"]
        st.session_state.role = payload["role"]

        st.query_params["sid"] = encrypted
        create_session(username=user["username"])

        st.success("Login successful! 👍 Redirecting...")
        time.sleep(0.5)
        st.switch_page(page_url.dashbord_url)

    def handle_failed_login(self, username):
        remaining = update_login_status(username, success=False)
        if remaining == 0:
            st.error("Your account has now been blocked. Please contact admin.", icon="❌")
        else:
            st.warning(
                f"Invalid username or password! You have {remaining} attempts remaining.",
                icon="⚠️"
            )

    # ---------------------------
    # Main form
    # ---------------------------
    def show_login_form(self):
        st.title("🔐 Login Portal", anchor=False)

        with st.form("login_form"):
            username = st.text_input("Username", icon="🧑🏻‍🦱").upper()
            password = st.text_input("Password", type="password", icon="🔑")
            submitted = st.form_submit_button("Login")

            if not submitted:
                return

            user = get_user_by_username(username)
            if user is None:
                self.handle_unregistered_user()
                return

            if user["role"] is None:
                self.handle_role_not_assigned()
                return

            helper.show_message(str(user), color="yellow")

            if user["status"] == "BLOCKED":
                self.handle_blocked_user()
            elif password == user["password"]:
                self.handle_successful_login(user, password)
            else:
                self.handle_failed_login(username)

    # ---------------------------
    # Page renderer
    # ---------------------------
    def render_page(self):
        self.check_logged_in()
        self.show_login_form()
        st.markdown(
            """
            <div style="
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                text-align: center;
                padding: 15px;
                font-size: 14px;
                color: #555;
                z-index: 9999;
            ">
                © Trishakti Securities Limited. All rights reserved.
            </div>
            """,
            unsafe_allow_html=True
        )


if __name__ == "__main__":
    LoginPage().render_page()