# _Logout.py
import streamlit as st
from utils import page_url
from time import sleep
from streamlit_bridge import app_state
from db import db
import time
from utils import helper


# Authentication
# app_state.restore_state_from_query_params()
# app_state.sync_query_params_from_session()
# app_state.check_authenticaiton_state()
app_state.sync_local_storage_to_session()
username, role, branch = app_state.get_current_user_info()
db.end_session(username=username)
helper.remove_token_from_local_storage()
sleep(0.5)
st.session_state.clear()
st.switch_page(page_url.login_url)
st.stop()