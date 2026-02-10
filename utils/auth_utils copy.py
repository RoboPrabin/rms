import time
import streamlit as st
import extra_streamlit_components as stx
from utils import page_url
from utils.security import decrypt_data
import streamlit.components.v1 as components
from streamlit.web.server.websocket_headers import _get_websocket_headers


def hide_sidebar():
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {
                display: none;
            }
            # [data-testid="collapsedControl"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)



def set_cookie_instantly(name, value, expiry_days=7):
    """Injects a cookie directly into the browser using JS."""
    js_code = f"""
        <script>
            let date = new Date();
            date.setTime(date.getTime() + ({expiry_days}*24*60*60*1000));
            let expires = "expires="+ date.toUTCString();
            document.cookie = "{name}={value};" + expires + ";path=/;SameSite=Lax";
            // No need to force rerun here if we are switching pages anyway
        </script>
    """
    # This renders the script in the app
    components.html(js_code, height=0)



def get_cookies_fast():
    """Reads cookies from HTTP headers."""
    headers = _get_websocket_headers()
    if not headers:
        return None
    
    cookie_header = headers.get("Cookie") or headers.get("cookie")
    if not cookie_header:
        return None
    
    # More robust parsing for multiple cookies
    cookies = {}
    for item in cookie_header.split(";"):
        if "=" in item:
            k, v = item.strip().split("=", 1)
            cookies[k] = v
            
    return cookies.get("auth_token")

def ensure_logged_in():
    now = int(time.time())

    # 1️⃣ Check Session State (If this exists, we don't need the cookie)
    if st.session_state.get("auth") and st.session_state.get("username"):
        if st.session_state.get("expiry", 0) <= now:
            st.session_state.clear() 
        else:
            return st.session_state

    # 2️⃣ Check Cookie (Fast Headers)
    token = get_cookies_fast()
    
    # 🚨 FIX: If token is None, wait a tiny bit and try ONE more time
    # This handles the race condition where headers aren't ready
    if not token:
        time.sleep(0.2) 
        token = get_cookies_fast()

    if not token:
        # Check if we are already on login page to avoid infinite loops
        st.switch_page(page_url.login_url)
        st.stop()

    try:
        payload = decrypt_data(token=token)
        
        # 3️⃣ Validate Integrity
        if not payload or not payload.get("username"):
            st.session_state.clear()
            st.switch_page(page_url.login_url)
            st.stop()

        # 4️⃣ Validate Expiry
        if payload["expiry"] <= now:
            st.error("Session expired.")
            st.stop()
        
        st.session_state.update(payload)
        return payload
    except Exception:
        st.switch_page(page_url.login_url)
        st.stop()




def logout_logic_only():
    """Wipes session and cookie without the full redirect."""
    st.session_state.clear()
    js_code = '<script>document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";</script>'
    components.html(js_code, height=0)





# def get_cookies_fast():
#     """Reads cookies instantly from HTTP headers (No lag)."""
#     headers = _get_websocket_headers()
#     if not headers or "Cookie" not in headers:
#         return None
    
#     cookie_str = headers["Cookie"]
#     cookies = dict(item.split("=", 1) for item in cookie_str.split("; ") if "=" in item)
#     return cookies.get("auth_token")



# def ensure_logged_in():
#     now = int(time.time())

#     # 1️⃣ VALIDATE SESSION STATE
#     # Add a check: if username is None, treat it as expired/invalid
#     if st.session_state.get("auth") and st.session_state.get("username"):
#         if st.session_state.get("expiry", 0) <= now:
#             st.session_state.clear() 
#         else:
#             return st.session_state

#     # 2️⃣ CHECK COOKIE
#     token = get_cookies_fast()
#     if not token:
#         print("TOKEN NOT FOUND", token)
#         st.switch_page(page_url.login_url)
#         st.stop()

#     try:
#         payload = decrypt_data(token=token)
        
#         # 3️⃣ VALIDATE DATA INTEGRITY
#         # If the cookie exists but the username is missing/None, it's a "Ghost Cookie"
#         if not payload or not payload.get("username"):
#             logout_logic_only()
#             st.session_state.clear()
#             st.switch_page(page_url.login_url)
#             st.stop()

