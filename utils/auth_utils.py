# # auth_utils.py
# import extra_streamlit_components as stx
# import streamlit as st
# from utils.security import decrypt_data
# from time import sleep


# def ensure_logged_in():
#     if st.session_state.get("authenticated") and st.session_state.get("username"):
#         return {
#             "username": st.session_state.username,
#             "role": st.session_state.role,
#             "branch": st.session_state.branch
#         }
    
#     controller = stx.CookieManager()
#     val = controller.get("auth_token")
#     sleep(0.6)
#     payload = decrypt_data(val)
#     st.session_state.authenticated = True
#     st.session_state.username = payload["username"]
#     st.session_state.role = payload["role"]
#     st.session_state.branch = payload["branch"]
#     st.session_state.expiry = payload["expiry"]
#     return payload


import time
import streamlit as st
import extra_streamlit_components as stx
from utils import page_url
from utils.security import decrypt_data


def ensure_logged_in():
    now = int(time.time())

    # 1️⃣ Already authenticated & not expired
    if (
        st.session_state.get("auth")
        and st.session_state.get("expiry", 0) > now
    ):
        return {
            "username": st.session_state.username,
            "role": st.session_state.role,
            "branch": st.session_state.branch,
            "expiry": st.session_state.expiry,
            "auth": st.session_state.auth
        }

    # 2️⃣ Check cookie
    controller = stx.CookieManager()
    token = controller.get("auth_token")

    if not token:
        redirect_to_login()
        st.stop()

    payload = decrypt_data(token)

    # 3️⃣ Expired token
    if payload["expiry"] <= now:
        controller.delete("auth_token")
        st.session_state.clear()
        redirect_to_login()
        st.stop()

    # 4️⃣ Restore session
    st.session_state.auth = True
    st.session_state.username = payload["username"]
    st.session_state.role = payload["role"]
    st.session_state.branch = payload["branch"]
    st.session_state.expiry = payload["expiry"]

    return payload


def redirect_to_login():
    st.error("Session expired.", icon="🚨")
    if st.button("Go to Login Page", icon="🔐"):
        st.switch_page(page_url.login_url)


def redirect_to_dashboard():
    st.switch_page(page_url.dashbord_url)


