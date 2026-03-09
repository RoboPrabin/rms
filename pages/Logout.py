import time
import streamlit as st
import streamlit.components.v1 as components
from utils import auth_utils,page_url

auth_utils.hide_sidebar()
st.set_page_config(page_title="Logging out...", layout="centered")
st.query_params.clear()
st.session_state.clear()
# del st.session_state
st.switch_page(page_url.login_url)
# st.stop()