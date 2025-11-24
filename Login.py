#Login.py
import time
import streamlit as st
import app_state
from db.db import get_user_by_username
from utils import page_url
from utils import security
class LoginPage:
    def __init__(self):
        st.set_page_config(page_title="Login", layout="centered", page_icon="🔐")

    def check_logged_in(self):    
        # If already logged in, redirect automatically
        # if is_logged_in():
        #     st.success("Already logged in, redirecting...")
        #     time.sleep(0.5)
        #     st.switch_page(page_url.dashbord_url)
        # 1) Restore from query params first
        app_state.restore_state_from_query_params()
        # 2) If already authenticated, bounce to dashboard
        app_state.check_authentication_state_login_page()

    def show_login_form(self):
        st.title("🔐Login Portal", anchor=False)
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                user = get_user_by_username(username)
                if user and password == user["password"]:
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

                    st.success("Login successful! 👍")
                    time.sleep(0.3)
                    st.switch_page("pages/_Dashboard.py")



    def render_page(self):
        self.check_logged_in()
        self.show_login_form()

        # Fixed bottom footer (clean & professional)
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
    login_page = LoginPage()
    login_page.render_page()