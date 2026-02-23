import time
import streamlit as st
from utils import page_url
from utils.security import decrypt_data

def bootstrap_session():
    sid = st.query_params.get("sid") or st.session_state.get("sid")
    try:
        if not st.session_state.get("auth") or st.session_state.get("sid") != sid:
            payload = decrypt_data(sid)
            st.session_state.update(payload)
            st.session_state.sid = sid
    except Exception:
        st.switch_page(page_url.login_url)
        st.stop()
        return
    remaining = st.session_state.get("expiry", 0) - int(time.time())
    if remaining <= 0:
        st.query_params.clear()
        st.session_state.clear()
        st.error("Session expired.", icon="⏰")
        if st.button("Back to Login", icon="🔐", key="exp_btn"):
            st.switch_page(page_url.login_url)
        st.stop()
    if "sid" not in st.query_params:
        st.query_params["sid"] = sid