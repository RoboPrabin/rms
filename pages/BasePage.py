import streamlit as st
from streamlit_bridge.auth_bootstrap import bootstrap_session
from utils.security import decrypt_data

class BasePage:

    def __init__(self):
        if "sid" in st.session_state and "sid" not in st.query_params:
            st.query_params["sid"] = st.session_state.sid
        # try:
        #     print("BasePage", st.query_params['sid'])
        #     payload = decrypt_data(st.query_params['sid'])
        #     print("\n\n")
        #     print("payload", payload)
        # except Exception:
        #     pass
        bootstrap_session()
        self.username = st.session_state.get("username")
        self.role = st.session_state.get("role")
        self.branch = st.session_state.get("branch")
        self.sid = st.session_state.get("sid")
        self.id = st.session_state.get("id")
        self.validate_user_context()

    def validate_user_context(self):
        if not self.username or not self.role:
            st.error("Invalid session context.")
            st.stop()
