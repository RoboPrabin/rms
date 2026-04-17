import streamlit as st
from streamlit_bridge.auth_bootstrap import bootstrap_session
from utils import page_url
from utils.security import decrypt_data
from db.db import get_connection
import time


class BasePage:
    _auth_checked = False
    _auth_valid = False

    def __init__(self, require_auth_check=True, required_role=None):
        self._auth_valid = False

        if "sid" in st.session_state and "sid" not in st.query_params:
            st.query_params["sid"] = st.session_state.sid

        bootstrap_session()

        self.username = st.session_state.get("username")
        self.role = st.session_state.get("role")
        self.branch = st.session_state.get("branch")
        self.sid = st.session_state.get("sid")
        self.id = st.session_state.get("id")
        self.email = st.session_state.get("email")

        if require_auth_check:
            self._check_auth(required_role)

    def _check_auth(self, required_role=None):
        self._prevent_back_navigation()

        if not self._is_authenticated():
            self._force_logout()
            return

        if not self.username:
            self._force_logout()
            return

        if required_role:
            if not self._check_role(required_role):
                self._force_logout()
                return

        if not self._validate_db_session():
            self._force_logout()
            return

        if not self._validate_sid_token():
            self._force_logout()
            return

        self._auth_valid = True

    def _is_authenticated(self) -> bool:
        return bool(st.session_state.get("auth")) and bool(st.session_state.get("username"))

    def _check_role(self, required_role: str) -> bool:
        user_role = str(self.role or "").upper().strip()
        required = str(required_role).upper().strip()
        return user_role == required

    def _validate_db_session(self) -> bool:
        if not self.username:
            return False
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT session_status
                        FROM user_session
                        WHERE UPPER(username) = UPPER(%s)
                        AND session_status = 'ACTIVE'
                        LIMIT 1
                    """, (self.username,))
                    result = cur.fetchone()
                    return result is not None
        except Exception:
            return True

    def _validate_sid_token(self) -> bool:
        sid = st.query_params.get("sid")
        if not sid:
            sid = st.session_state.get("sid")
        if not sid:
            return False
        try:
            payload = decrypt_data(sid)
            if not payload:
                return False
            if payload.get("expiry", 0) <= int(time.time()):
                return False
            if payload.get("username", "").upper() != self.username.upper():
                return False
            return True
        except Exception:
            return False

    def _invalidate_db_session(self):
        if not self.username:
            return
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_session
                        SET session_status = 'EXPIRED'
                        WHERE UPPER(username) = UPPER(%s)
                        AND session_status = 'ACTIVE'
                    """, (self.username,))
                conn.commit()
        except Exception:
            pass

    def _prevent_back_navigation(self):
        st.html("""
            <script>
            if (window.history && window.history.pushState) {
                history.pushState(null, '', location.href);
                window.addEventListener('popstate', function(event) {
                    history.pushState(null, '', location.href);
                    window.location.reload();
                });
            }
            window.addEventListener('load', function() {
                setTimeout(function() {
                    if (window.history && window.history.pushState) {
                        history.pushState(null, '', location.href);
                    }
                }, 100);
            });
            </script>
        """)

    def _force_logout(self):
        self._invalidate_db_session()

        st.query_params.clear()
        keys_to_delete = [k for k in st.session_state.keys()
                         if k not in ["_cached_retry_000", "_cached_retry_001"]]
        for key in keys_to_delete:
            del st.session_state[key]

        st.cache_data.clear()
        st.cache_resource.clear()

        st.html(f"""
            <script>
            window.location.replace("{page_url.login_url}");
            </script>
        """)
        st.error("Session expired. Redirecting...")
        time.sleep(2)
        if st.button("Login Again", icon="🔄"):
            st.switch_page(page_url.login_url)
        st.stop()


    def logout(self):
        self._invalidate_db_session()

        st.query_params.clear()
        keys_to_delete = [k for k in st.session_state.keys()
                         if k not in ["_cached_retry_000", "_cached_retry_001"]]
        for key in keys_to_delete:
            del st.session_state[key]

        st.cache_data.clear()
        st.cache_resource.clear()

        st.html(f"""
            <script>
            window.location.replace("{page_url.login_url}");
            </script>
        """)
        st.success("Logged out successfully!")
        time.sleep(0.5)
        st.switch_page(page_url.login_url)
        st.stop()

    @property
    def is_admin(self) -> bool:
        return self._check_role("ADMIN")

    @property
    def is_manager(self) -> bool:
        return self._check_role("MANAGER")

    @property
    def is_authenticated(self) -> bool:
        return self._auth_valid
