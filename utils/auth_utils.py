import time
import streamlit as st
from utils import page_url
from utils.security import decrypt_data
from streamlit_cookies_manager import EncryptedCookieManager


# -------------------------------------------------------------------
# Cookie Manager (initialize once per script run)
# -------------------------------------------------------------------
cookies = EncryptedCookieManager(
    prefix="rms_",                 # avoid collision
    password="SUPER_SECRET_KEY"  # use env variable in production
)
if not cookies.ready():
    st.stop()

# def get_cookie_manager():
#     return cookies


# -------------------------------------------------------------------
# UI Utilities
# -------------------------------------------------------------------

def hide_sidebar():
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] { display: none; }
            [data-testid="collapsedControl"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------------
# AUTH CORE
# -------------------------------------------------------------------
def ensure_logged_in():
    now = int(time.time())

    # 1️⃣ Session state first
    if st.session_state.get("auth") and st.session_state.get("username"):
        print("\n\n")
        print("======Session exists", st.session_state)
        if st.session_state.get("expiry", 0) > now:
            print("&&&&&& ohhkay")
            return st.session_state

    # 2️⃣ Then check cookie
    token = cookies.get("auth_token")

    if not token:
        st.session_state.clear()
        st.switch_page(page_url.login_url)
        st.stop()

    # 3️⃣ Decode payload
    try:
        payload = decrypt_data(token)
        if not payload or payload.get("expiry", 0) <= now:
            st.session_state.clear()
            st.switch_page(page_url.login_url)
            st.stop()

        # Update session state for next page loads
        st.session_state.update(payload)
        st.session_state["auth"] = True
        return payload

    except:
        st.session_state.clear()
        st.switch_page(page_url.login_url)
        st.stop()



# -------------------------------------------------------------------
# LOGIN SUCCESS HANDLER
# -------------------------------------------------------------------

def set_login_session(token: str, payload: dict):
    """
    Call this after successful login.
    """
    print("Inside set login session")
    print(cookies)
    # Store in cookie
    cookies["auth_token"] = token
    cookies.save()

    # Store in session
    st.session_state.update(payload)
    st.session_state["auth"] = True
    print("Completed")
    # Force clean rerun so session is stable
    # st.rerun()


# -------------------------------------------------------------------
# LOGOUT
# -------------------------------------------------------------------

# def logout_logic_only():
#     if "auth_token" in cookies:
#         cookies["auth_token"] = ''
#         # del cookies["auth_token"]
#         cookies.save()

#     st.session_state.clear()

#     st.switch_page(page_url.login_url)
#     # st.stop()




import streamlit as st
import streamlit.components.v1 as components

def logout_logic_only():
    # 1. Clear Session State
    st.session_state.clear()

    # 2. JavaScript "Clear and Redirect"
    # We target the specific keys you found remaining in the browser.
    # We use window.parent.location.assign because Streamlit runs in an iframe.
    js_redirect = f"""
        <script>
            function deleteCookie(name) {{
                document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            }}

            // Delete the specific keys you identified
            deleteCookie("rms_auth_token");
            deleteCookie("rms_EncryptedCookieManager.key_params");

            // Redirect the parent window to the login page
            window.parent.location.href = "http://localhost:8501";
        </script>
    """
    components.html(js_redirect, height=0)
    
    # 3. Stop Streamlit execution to let the JS take over
    st.stop()


def logout_logic_only():
    # Clear session state immediately
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Return the JS code
    return f"""
        <script>
            function deleteCookie(name) {{
                document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            }}
            deleteCookie("rms_auth_token");
            deleteCookie("rms_EncryptedCookieManager.key_params");

            // Use replace so the user can't hit 'back' to the authenticated page
        </script>
    """

# import streamlit.components.v1 as components

# def logout_logic_only():
#     # 1. Attempt standard library deletion
#     if "auth_token" in cookies:
#         del cookies["auth_token"]
#         cookies.save()

#     # 2. Clear Session State
#     st.session_state.clear()

#     # 3. THE FIX: JavaScript "Nuclear" Clear
#     # This force-expires the cookies directly in the browser
#     components.html(
#         """
#         <script>
#             // Delete the main token
#             document.cookie = "rms_auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
#             // Delete the manager metadata
#             document.cookie = "rms_EncryptedCookieManager.key_params=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
            
#             // Optional: Reload to ensure state is wiped
#             window.parent.location.reload();
#         </script>
#         """,
#         height=0
#     )
#     st.stop() # Stop execution to let the JS run






















# import time
# import streamlit as st
# from utils import page_url
# from utils.security import decrypt_data
# import streamlit.components.v1 as components

# def hide_sidebar():
#     st.markdown("""
#         <style>
#             section[data-testid="stSidebar"] { display: none; }
#             [data-testid="collapsedControl"] { display: none; }
#         </style>
#     """, unsafe_allow_html=True)

# def set_cookie_instantly(name, value, expiry_days=7):
#     """Injects a cookie directly into the browser using JS."""
#     # Added SameSite=Lax for better browser compatibility on refreshes
#     # js_code = f"""
#     #     <script>
#     #         let date = new Date();
#     #         date.setTime(date.getTime() + ({expiry_days}*24*60*60*1000));
#     #         let expires = "expires="+ date.toUTCString();
#     #         document.cookie = "{name}={value};" + expires + ";path=/;SameSite=Lax";
#     #     </script>
#     # """
#     js_code = f"""
#         <script>
#             let date = new Date();
#             date.setTime(date.getTime() + ({expiry_days}*24*60*60*1000));
#             let expires = "expires="+ date.toUTCString();
#             document.cookie = "{name}={value};" + expires + ";path=/;SameSite=Lax;Secure";
#         </script>
#         """
#     components.html(js_code, height=0)

    
# def ensure_logged_in():
#     now = int(time.time())

#     # 1. ALWAYS prioritize Session State. 
#     # If the user just logged in, the login page should have set this.
#     if st.session_state.get("auth") == True and st.session_state.get("username"):
#         print("Session is present", st.session_state.auth, st.session_state.username)
#         if st.session_state.get("expiry", 0) > now:
#             return st.session_state
    
#     # 2. If Session State is empty (e.g. after a Refresh), check Cookies
#     # Give the browser a tiny moment to send headers if they are missing
#     token = st.context.cookies.get("auth_token")
    
#     if not token:
#         time.sleep(0.3) # Wait for headers to stabilize on VM
#         token = st.context.cookies.get("auth_token")

#     if not token:
#         # If cookie missing but session exists, trust session
#         if st.session_state.get("auth") and st.session_state.get("username"):
#             return st.session_state
        
#         st.switch_page(page_url.login_url)
#         st.stop()

#     try:
#         payload = decrypt_data(token=token)
#         if not payload or payload.get("expiry", 0) <= now:
#             st.session_state.clear()
#             st.switch_page(page_url.login_url)
#             st.stop()

#         # Re-populate session state so we don't hit this block again
#         st.session_state.update(payload)
#         st.session_state["auth"] = True
#         return payload
#     except:
#         st.switch_page(page_url.login_url)
#         st.stop()

# def logout_logic_only():
#     """Wipes session and cookie."""
#     st.session_state.clear()
#     # Explicitly clear cookie with path and SameSite for consistency
#     js_code = """
#         <script>
#             document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; SameSite=Lax";
#         </script>
#     """
#     components.html(js_code, height=0)