#         # 4️⃣ CHECK EXPIRY
#         if payload["expiry"] <= now:
#             logout_logic_only()
#             st.error("Your session has expired.", icon="🚨")
#             if st.button("Go to Login Page", icon="🔐"):
#                 st.switch_page(page_url.login_url)
#             st.stop()
        
#         # 5️⃣ SUCCESS: Sync and Return
#         st.session_state.update(payload)
#         return payload

#     except Exception as e:
#         logout_logic_only()
#         st.session_state.clear()
#         st.switch_page(page_url.login_url)
#         st.stop()





def logout_and_redirect(login_url_path):
    """The most aggressive way to log out and move to login."""
    st.session_state.clear()
    js_code = f"""
        <script>
            document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            setTimeout(function(){{
                window.parent.location.assign(window.parent.location.origin + "/{login_url_path}");
            }}, 300);
        </script>
    """
    components.html(js_code, height=0)
    # st.switch_page(page_url.login_url)
    # st.stop()




















# def ensure_logged_in():
#     now = int(time.time())

#     # 1. VALIDATE SESSION STATE FIRST
#     # If session exists but is expired, clear it!
#     if st.session_state.get("auth"):
#         if st.session_state.get("expiry", 0) <= now:
#             st.session_state.clear() # Clear the expired session
#             # Don't return! Let the code fall through to the cookie check or login
#         else:
#             return st.session_state

#     # 2. CHECK COOKIE
#     token = get_cookies_fast()
#     if token:
#         user = decrypt_data(token=token)
#         if user['expiry']>now:
#             st.info("Expired session")
#             st.switch_page(page_url.login_url)
#             st.stop()
#         else:
#             st.switch_page(page_url.dashbord_url)
#         # If no cookie and no session, go to login
#         # print("hello worlding.")

#     try:
#         payload = decrypt_data(token)
        
#         # 3. VALIDATE COOKIE EXPIRY
#         if payload["expiry"] <= now:
#             # Token is in browser but is old
#             hide_sidebar()
#             st.error("Session expired. Please login again. FIRST TRY", icon="🚨")
#             if st.button("Go to Login Page", icon="🔐"):
#                 # Clean up the old cookie so it doesn't keep looping
#                 logout_logic_only() 
#                 st.switch_page(page_url.login_url)
        
#         # Restore state if valid
#         st.session_state.update(payload)
#         st.stop()
#         return payload
#     except Exception:
#         hide_sidebar()
#         st.error("Session expired. Please login again.", icon="🚨")
#         if st.button("Go to Login Page", icon="🔐"):
#             # Clean up the old cookie so it doesn't keep looping
#             logout_logic_only() 
#             st.switch_page(page_url.login_url)
#         st.stop()
#         return None


# def ensure_logged_in():
#     now = int(time.time())

#     # 1️⃣ VALIDATE SESSION STATE FIRST (Fastest)
#     if st.session_state.get("auth"):
#         if st.session_state.get("expiry", 0) <= now:
#             st.session_state.clear() 
#         else:
#             return st.session_state # Still valid, keep going

#     # 2️⃣ CHECK COOKIE
#     token = get_cookies_fast()
    
#     if not token:
#         st.switch_page(page_url.login_url)
#         st.stop()

#     try:
#         payload = decrypt_data(token=token)
        
#         # 3️⃣ CHECK EXPIRY
#         if payload["expiry"] <= now:
#             # TOKEN EXPIRED
#             hide_sidebar()
#             logout_logic_only() # Clear the bad cookie
#             st.error("Your session has expired. Please log in again.", icon="🚨")
#             if st.button("Go to Login Page", icon="🔐"):
#                 st.switch_page(page_url.login_url)
#             st.stop()
#         else:
#             # TOKEN VALID -> Sync to Session State
#             st.session_state.update(payload)
#             # Optional: if you are on the login page, redirect to dashboard
#             # But usually, this function is called at the top of dashboard pages.
#             print("Else part", payload)
#             return payload

#     except Exception as e:
#         logout_logic_only()
#         st.session_state.clear()
#         st.switch_page(page_url.login_url)
#         st.stop()
    














































