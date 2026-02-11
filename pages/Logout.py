import time
import streamlit as st
import streamlit.components.v1 as components
from utils import auth_utils,page_url

auth_utils.hide_sidebar()
st.set_page_config(page_title="Logging out...", layout="centered")

# logout_js = auth_utils.logout_logic_only()

# components.html(logout_js, height=0, width=0)

st.info("Logging out and clearing secure cookies... Please wait.", icon="ℹ️")
time.sleep(0.3)
st.session_state.clear()
st.switch_page(page_url.login_url)

st.stop()