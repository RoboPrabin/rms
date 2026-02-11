# import streamlit as st
# import time
# from utils import auth_utils, page_url

# # 1. Clear Browser Cookies (Client-side)
# auth_utils.logout_logic_only()

# # # 2. Clear Session State (User-specific variables)
# # st.session_state.clear()

# # # 3. Clear Streamlit Cache (Server-side)
# # # This clears @st.cache_data and @st.cache_resource for THIS specific user session
# # st.cache_data.clear()
# # st.cache_resource.clear()

# # 4. Visual Feedback & Execution Gap
# st.info("Clearing cache and logging out safely...", icon="🧹")
# time.sleep(0.5) 
# st.switch_page(page_url.login_url)

# # 5. Hard Redirect
# # st.switch_page(page_url.login_url)



import streamlit as st
import streamlit.components.v1 as components
from utils import auth_utils

st.set_page_config(page_title="Logging out...", layout="centered")

# 1. Get the script
logout_js = auth_utils.logout_logic_only()

# 2. RENDER IT (This is what triggers the browser action)
components.html(logout_js, height=0, width=0)

# 3. Visual fallback in case JS is disabled or slow
st.info("Logging out and clearing secure cookies... Please wait.")
st.switch_page("LoginPage.py")
# Do NOT use st.stop() or st.switch_page here immediately.
# Let the page finish rendering so the component above actually loads.