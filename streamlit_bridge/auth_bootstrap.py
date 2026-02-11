import time
import streamlit as st
from utils import page_url
from utils.security import decrypt_data



# def bootstrap_session():
#     if st.session_state.get("expiry"):
#         remaining = st.session_state.expiry - int(time.time())
#         if remaining > 0:
#             st.sidebar.write(f"Session ends in: {remaining}s")
#         else:
#             st.query_params.clear() 
#             st.error("Session expired. Please login again for security.", icon="⏰")
#             if st.button("Back to Login", icon="🔐"):
#                 st.switch_page(page_url.login_url)
#             return
    
#     # 1. Skip if already authenticated in this rerun
#     if st.session_state.get("auth"):
#         return

#     # 2. Get sid from query params
#     sid = st.query_params.get("sid")

#     if not sid:
#         st.warning("Session lost. Please login again.", icon="⚠️")
#         if st.button("Goto Login page", icon="🔐"):
#             st.switch_page(page_url.login_url) # Ensure this path is correct
#         st.stop()

#     try:
#         # Decrypt the payload
#         payload = decrypt_data(sid)
        
#         # --- EXPIRY CHECK LOGIC ---
#         current_time = int(time.time())
#         expiry_time = payload.get("expiry", 0)

#         if expiry_time < current_time:
#             # Clear query params so they don't get stuck in a loop
#             st.query_params.clear() 
#             st.error("Session expired. Please login again for security.", icon="⏰")
#             if st.button("Back to Login", icon="🔐"):
#                 st.switch_page(page_url.login_url)
#             st.stop()
#         # ---------------------------

#         # If not expired, hydrate session_state
#         st.session_state.update(payload)
#         st.session_state.sid = sid

#     except Exception as e:
#         st.error(f"Invalid or corrupted session token.")
#         st.stop()




import time
import streamlit as st

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

    # 5. Success - ensure sid stays in URL for the next refresh
    if "sid" not in st.query_params:
        st.query_params["sid"] = sid