# def ensure_logged_in():
#     # 1. Check Session State (Instant)
#     if st.session_state.get("auth"):
#         return st.session_state

#     # 2. Check Headers (Instant - No component lag!)
#     headers = _get_websocket_headers()
#     cookie_str = headers.get("Cookie", "")
    
#     # Simple extraction logic
#     token = None
#     if "auth_token=" in cookie_str:
#         token = cookie_str.split("auth_token=")[1].split(";")[0]

#     if token:
#         payload = decrypt_data(token)
#         # Update session state...
#         return payload
    
#     # 3. If no token, redirect
#     st.switch_page("login.py")

# def ensure_logged_in():
#     now = int(time.time())

#     # 1️⃣ Already authenticated & not expired
#     if (
#         st.session_state.get("auth")
#         and st.session_state.get("expiry", 0) > now
#     ):
#         print("Already auth", st.session_state.get('username'))
#         return {
#             "username": st.session_state.username,
#             "role": st.session_state.role,
#             "branch": st.session_state.branch,
#             "expiry": st.session_state.expiry,
#             "auth": st.session_state.auth
#         }

#     # 2️⃣ Check cookie
#     controller = stx.CookieManager()
#     # Give it a split second to sync with the browser
#     if "auth_token" not in st.session_state:
#         time.sleep(0.2) # Small buffer
#         token = controller.get("auth_token")
#         # token = controller.get("auth_token")

#     if not token:
#         redirect_to_login()
#         st.stop()

#     payload = decrypt_data(token)

#     # 3️⃣ Expired token
#     if payload["expiry"] <= now:
#         controller.delete("auth_token")
#         st.session_state.clear()
#         redirect_to_login()
#         st.stop()

#     # 4️⃣ Restore session
#     st.session_state.auth = True
#     st.session_state.username = payload["username"]
#     st.session_state.role = payload["role"]
#     st.session_state.branch = payload["branch"]
#     st.session_state.expiry = payload["expiry"]
#     print("auth_utils",payload)
#     return payload



# def ensure_logged_in():
#     now = int(time.time())

#     # 1️⃣ SHORT-CIRCUIT: Use Session State if it exists and is valid
#     # This prevents unnecessary cookie lookups and decryption
#     if (
#         st.session_state.get("auth") is True 
#         and st.session_state.get("username") is not None
#         and st.session_state.get("expiry", 0) > now
#     ):
#         print("Inside session", st.session_state.get('username'))
#         return {
#             "username": st.session_state.username,
#             "role": st.session_state.role,
#             "branch": st.session_state.branch,
#             "expiry": st.session_state.expiry,
#             "auth": st.session_state.auth
#         }

#     # 2️⃣ FALLBACK: Only check Cookie if Session State is empty or expired
#     controller = stx.CookieManager()
    
#     # stx.CookieManager can be slow to initialize; we check for token
#     token = controller.get("auth_token")
#     print("Token", token)
#     time.sleep(0.2) 

#     # If the component hasn't loaded the cookie yet, force a rerun to try again
#     if token is None:
#         st.switch_page(page_url.login_url)
#         # time.sleep(0.2) 
#         # st.rerun()

#     payload = decrypt_data(token)

#     # 3️⃣ Validate Decrypted Payload
#     if not payload or payload.get("expiry", 0) <= now:
#         controller.delete("auth_token")
#         st.session_state.clear()
#         redirect_to_login()
#         st.stop()

#     # 4️⃣ RESTORE SESSION: Save to state so Step 1 works on next rerun
#     st.session_state.auth = True
#     st.session_state.username = payload["username"]
#     st.session_state.role = payload["role"]
#     st.session_state.branch = payload["branch"]
#     st.session_state.expiry = payload["expiry"]
#     print("Loaded payload", payload)
#     return payload



# def redirect_to_login():
#     st.error("Session expired.", icon="🚨")
#     if st.button("Go to Login Page", icon="🔐"):
#         st.switch_page(page_url.login_url)


# def redirect_to_dashboard():
#     st.switch_page(page_url.dashbord_url)


