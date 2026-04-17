import time
import streamlit as st
import streamlit.components.v1 as components
from utils import page_url


# -------------------------------------------------------------------
# STRICT ACCESS GUARD
# -------------------------------------------------------------------
def enforce_strict_access(required_role: str = "ADMIN"):
    """
    Centralized function to enforce strict role-based access control.
    
    Runs on EVERY page load and validates:
    - User has valid authenticated session
    - User has required role (default: ADMIN)
    - Session is not expired (if expiry exists in query params)
    
    If any validation fails:
    - Clears all session state
    - Deletes cookies via JavaScript
    - Replaces browser history (prevents back button)
    - Redirects to login page
    - Stops execution immediately
    
    Args:
        required_role: The role required to access the page (default: ADMIN)
    
    Usage:
        from utils.access_guard import enforce_strict_access
        
        # For admin-only pages:
        enforce_strict_access("ADMIN")
        
        # For pages requiring specific role:
        enforce_strict_access("MANAGER")
    """
    # Step 1: Check if user is authenticated in session
    if not st.session_state.get("authenticated"):
        _force_logout()
    
    # Step 2: Check if username exists
    if not st.session_state.get("username"):
        _force_logout()
    
    # Step 3: Check if user has required role
    role = str(st.session_state.get("role", "")).upper().strip()
    required_role_upper = str(required_role).upper().strip()
    
    if role != required_role_upper:
        _force_logout()
    
    # Step 4: Validate session from query params if exists
    sid = st.query_params.get("sid")
    if sid:
        try:
            from utils.security import decrypt_data
            payload = decrypt_data(sid)
            if payload:
                # Update session state with valid payload
                st.session_state.update(payload)
                # Check expiry if present
                if "expiry" in payload:
                    if payload.get("expiry", 0) <= int(time.time()):
                        _force_logout()
        except Exception:
            # If decryption fails, check if session is valid another way
            pass
    
    return True


def _force_logout():
    """
    Internal function to force logout - clears everything and redirects.
    """
    # Clear all session state (iterate over copy of keys)
    keys_to_delete = list(st.session_state.keys())
    for key in keys_to_delete:
        if key != "cookies_initialized":
            if key in st.session_state:
                del st.session_state[key]
    
    # Clear query params
    st.query_params.clear()
    
    # JavaScript to delete cookies and replace history
    logout_js = f"""
    <script>
        (function() {{
            // Delete all cookies with rms_ prefix
            var cookies = document.cookie.split(";");
            for (var i = 0; i < cookies.length; i++) {{
                var cookie = cookies[i].trim();
                var eqPos = cookie.indexOf("=");
                var name = eqPos > -1 ? cookie.substr(0, eqPos) : cookie;
                if (name.indexOf("rms_") === 0) {{
                    document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/";
                }}
            }}
            // Force delete auth tokens
            document.cookie = "rms_auth_token=;expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/";
            document.cookie = "rms_EncryptedCookieManager.key_params=;expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/";
            document.cookie = "auth_token=;expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/";
        }})();
        // Replace browser history to prevent back button
        window.location.replace("{page_url.login_url}");
    </script>
    """
    components.html(logout_js, height=0, width=0)
    st.switch_page(page_url.login_url)
    st.stop()


def ensure_admin_only():
    """
    Convenience function specifically for ADMIN-only access.
    Equivalent to enforce_strict_access("ADMIN")
    
    Usage:
        from utils.access_guard import ensure_admin_only
        ensure_admin_only()
    """
    enforce_strict_access("ADMIN")