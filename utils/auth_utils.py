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
        if st.session_state.get("expiry", 0) > now:
            return st.session_state

    # 2️⃣ Then check cookie
    token = cookies.get("auth_token")

    if not token:
        clear_session_and_redirect()

    # 3️⃣ Decode payload
    try:
        payload = decrypt_data(token)
        if not payload or payload.get("expiry", 0) <= now:
            clear_session_and_redirect()

        st.session_state.update(payload)
        st.session_state["auth"] = True
        return payload

    except:
        clear_session_and_redirect()


def clear_session_and_redirect():
    for key in list(st.session_state.keys()):
        if key != "cookies_initialized":
            del st.session_state[key]
    logout_logic_only()
    st.switch_page(page_url.login_url)
    st.stop()



# -------------------------------------------------------------------
# LOGIN SUCCESS HANDLER
# -------------------------------------------------------------------

def set_login_session(token: str, payload: dict):
    cookies["auth_token"] = token
    cookies.save()
    st.session_state.update(payload)
    st.session_state["auth"] = True


def logout_logic_only():
    for key in list(st.session_state.keys()):
        if key != "cookies_initialized":
            del st.session_state[key]

    return f"""
        <script>
            function deleteCookie(name) {{
                document.cookie = name + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            }}
            deleteCookie("rms_auth_token");
            deleteCookie("rms_EncryptedCookieManager.key_params");
            // Navigate to login page and replace history
            window.location.replace("{page_url.login_url}");
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
            window.location.replace("{page_url.login_url}");
        </script>
    """
    components.html(logout_js, height=0, width=0)