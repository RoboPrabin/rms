from time import sleep
from contextlib import suppress
import streamlit as st
from utils import helper, page_url
import streamlit_bridge.navigation as navigation
from streamlit_bridge.permissions import DEFAULT_ROLE_ACCESS, ALL_MENU_KEYS
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage
from db.db import get_connection


MENU_SECTIONS = [
    # ── Column 1: Business Information ────────────────────
    {
        "label": "Business information",
        "badge": "BI",
        "badge_color": "#E1F5EE",
        "badge_text": "#085041",
        "items": [
            ("reports",           "📂", "Reports"),
            ("client_profile",    "🖊️", "Client profile"),
            ("business_turnover", "🅱️", "Business turnover"),
            ("top_broker",        "🏦", "Top brokers"),
            ("cbr",               "🌱", "Cost benefit"),
            ("business_ratio",    "⚖️", "Business ratio"),
            ("floorsheet",        "📄", "Floorsheet"),
            ("due_list",          "📋", "Due list"),
            ("book_closure",      "📫", "Book closure"),
            ("gallery",           "📸", "Gallery"),
            ("dpm3",              "📦", "DPM3"),
            ("edis_call",         "📞", "EDIS call"),
        ],
        "sub": [
            {
                "label": "Accounts",
                "badge": "AC",
                "badge_color": "#E8F4FD",
                "badge_text": "#0C447C",
                "items": [
                    ("cashin_out",       "📖", "Cash In/Out"),
                    ("pay_rec",          "💸", "Payable & receivable"),
                    ("unverified_trans", "⚠️", "Unverified transactions"),
                ],
            },
        ],
    },

    # ── Column 2: RM Management + KYC + AML ──────────────
    {
        "label": "RM management",
        "badge": "RM",
        "badge_color": "#E6F1FB",
        "badge_text": "#0C447C",
        "items": [
            ("live_rm",     "🟢", "Live RM performance"),
            ("client_comm", "📅", "Client communication"),
            ("client_limit",      "💷", "Client limit"),
            ("bro_limit",   "🧮", "BRO limit manager"),
            ("bro_targets", "🎯", "RM targets & achievements"),
            ("rm_tag",      "🏷️", "RM tag"),
        ],
        "sub": [
            {
                "label": "KYC",
                "badge": "KYC",
                "badge_color": "#EEEDFE",
                "badge_text": "#3C3489",
                "items": [
                    ("kyc_modify",    "📚", "KYC modification"),
                    ("demat_records", "🧾", "TMS and Demat records"),
                    ("tms_code",      "🏷️", "TMS code"),
                ],
            },
            {
                "label": "AML",
                "badge": "AML",
                "badge_color": "#FAECE7",
                "badge_text": "#712B13",
                "items": [
                    ("transaction_monitoring", "🕵️", "Transaction monitoring"),
                    ("trade_history",          "🔎", "Trade history"),
                    ("risk_monitoring",        "🚨", "Risk monitoring"),
                    ("notable_client",         "⭐", "Notable client"),
                ],
            },
        ],
    },

    # ── Column 3: User Management + Utility ──────────────
    {
        "label": "User management",
        "badge": "UM",
        "badge_color": "#FAEEDA",
        "badge_text": "#633806",
        "items": [
            ("create_user",    "➕", "Create app user"),
            ("access_management",    "📌", "Access management"),
            ("active_session", "🕓", "Active sessions"),
            ("meroshare",      "📝", "Meroshare"),
            ("automation",     "⚡", "Automations"),
        ],
        "sub": [
            {
                "label": "Utility",
                "badge": "UT",
                "badge_color": "#F1EFE8",
                "badge_text": "#444441",
                "items": [
                    ("tri_projects",         "📁", "Trishakti projects"),
                    ("profile",              "💼", "Profile"),
                    ("communication_report", "📢", "Communication report"),
                    ("project_request",      "🤝", "Project request"),
                    ("digital_vault",        "🔐", "Digital vault"),
                    ("uarf",                 "🪪", "UARF"),
                    ("cache",                "🗑️", "Cache"),
                    ("mail_cleaner",         "📧", "Mail cleaner"),
                    ("feedback",             "💬", "Feedback"),
                    ("view_feedback",        "💬", "View feedback"),
                    ("interest_calc",        "🧩", "Interest calculation"),
                ],
            },
        ],
    },
]


# ==========================================================
# DB helpers
# ==========================================================

def _ensure_table():
    """Create user_menu_access table if it does not exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_menu_access (
                    id          SERIAL PRIMARY KEY,
                    username    VARCHAR(50)  NOT NULL,
                    menu_item   VARCHAR(100) NOT NULL,
                    has_access  BOOLEAN      DEFAULT FALSE,
                    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                    updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (username, menu_item)
                )
            """)
            conn.commit()


def _load_app_users() -> list[str]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username
                FROM app_user
                WHERE role <> 'ADMIN'
                ORDER BY username
            """)
            return [row[0] for row in cur.fetchall()]


def _load_user_detail(username: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, full_name, email, role
                FROM app_user
                WHERE username = %s
            """, (username,))
            return cur.fetchone()


