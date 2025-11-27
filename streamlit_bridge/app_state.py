import streamlit as st
import time
from utils.security import decrypt_data, encrypt_data
from utils import helper

def restore_state_from_query_params():
    params = st.query_params
    # helper.show_message("Restoring state from query params:" + str(params))
    if "sid" not in params:
        return

    try:
        payload = decrypt_data(params["sid"])

        if payload.get("auth") is True:
            st.session_state.authenticated = True
            st.session_state.username = payload.get("user", "Guest")
            st.session_state.role = payload.get("role", "User")

    except Exception as e:
        print("SID decryption failed:", e)
        st.session_state.authenticated = False

def check_authenticaiton_state():
    # Gate: only allow if authenticated
    if not st.session_state.get("authenticated", False):
        st.warning("Please log in via the Login page to access the dashboard.")
        if st.button("Go to Login Page"):
            st.info("Redirecting to Login page...")
            st.switch_page("Login.py")
        st.stop()

def sync_query_params_from_session():
    if st.session_state.get("authenticated") and "sid" not in st.query_params:
        payload = {
            "auth": True,
            "user": st.session_state.username,
            "role": st.session_state.role
        }
        st.query_params["sid"] = encrypt_data(payload)

def get_current_user_info():
    username = st.session_state.get("username", "NF")
    role = st.session_state.get("role", "NF")
    return username, role

def check_authentication_state_login_page():
    # If already authenticated, redirect to Dashboard
    if st.session_state.get("authenticated", False):
        st.success("Already logged in, redirecting...")
        time.sleep(0.3)
        st.switch_page("pages/_Dashboard.py")
