import random
import time
import streamlit as st
import streamlit.components.v1 as components
from utils import page_url
from utils.security import decrypt_data
from streamlit_cookies_manager import EncryptedCookieManager


# -------------------------------------------------------------------
# Cookie Manager (initialize once per script run)
# -------------------------------------------------------------------
cookies = EncryptedCookieManager(
    prefix="rms_",                
    password="SUPER_SECRET_KEY"  
)
if not cookies.ready():
    st.stop()

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

def session_expired_ui():
    st.error("Your session has expired. Please login again.", icon="🚨")
    if st.button("Goto Login Page", icon="😁", key=random.randint(100,1999)):
        st.switch_page(page_url.login_url)
        logout_js = logout_logic_only()
        components.html(logout_js, height=0, width=0)
        st.stop()

# -------------------------------------------------------------------
# AUTH CORE
# -------------------------------------------------------------------
def ensure_logged_in():
    now = int(time.time())

    # 1️⃣ Session state first
    if st.session_state.get("auth") and st.session_state.get("username"):
        # print("\n\n")
        # print("======Session exists", st.session_state)
        if st.session_state.get("expiry", 0) > now:
            # print("&&&&&& ohhkay")
            # session_expired_ui()

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
    # print("Inside set login session")
    # print(cookies)
    # Store in cookie
    cookies["auth_token"] = token
    cookies.save()

    # Store in session
    st.session_state.update(payload)
    st.session_state["auth"] = True
    # print("Completed")
    # Force clean rerun so session is stable
    # st.rerun()


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


def delete_token_from_cookies():
    logout_js = f"""
        <script>
            function deleteCookie(name) {{
                document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            }}
            deleteCookie("rms_auth_token");
            deleteCookie("rms_EncryptedCookieManager.key_params");

            // Use replace so the user can't hit 'back' to the authenticated page
        </script>
    """
    components.html(logout_js, height=0, width=0)