def _load_db_permissions(username: str) -> dict:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'user_menu_access'
                    )
                """)
                if not cur.fetchone()[0]:
                    return {}
                cur.execute("""
                    SELECT menu_item, has_access
                    FROM user_menu_access
                    WHERE username = %s
                """, (username,))
                return {row[0]: row[1] for row in cur.fetchall()}
    except Exception as e:
        st.warning(f"Could not load permissions: {e}")
        return {}


def _save_permissions(username: str, permissions: dict):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for menu_item, has_access in permissions.items():
                    cur.execute("""
                        INSERT INTO user_menu_access (username, menu_item, has_access, updated_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (username, menu_item)
                        DO UPDATE SET has_access = EXCLUDED.has_access,
                                      updated_at = CURRENT_TIMESTAMP
                    """, (username, menu_item, has_access))
                conn.commit()
    except Exception as e:
        st.error(f"Failed to save permissions: {e}")


# ==========================================================
# Permission resolution
# ==========================================================

def _normalize_role(role: str) -> str:
    return str(role).upper().strip()


def _resolve_permissions(role: str, db_perms: dict) -> dict:
    """
    Merge role defaults with DB overrides.
      DB True    → grant access
      DB False   → fall back to role default (DB cannot revoke a role default)
      DB missing → use role default
    """
    role_key = _normalize_role(role)
    role_defaults = DEFAULT_ROLE_ACCESS.get(role_key, DEFAULT_ROLE_ACCESS["DEFAULT"])

    merged = {}
    for key in ALL_MENU_KEYS:
        db_val = db_perms.get(key)
        if db_val is True:
            merged[key] = True
        else:
            merged[key] = role_defaults.get(key, False)
    return merged


def _is_role_default(key: str, role: str) -> bool:
    role_key = _normalize_role(role)
    return bool(DEFAULT_ROLE_ACCESS.get(role_key, {}).get(key, False))


# ==========================================================
# Widget state helpers
# ==========================================================

def _widget_key(menu_key: str, username: str) -> str:
    return f"acm__{username}__{menu_key}"


def _clear_widget_state(username: str):
    prefix = f"acm__{username}__"
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(prefix):
            st.session_state.pop(k, None)


def _seed_widget_state(username: str, effective: dict):
    """Seed toggle state only on first render after a user change."""
    for key, val in effective.items():
        wk = _widget_key(key, username)
        if wk not in st.session_state:
            st.session_state[wk] = val


# ==========================================================
# Section renderer helpers
# ==========================================================

def _render_toggles(items: list, username: str, user_role: str):
    for menu_key, icon, label in items:
        wk        = _widget_key(menu_key, username)
        is_locked = _is_role_default(menu_key, user_role)
        display   = f"{icon} {label}"
        if is_locked:
            display += "  🔒"

        st.toggle(
            display,
            key=wk,
            help="Granted by role default." if is_locked else None,
        )


def _render_section(section: dict, username: str, user_role: str, expanded: bool = False):
    title = f"`{section['badge']}`  {section['label']}"
    with st.expander(title, expanded=expanded):
        _render_toggles(section["items"], username, user_role)


def _render_column(section: dict, username: str, user_role: str):
    _render_section(section, username, user_role, expanded=False)
    for sub in section.get("sub", []):
        _render_section(sub, username, user_role, expanded=False)


# ==========================================================
# Page class
# ==========================================================

class AccessManagement(BasePage):
    def __init__(self):
        super().__init__(require_auth_check=True, required_role="ADMIN")
        helper.eliminate_top_padding()
        st.session_state.active_menu = "user"
        st.set_page_config("Access Management", page_icon="📌", layout="wide")
        activate_client_code_hotkey()
        _ensure_table()
        navigation.render_sidebar()
        self._render()

    # ----------------------------------------------------------
    def _render(self):
        st.header("📌 Access Management", anchor=False)

        # ── User selector ───────────────────────────────────
        users = _load_app_users()
        if not users:
            st.warning("No app users found.")
            st.stop()

        selected_user = st.selectbox(
            "App users",
            users,
            index=None,
            placeholder="Select user",
        )

        if not selected_user:
            return

        # Clear stale widget state when selection changes
        prev = st.session_state.get("_acm_selected_user")
        if prev != selected_user:
            if prev:
                _clear_widget_state(prev)
            st.session_state["_acm_selected_user"] = selected_user

        # ── User detail ─────────────────────────────────────
        user_detail = _load_user_detail(selected_user)
        if user_detail is None:
            st.warning(f"No details found for: {selected_user}")
            st.stop()

        username, full_name, email, user_role = user_detail

        with st.container(border=True):
            st.markdown("##### User details")
            r1, r2 = st.columns(2), st.columns(2)
            r1[0].text_input("Username",  username,    disabled=True)
            r1[1].text_input("Full name", full_name,   disabled=True)
            r2[0].text_input("Email",     email or "", disabled=True)
            r2[1].text_input("Role",      user_role,   disabled=True)

        # ── Resolve & seed permissions ──────────────────────
        db_perms  = _load_db_permissions(username)
        effective = _resolve_permissions(user_role, db_perms)
        _seed_widget_state(username, effective)

        # ── 3-column expander grid ─────────────────────────
        st.markdown("#### Access details")
        col1, col2, col3 = st.columns(3)

        with col1:
            _render_column(MENU_SECTIONS[0], username, user_role)

        with col2:
            _render_column(MENU_SECTIONS[1], username, user_role)

        with col3:
            _render_column(MENU_SECTIONS[2], username, user_role)

        # ── Save button ─────────────────────────────────────
        if st.button("💾 Save permissions", type="primary"):
            new_perms = {}
            for section in MENU_SECTIONS:
                for menu_key, _, _ in section["items"]:
                    wk = _widget_key(menu_key, username)
                    new_perms[menu_key] = st.session_state.get(wk, False)
                for sub in section.get("sub", []):
                    for menu_key, _, _ in sub["items"]:
                        wk = _widget_key(menu_key, username)
                        new_perms[menu_key] = st.session_state.get(wk, False)

            _save_permissions(username, new_perms)
            st.toast("✅ Permissions updated successfully")
            sleep(0.4)
            st.rerun()


if __name__ == "__main__":
    page = AccessManagement()