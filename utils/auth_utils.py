import time
import streamlit as st
from utils import page_url
from utils.security import decrypt_data
import streamlit.components.v1 as components

def hide_sidebar():
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] { display: none; }
            [data-testid="collapsedControl"] { display: none; }
        </style>
    """, unsafe_allow_html=True)

def set_cookie_instantly(name, value, expiry_days=7):
    """Injects a cookie directly into the browser using JS."""
    # Added SameSite=Lax for better browser compatibility on refreshes
    js_code = f"""
        <script>
            let date = new Date();
            date.setTime(date.getTime() + ({expiry_days}*24*60*60*1000));
            let expires = "expires="+ date.toUTCString();
            document.cookie = "{name}={value};" + expires + ";path=/;SameSite=Lax";
        </script>
    """
    components.html(js_code, height=0)
def ensure_logged_in():
    now = int(time.time())

    # 1. ALWAYS prioritize Session State. 
    # If the user just logged in, the login page should have set this.
    if st.session_state.get("auth") == True and st.session_state.get("username"):
        if st.session_state.get("expiry", 0) > now:
            return st.session_state
    
    # 2. If Session State is empty (e.g. after a Refresh), check Cookies
    # Give the browser a tiny moment to send headers if they are missing
    token = st.context.cookies.get("auth_token")
    
    if not token:
        time.sleep(0.3) # Wait for headers to stabilize on VM
        token = st.context.cookies.get("auth_token")

    if not token:
        st.switch_page(page_url.login_url)
        st.stop()

    try:
        payload = decrypt_data(token=token)
        if not payload or payload.get("expiry", 0) <= now:
            st.session_state.clear()
            st.switch_page(page_url.login_url)
            st.stop()

        # Re-populate session state so we don't hit this block again
        st.session_state.update(payload)
        st.session_state["auth"] = True
        return payload
    except:
        st.switch_page(page_url.login_url)
        st.stop()

def logout_logic_only():
    """Wipes session and cookie."""
    st.session_state.clear()
    # Explicitly clear cookie with path and SameSite for consistency
    js_code = """
        <script>
            document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; SameSite=Lax";
        </script>
    """
    components.html(js_code, height=0)