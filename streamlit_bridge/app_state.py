
from db import db
import json
from utils.security import decrypt_data
from streamlit_js_eval import streamlit_js_eval
from utils import page_url
import streamlit as st
import time
from utils.security import decrypt_data, encrypt_data
from utils import helper
import extra_streamlit_components as stx



# def get_cookie_manager():
#     """
#     Returns the CookieManager instance stored in session state.
#     This avoids the CachedWidgetWarning and Duplicate Key error.
#     """
#     if "cookie_manager" not in st.session_state:
#         # Create it only once and store it
#         st.session_state.cookie_manager = stx.CookieManager(key="trishakti_auth_manager")
#     return st.session_state.cookie_manager

# def ensure_authentication():
#     """
#     Centralized Security Guard for all 30+ pages.
#     """
#     # 1. FAST TRACK: Session is already live
#     if st.session_state.get("authenticated") and st.session_state.get("username"):
#         return {
#             "username": st.session_state.username,
#             "role": st.session_state.role,
#             "branch": st.session_state.branch
#         }

#     # 2. RECOVERY TRACK: Session lost, check Cookies
#     cookie_manager = get_cookie_manager()
    
#     # Give the browser a split second to send cookie data to the component
#     token = cookie_manager.get("auth_token")
#     if token is None:
#         time.sleep(0.1)
#         token = cookie_manager.get("auth_token")

#     if token:
#         try:
#             payload = decrypt_data(token)
#             if payload and payload.get('auth'):
#                 current_time = int(time.time())
#                 expiry_time = payload.get('expiry', 0)
                
#                 if current_time < expiry_time:
#                     # Restore Session State
#                     st.session_state.authenticated = True
#                     st.session_state.username = payload.get("user")
#                     st.session_state.role = payload.get("role")
#                     st.session_state.branch = payload.get("branch")
#                     st.session_state.expiry = expiry_time
                    
#                     return {
#                         "username": st.session_state.username,
#                         "role": st.session_state.role,
#                         "branch": st.session_state.branch
#                     }
#         except Exception:
#             pass

#     # 3. FAIL TRACK: No valid session or cookie
#     st.info("Please login to access this page.")
#     st.switch_page("LoginPage.py") # Make sure this filename is exact
#     st.stop()





# def get_cookie_manager():
#     """Returns the singleton CookieManager instance."""
#     if "cookie_manager" not in st.session_state:
#         st.session_state.cookie_manager = stx.CookieManager(key="trishakti_auth_manager")
#     return st.session_state.cookie_manager

# def ensure_authentication():
#     # 1. FAST TRACK: Session is live (Normal navigation)
#     if st.session_state.get("authenticated") and st.session_state.get("username"):
#         return {
#             "username": st.session_state.username,
#             "role": st.session_state.role,
#             "branch": st.session_state.branch
#         }

#     # 2. RECOVERY TRACK: Page Refreshed, session state is empty
#     cookie_manager = get_cookie_manager()
#     token = cookie_manager.get("auth_token")

#     # 3. THE HANDSHAKE FIX:
#     # If token is None, it might be because the component is still 'warming up'
#     if token is None:
#         if "auth_retry_count" not in st.session_state:
#             st.session_state.auth_retry_count = 1
#             time.sleep(0.2) # Small buffer for the component
#             st.rerun() # Force one rerun to capture the browser cookie
#         else:
#             # If we already retried and still have no token, then the user is truly logged out
#             del st.session_state.auth_retry_count
#             st.info("Session expired. Please login.")
#             st.switch_page("LoginPage.py")
#             st.stop()

#     # 4. VALIDATION (If we found a token)
#     if token:
#         # Clear the retry count since we succeeded
#         if "auth_retry_count" in st.session_state:
#             del st.session_state.auth_retry_count
            
#         try:
#             payload = decrypt_data(token)
#             if payload and payload.get('auth'):
#                 # Re-hydrate the session state
#                 st.session_state.authenticated = True
#                 st.session_state.username = payload.get("user")
#                 st.session_state.role = payload.get("role")
#                 st.session_state.branch = payload.get("branch")
#                 st.session_state.expiry = payload.get("expiry")
                
#                 return {
#                     "username": st.session_state.username,
#                     "role": st.session_state.role,
#                     "branch": st.session_state.branch
#                 }
#         except Exception:
#             pass

#     # Final fallback
#     st.switch_page("LoginPage.py")
#     st.stop()




def get_cookie_manager():
    """
    The only way to avoid Duplicate Key AND survive refresh is to 
    initialize it inside the function but ensure it only runs once 
    per script execution.
    """
    # We use st.empty() or a simple check to see if we've rendered it 
    # IN THIS SPECIFIC RUN. 
    # We don't store the OBJECT in session_state, we just flag that it's been called.
    
    return stx.CookieManager(key="trishakti_auth_manager")

def ensure_authentication():
    # 1. FAST TRACK: Session state is the only thing that works instantly
    if st.session_state.get("authenticated") and st.session_state.get("username"):
        return {
            "username": st.session_state.username,
            "role": st.session_state.role,
            "branch": st.session_state.branch
        }

    # 2. RECOVERY TRACK: (This runs ONLY on Refresh or first load)
    # We initialize it here. 
    cookie_manager = get_cookie_manager()
    
    # Handshake delay - REQUIRED for Refresh
    token = cookie_manager.get("auth_token")
    if token is None:
        time.sleep(0.6)
        token = cookie_manager.get("auth_token")

    if token:
        try:
            payload = decrypt_data(token)
            if payload and payload.get('auth'):
                # Re-hydrate
                st.session_state.authenticated = True
                st.session_state.username = payload.get("user")
                st.session_state.role = payload.get("role")
                st.session_state.branch = payload.get("branch")
                return payload
        except Exception:
            pass

    # 3. FAIL TRACK
    st.switch_page("LoginPage.py")
    st.stop()

































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



# def restore_state_from_query_params():
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


# def check_authenticaiton_state():
#     # Gate: only allow if authenticated
#     if not st.session_state.get("authenticated", False):
#         st.warning("Please log in via the Login page to access the dashboard.")
#         if st.button("Go to Login Page"):
#             st.info("Redirecting to Login page...")
#             st.switch_page(page_url.login_url)
#         st.stop()

# def sync_query_params_from_session():
#     if st.session_state.get("authenticated") and "sid" not in st.query_params:
#         payload = {
#             "auth": True,
#             "user": st.session_state.username,
#             "role": st.session_state.role,
#             "branch":st.session_state.branch
#         }
#         st.query_params["sid"] = encrypt_data(payload)

# def get_current_user_info():    
#     username = st.session_state.get("username", "...")
#     role = st.session_state.get("role", "...")
#     branch = st.session_state.get("branch", "...")
#     return username, role, branch

# def check_authentication_state_login_page():
#     # If already authenticated, redirect to Dashboard
#     if st.session_state.get("authenticated", False):
#         st.success("Already logged in, redirecting...")
#         time.sleep(0.3)
#         st.switch_page(page_url.dashbord_url)



