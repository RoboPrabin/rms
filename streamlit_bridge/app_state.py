
from db import db
import json
from utils.security import decrypt_data
from streamlit_js_eval import streamlit_js_eval
from utils import page_url
import streamlit as st
import time
from utils.security import decrypt_data, encrypt_data
from utils import helper

def sync_local_storage_to_session():
    """
    Call this ONLY at the very top of your main entry point or in your 
    initialization logic.
    """
    # If we already have the token in session, don't trigger the JS widget again
    if "token" not in st.session_state:
        try:
            token = streamlit_js_eval(
                js_expressions="localStorage.getItem('token')", 
                key="get_auth_token_static"
            )
            if token and token != "undefined":
                st.session_state["token"] = token
                try:
                    # Decrypt once and store everything in session_state
                    payload = decrypt_data(token)
                    st.session_state.authenticated = True
                    st.session_state.username = payload.get("user")
                    st.session_state.role = payload.get("role")
                    st.session_state.branch = payload.get("branch")
                except Exception as e:
                    print(f"Initial sync decryption failed: {e}")
        except Exception as e:
            pass




def enforce_authentication():
    # 1. If not authenticated, check browser storage
    if not st.session_state.get("authenticated", False):
        token_from_browser = streamlit_js_eval(
            js_expressions="localStorage.getItem('token')", 
            key="recovery_token_check"
        )

        # 2. THE CRITICAL WAIT: Give the JS component a moment to respond
        # This prevents the 'flicker' by pausing the script for a split second
        if token_from_browser is None:
            with st.spinner("Authenticating..."):
                time.sleep(0.5) 
                # This pause allows the JS to return data and trigger a rerun 
                # before we ever reach the "Please Login" warning below.
            st.stop() 

        # 3. If we got the token, validate and set state
        if token_from_browser and token_from_browser != "undefined":
            try:
                payload = decrypt_data(token_from_browser)
                if int(time.time()) < payload.get("expiry", 0):
                    st.session_state.token = token_from_browser
                    st.session_state.authenticated = True
                    st.session_state.username = payload.get("user")
                    st.session_state.role = payload.get("role")
                    st.session_state.branch = payload.get("branch")
                    st.session_state.expiry = payload.get("expiry")
                    st.rerun() 
                else:
                    show_expiry_screen()
                    st.stop()
            except Exception as e:
                print(f"Recovery failed: {e}")

    # 4. ONLY show the warning if we have waited and still aren't authenticated
    if not st.session_state.get("authenticated", False):
        st.warning("Please log in to access this page.")
        if st.button("Go to Login"):
            
            st.switch_page(page_url.login_url)
        st.stop() 

    # 5. Continuous Expiry Check
    if int(time.time()) > st.session_state.get("expiry", 0):
        show_expiry_screen()
        st.stop()



def show_expiry_screen():
    helper.eliminate_top_margin()
    st.error("🚨 Session Expired")
    
    # Capture the username BEFORE clearing the state
    username = st.session_state.get("username")

    if st.button("Return to Login Page", icon="🔐"):
        # 1. End database session using the username we already have in memory
        if username:
            try:
                db.end_session(username=username.upper())
            except Exception as e:
                print(f"DB End Session failed: {e}")

        # 2. Clear Python memory
        st.session_state.clear()
        streamlit_js_eval(
            js_expressions=f"""
                localStorage.removeItem('token');
            """,
            key="logout_and_redirect"
        )
        time.sleep(0.5)
        # Backup for Streamlit routing
        st.switch_page(page_url.login_url)



def restore_state_from_query_params():
    params = st.query_params
    # helper.show_message("Restoring state from query params:" + str(params))
    if "sid" not in params:
        return

    try:
        payload = decrypt_data(params["sid"])
        if payload.get("auth") is True:
            st.session_state.authenticated = True
            st.session_state.username = payload.get("user", "Guest")
            st.session_state.role = payload.get("role", "User")
            st.session_state.branch = payload.get("branch", "None")

    except Exception as e:
        print("SID decryption failed:", e)
        st.session_state.authenticated = False


# def restore_state_from_query_params_test():
#     params = st.query_params
#     # helper.show_message("Restoring state from query params:" + str(params))
#     if "sid" not in params:
#         return

#     try:
#         payload = decrypt_data(params["sid"])

#         if payload.get("auth") is True:
#             st.session_state.authenticated = True
#             st.session_state.username = payload.get("user", "Guest")
#             st.session_state.role = payload.get("role", "User")
#             st.session_state.branch = payload.get("branch", "None")


#     except Exception as e:
#         print("SID decryption failed:", e)
#         st.session_state.authenticated = False


def check_authenticaiton_state():
    # Gate: only allow if authenticated
    if not st.session_state.get("authenticated", False):
        st.warning("Please log in via the Login page to access the dashboard.")
        if st.button("Go to Login Page"):
            st.info("Redirecting to Login page...")
            st.switch_page(page_url.login_url)
        st.stop()

# def sync_query_params_from_session():
#     if st.session_state.get("authenticated") and "sid" not in st.query_params:
#         payload = {
#             "auth": True,
#             "user": st.session_state.username,
#             "role": st.session_state.role,
#             "branch":st.session_state.branch
#         }
#         st.query_params["sid"] = encrypt_data(payload)

def get_current_user_info():    
    username = st.session_state.get("username", "...")
    role = st.session_state.get("role", "...")
    branch = st.session_state.get("branch", "...")
    return username, role, branch

def check_authentication_state_login_page():
    # If already authenticated, redirect to Dashboard
    if st.session_state.get("authenticated", False):
        st.success("Already logged in, redirecting...")
        time.sleep(0.3)
        st.switch_page(page_url.dashbord_url)



