# _Logout.py
import streamlit as st
from utils import page_url
from time import sleep
from streamlit_bridge import app_state
from db import db

username, role = app_state.get_current_user_info()
db.end_session(username=username)
st.session_state.clear()
st.switch_page(page_url.login_url)
st.stop()