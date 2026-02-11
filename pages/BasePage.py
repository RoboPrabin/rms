import streamlit as st
from streamlit_bridge.auth_bootstrap import bootstrap_session


class BasePage:

    def __init__(self):
        bootstrap_session()
        self.username = st.session_state.get("username")
        self.role = st.session_state.get("role")
        self.branch = st.session_state.get("branch")
        self.sid = st.session_state.get("sid")
        self.validate_user_context()

    def validate_user_context(self):
        if not self.username or not self.role:
            st.error("Invalid session context.")
            st.stop()
