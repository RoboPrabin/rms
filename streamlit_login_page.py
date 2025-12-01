# import time
# import streamlit as st
# import app_state
# from db.db import get_user_by_username
# from utils import security

# class LoginPage:
#     def __init__(self):
#         st.set_page_config(
#             page_title="Login", 
#             layout="wide", 
#             page_icon="🔐"
#         )
#         self.set_background()

#     def set_background(self):
#         # Optional: nice gradient background
#         st.markdown(
#             """
#             <style>
#             body {
#                 background: linear-gradient(135deg, #003F8C, #24A148);
#                 color: white;
#             }
#             .login-card {
#                 background-color: rgba(255, 255, 255, 0.95);
#                 padding: 40px;
#                 border-radius: 15px;
#                 box-shadow: 0 8px 20px rgba(0,0,0,0.3);
#                 color: #000;
#             }
#             .stButton>button {
#                 background-color: #003F8C;
#                 color: white;
#                 font-weight: bold;
#                 border-radius: 8px;
#                 padding: 10px 20px;
#             }
#             .stButton>button:hover {
#                 background-color: #002C70;
#                 color: #fff;
#             }
#             </style>
#             """, 
#             unsafe_allow_html=True
#         )

#     def check_logged_in(self):    
#         app_state.restore_state_from_query_params()
#         app_state.check_authentication_state_login_page()

#     def show_login_form(self):
#         st.markdown("<h1 style='text-align:center; color:white;'>🔐 Trishakti Login</h1>", unsafe_allow_html=True)
#         st.markdown("<br>", unsafe_allow_html=True)

#         col1, col2, col3 = st.columns([1, 2, 1])
#         with col2:
#             st.markdown('<div class="login-card">', unsafe_allow_html=True)
#             with st.form("login_form"):
#                 st.markdown("## Welcome Back!", unsafe_allow_html=True)
#                 st.markdown("Please enter your credentials to login.\n\n", unsafe_allow_html=True)
                
#                 username = st.text_input("Username", placeholder="Enter your username")
#                 password = st.text_input("Password", type="password", placeholder="Enter your password")
                
#                 submitted = st.form_submit_button("Login")
#                 if submitted:
#                     user = get_user_by_username(username)
#                     if user and password == user["password"]:
#                         payload = {
#                             "auth": True,
#                             "user": user["username"].upper(),
#                             "role": user["role"].upper()
#                         }

#                         encrypted = security.encrypt_data(payload)

#                         st.session_state.authenticated = True
#                         st.session_state.username = payload["user"]
#                         st.session_state.role = payload["role"]

#                         st.query_params["sid"] = encrypted

#                         st.success("Login successful! 👍 Redirecting...")
#                         time.sleep(0.5)
#                         st.switch_page("pages/_Dashboard.py")
#                     else:
#                         st.error("Invalid username or password! ❌")
#             st.markdown('</div>', unsafe_allow_html=True)

#     def render_page(self):
#         self.check_logged_in()
#         self.show_login_form()
#         st.markdown(
#             """
#             <div style="
#                 position: fixed;
#                 bottom: 0;
#                 left: 0;
#                 width: 100%;
#                 text-align: center;
#                 padding: 10px;
#                 font-size: 14px;
#                 color: #fff;
#                 background-color: rgba(0,0,0,0.2);
#                 z-index: 9999;
#             ">
#                 © Trishakti Securities Limited. All rights reserved.
#             </div>
#             """,
#             unsafe_allow_html=True
#         )

# if __name__ == "__main__":
#     login_page = LoginPage()
#     login_page.render_page()






#Login.py
import time
import streamlit as st
import streamlit_bridge.app_state as app_state
from db.db import get_user_by_username, update_login_status, create_session
from utils import page_url
from utils import security
from utils import helper

class LoginPage:
    def __init__(self):
        st.set_page_config(page_title="Login", layout="centered", page_icon="🔐")

    def check_logged_in(self):    
        app_state.restore_state_from_query_params()
        app_state.check_authentication_state_login_page()

    def show_login_form(self):
        st.title("🔐Login Portal", anchor=False)
        with st.form("login_form"):
            username = st.text_input("Username", icon="🧑🏻‍🦱").lower()
            password = st.text_input("Password", type="password", icon="🔑")
            submitted = st.form_submit_button("Login")

            if submitted:
                user = get_user_by_username(username)
                print(user)
                if user and user["status"] == "BLOCKED":
                    st.error("Your account is blocked after multiple failed login attempts! ❌")
                elif user and password == user["password"]:
                    # reset failed_attempts on success
                    update_login_status(username, success=True)

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
                    create_session(username=user['username'].upper())
                    st.success("Login successful! 👍. Redirecting .....")
                    time.sleep(0.5)
                    st.switch_page("pages/_Dashboard.py")
                else:
                    # wrong password → increment failed attempts and get remaining
                    if user:
                        remaining = update_login_status(username, success=False)
                        if remaining == 0:
                            st.error("Your account has now been blocked. Plesase contact admin.", icon="❌")
                        else:
                            st.warning(f"Invalid username or password! You have {remaining} attempts remaining.", icon="⚠️")
                            # st.toast(f"Invalid username or password! You have {remaining} attempts remaining.", icon="⚠️")
                    else:
                        st.error("You are not register yet. Please contact admin.", icon="❌")



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
    login_page = LoginPage()
    login_page.render_page()