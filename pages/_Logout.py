# _Logout.py
import streamlit as st
from utils import page_url
# from app_state import logout_user
from time import sleep

st.session_state.clear()
st.switch_page("Login.py")
st.stop()