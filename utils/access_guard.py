import time
import streamlit as st
from utils import page_url
from db.db import get_connection

_audit_table_ensured = False


def _ensure_audit_table():
    global _audit_table_ensured
    if _audit_table_ensured:
        return
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS access_audit_log (
                        id              SERIAL PRIMARY KEY,
                        username        VARCHAR(100),
                        page_accessed    VARCHAR(200),
                        ip_address       VARCHAR(50),
                        success          BOOLEAN,
                        reason           TEXT,
                        accessed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        _audit_table_ensured = True
    except Exception:
        _audit_table_ensured = True


def _invalidate_user_session(username: str):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_session
                    SET session_status = 'EXPIRED'
                    WHERE UPPER(username) = UPPER(%s)
                    AND session_status = 'ACTIVE'
                """, (username,))
            conn.commit()
    except Exception:
        pass


def _validate_db_session(username: str) -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT session_status
                    FROM user_session
                    WHERE UPPER(username) = UPPER(%s)
                    AND session_status = 'ACTIVE'
                    LIMIT 1
                """, (username,))
                result = cur.fetchone()
                return result is not None
    except Exception:
        return True


def _log_access_attempt(username: str, page: str, success: bool, reason: str = ""):
    try:
        _ensure_audit_table()
        from utils.helper import get_client_ip
        ip_address = get_client_ip()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO access_audit_log (username, page_accessed, ip_address, success, reason, accessed_at)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (username, page, ip_address, success, reason))
            conn.commit()
    except Exception:
        pass


def _prevent_cached_page():
    st.html("""
        <script>
        if (window.history && window.history.pushState) {
            window.history.pushState(null, '', window.location.href);
            window.addEventListener('popstate', function(event) {
                window.history.pushState(null, '', window.location.href);
                window.location.reload();
            });
        }
        </script>
    """)


def _redirect_to_login():
    st.html("""
        <script>
        window.location.replace(arguments[0]);
        </script>
    """.format(page_url.login_url))
    st.stop()


def _enforce_logout(username: str = "", page: str = "access_management"):
    if username:
        _log_access_attempt(username, page, False, "Unauthorized access attempt - forced logout")
        _invalidate_user_session(username)

    _prevent_cached_page()

    st.query_params.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.clear()

    st.error("Access denied. Redirecting to login...")

    st.html(f"""
        <script>
        window.location.replace("{page_url.login_url}");
        </script>
    """)
    st.stop()


def enforce_strict_access(required_role: str = "ADMIN", page_name: str = ""):
    current_page = page_name or "restricted_page"
    username = st.session_state.get("username", "")

    _prevent_cached_page()

    if not st.session_state.get("auth"):
        _enforce_logout(username, current_page)

    if not username:
        _enforce_logout(username, current_page)

    role = str(st.session_state.get("role", "")).upper().strip()
    required_role_upper = str(required_role).upper().strip()

    if role != required_role_upper:
        _enforce_logout(username, current_page)

    if not _validate_db_session(username):
        _enforce_logout(username, current_page)

    sid = st.query_params.get("sid")
    if sid:
        try:
            from utils.security import decrypt_data
            payload = decrypt_data(sid)
            if payload:
                st.session_state.update(payload)
                if "expiry" in payload and payload.get("expiry", 0) <= int(time.time()):
                    _enforce_logout(username, current_page)
                if payload.get("username", "").upper() != username.upper():
                    _enforce_logout(username, current_page)
        except Exception:
            pass

    _log_access_attempt(username, current_page, True, "Access granted")
    return True


def ensure_admin_only(page_name: str = "access_management"):
    enforce_strict_access("ADMIN", page_name)
