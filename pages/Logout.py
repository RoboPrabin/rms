import time
from db import db
import streamlit as st
from utils import page_url
from time import sleep
import extra_streamlit_components as stx
from utils import auth_utils
from utils.security import decrypt_data

auth_utils.logout_logic_only()
st.stop()








# import streamlit as st
# from utils import page_url
# from streamlit_bridge import app_state
# from db import db
# import time
# import extra_streamlit_components as stx

# # 1. Use the SAME key used in the rest of the app
# # This ensures we are looking at the right cookie "bucket"
# controller = stx.CookieManager(key="trishakti_auth_manager")

# st.info("Logging out. Please wait ...", icon="ℹ️")
# # Give it a tiny bit of time to sync so controller.cookies is populated
# time.sleep(0.3)

# try:
#     # Try to get user from session state or cookie before we wipe everything
#     username = st.session_state.get('username')
#     if username:
#         db.end_session(username=username)
# except Exception:
#     pass

# # 2. Safety Check: Only delete if the key actually exists in the controller's internal dict
# # This prevents the KeyError: 'auth_token'
# if "auth_token" in controller.cookies:
#     controller.delete("auth_token")
# else:
#     try:
#         controller = stx.CookieManager()
#         controller.delete("auth_token")
#         time.sleep(0.2)
#     except Exception:
#         pass
# st.session_state.clear()
# st.switch_page(page_url.login_url)