import time
import streamlit as st
from utils import page_url
from utils.security import decrypt_data

def bootstrap_session():
    # 1. Get SID from URL or State
    sid = st.query_params.get("sid") or st.session_state.get("sid")

    # # 2. EMERGENCY OVERRIDE: If we have NO sid, we must allow login
    # if not sid:
    #     st.warning("Session lost. Please login again.", icon="⚠️")
    #     if st.button("Goto Login page", icon="🔐", key="no_sid_btn"):
    #         st.switch_page(page_url.login_url)
    #     st.stop() # Stops execution here if no button is clicked

    # 3. Process the Token
    try:
        if not st.session_state.get("auth") or st.session_state.get("sid") != sid:
            payload = decrypt_data(sid)
            st.session_state.update(payload)
            st.session_state.sid = sid
    except Exception:

        # st.error("Invalid session.")
        # if st.button("Back to Login", key="err_btn"):
        st.switch_page(page_url.login_url)
        st.stop()

    # 4. EXPIRY CHECK (The problematic part)
    remaining = st.session_state.get("expiry", 0) - int(time.time())

    if remaining <= 0:
        # Clear everything so it doesn't loop
        st.query_params.clear()
        st.session_state.clear()
        
        st.error("Session expired.", icon="⏰")
        # We MUST use the return of the button to switch BEFORE the st.stop()
        if st.button("Back to Login", icon="🔐", key="exp_btn"):
            st.switch_page(page_url.login_url)
        
        # This is what causes the "WTF" moment: 
        # On click, Streamlit reruns the script. It needs to stop HERE 
        # but only if the button wasn't just clicked.
        st.stop()
    # else:
    #     st.switch_page(page_url.dashbord_url)

    # 5. Success - ensure sid stays in URL for the next refresh
    if "sid" not in st.query_params:
        st.query_params["sid"] = sid