import time
import streamlit as st
from utils import page_url
from utils.security import decrypt_data

def bootstrap_session():
    # If already authenticated in session, skip
    if st.session_state.get("auth"):
        return

    # Get sid from query params
    sid = st.query_params.get("sid")

    if not sid:
        st.warning("Session lost during refresh. Please login again.", icon="⚠️")
        st.info("Stop doing page refresh for this system.", icon="ℹ️")
        if st.button("Goto Login page", icon="🔐"):
            st.switch_page(page_url.login_url)
        st.stop()

    try:
        payload = decrypt_data(sid)
    except Exception:
        st.error("Invalid session token.")
        st.stop()

    # Expiry check
    if payload.get("expiry", 0) < int(time.time()):
        st.error("Session expired.")
        st.stop()

    # Hydrate session_state
    st.session_state.update(payload)
    st.session_state.sid = sid
