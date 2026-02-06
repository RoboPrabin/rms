# _Logout.py
import streamlit as st
from utils import auth_utils, page_url
from time import sleep
from streamlit_bridge import app_state
from db import db
from streamlit_bridge import app_state
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils import helper

# helper.eliminate_top_padding()
st.session_state.active_menu = "utility"
user = auth_utils.ensure_logged_in()
username= user['username']
role= user['role']
branch = user['branch']
navigation.render_sidebar()
if st.button("Clear cache", icon="🗑️"):
    st.cache_data.clear()      # clears all st.cache_data
    st.cache_resource.clear()  # clears all st.cache_resource
    st.success("Cache cleared!")
    sleep(1)
    st.rerun()
