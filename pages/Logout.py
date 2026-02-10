import streamlit as st
import time
from utils import auth_utils, page_url

# 1. Clear Browser Cookies (Client-side)
auth_utils.logout_logic_only()

# 2. Clear Session State (User-specific variables)
st.session_state.clear()

# 3. Clear Streamlit Cache (Server-side)
# This clears @st.cache_data and @st.cache_resource for THIS specific user session
st.cache_data.clear()
st.cache_resource.clear()

# 4. Visual Feedback & Execution Gap
st.info("Clearing cache and logging out safely...", icon="🧹")
time.sleep(0.5) 

# 5. Hard Redirect
st.switch_page(page_url.login_url)