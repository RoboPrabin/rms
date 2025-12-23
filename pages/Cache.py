# _Logout.py
import streamlit as st
from utils import page_url
from time import sleep
from streamlit_bridge import app_state
from db import db
from streamlit_bridge import app_state
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils import helper

helper.eliminate_top_padding()
# Authentication
app_state.restore_state_from_query_params()
app_state.sync_query_params_from_session()
app_state.check_authenticaiton_state()
username, role = app_state.get_current_user_info()
navigation.render_sidebar()
if st.button("Clear cache", icon="🗑️"):
    st.cache_data.clear()      # clears all st.cache_data
    st.cache_resource.clear()  # clears all st.cache_resource
    st.success("Cache cleared!")
    sleep(1)
    st.rerun()
