# _Logout.py
import streamlit as st
from utils import page_url
from time import sleep
from streamlit_bridge import app_state
from db import db


# Authentication
app_state.restore_state_from_query_params()
app_state.sync_query_params_from_session()
app_state.check_authenticaiton_state()
username, role = app_state.get_current_user_info()
print("logging out", username)
db.end_session(username=username)

st.session_state.clear()
st.switch_page(page_url.login_url)
st.stop()