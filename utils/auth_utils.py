# auth_utils.py
import extra_streamlit_components as stx
import streamlit as st
from utils.security import decrypt_data
from time import sleep


def ensure_logged_in():
    if st.session_state.get("authenticated") and st.session_state.get("username"):
        return {
            "username": st.session_state.username,
            "role": st.session_state.role,
            "branch": st.session_state.branch
        }
    
    controller = stx.CookieManager()
    val = controller.get("auth_token")
    sleep(0.6)
    payload = decrypt_data(val)
    st.session_state.authenticated = True
    st.session_state.username = payload["username"]
    st.session_state.role = payload["role"]
    st.session_state.branch = payload["branch"]
    return payload
