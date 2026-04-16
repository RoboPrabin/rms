from time import sleep
from contextlib import suppress
import streamlit as st
from utils import helper
import streamlit_bridge.navigation as navigation
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage
from db.db import get_connection
from utils import auth_utils




DEFAULT_ROLE_ACCESS = {
    "ADMIN": {},

    "MANAGEMENT": {
        "reports": True,
        "client_profile": True,
        "client_limit": True,
        "business_turnover": True,
        "top_broker": True,
        "cbr": True,
        "business_ratio": True,
        "floorsheet": True,
        "due_list": True,
        "pay_rec": True,
        "unverified_trans": True,
        "book_closure": True,
        "dpm3": True,
        "meroshare": True,
        "gallery": True,
        "live_rm": True,
        "client_comm": True,
        "bro_targets": True,
        "rm_tag": True,
        "kyc_modify": True,
        "demat_records": True,
        "transaction_monitoring": True,
        "tri_projects": True,
        "profile": True,
        "communication_report": True,
        "project_request": True,
        "digital_vault": True,
        "uarf": True,
        "cache": True,
        "feedback": True,
        "cashin_out": True,
        "trade_history": True,
    },

    "MANAGER": {
        "reports": True,
        "client_profile": True,
        "client_limit": True,
        "business_turnover": True,
        "top_broker": True,
        "cbr": True,
        "business_ratio": True,
        "floorsheet": True,
        "due_list": True,
        "pay_rec": True,
        "unverified_trans": True,
        "book_closure": True,
        "dpm3": True,
        "meroshare": True,
        "gallery": True,
        "live_rm": True,
        "client_comm": True,
        "bro_targets": True,
        "rm_tag": True,
        "kyc_modify": True,
        "demat_records": True,
        "transaction_monitoring": True,
        "profile": True,
        "communication_report": True,
        "project_request": True,
        "digital_vault": True,
        "uarf": True,
        "cache": True,
        "feedback": True,
        "cashin_out": True,
        "trade_history": True,
    },

    "BM": {
        "profile": True,
        "uarf": True,
        "feedback": True,
    },

    "RM": {
        "bro_targets": True,
        "live_rm": True,
        "rm_tag": True,
    },

    "BRO": {
        "live_rm": True,
        "client_comm": True,
        "client_limit": True,
        "bro_targets": True,
        "rm_tag": True,
        "client_profile": True,
        "due_list": True,
        "top_broker": True,
        "book_closure": True,
        "gallery": True,
        "meroshare": True,
        "uarf": True,
        "communication_report": True,
        "project_request": True,
        "digital_vault": True,
        "profile": True,
        "feedback": True,
        "trade_history": True,
    },

    "HR": {
        "uarf": True,
        "top_broker": True,
        "pay_rec": True,
        "book_closure": True,
        "gallery": True,
        "communication_report": True,
        "project_request": True,
        "digital_vault": True,
        "profile": True,
        "feedback": True,
    },

    "IT": {
        "uarf": True,
        "create_user": True,
        "top_broker": True,
        "pay_rec": True,
        "bro_targets": True,
        "book_closure": True,
        "gallery": True,
        "communication_report": True,
        "project_request": True,
        "digital_vault": True,
        "profile": True,
        "feedback": True,
    },

    "VIEWER": {
        "cbr": True,
        "client_profile": True,
        "unverified_trans": True,
        "live_rm": True,
        "dpm3": True,
        "due_list": True,
        "top_broker": True,
        "rm_tag": True,
        "book_closure": True,
        "gallery": True,
        "communication_report": True,
        "project_request": True,
        "digital_vault": True,
        "profile": True,
        "feedback": True,
    },

    "USER": {
        "book_closure": True,
        "edis_call": True,
        "demat_records": True,
        "pay_rec": True,
        "uarf": True,
        "gallery": True,
        "profile": True,
    },

    "DEFAULT": {},
}


# ==========================================================
# All possible menu permission keys
# ==========================================================

ALL_MENU_KEYS = {
    "dashboard",
    "interest_calc",
    "pledge",
    "reports",
    "client_profile",
    "client_limit",
    "business_turnover",
    "top_broker",
    "cbr",
    "business_ratio",
    "floorsheet",
    "due_list",
    "pay_rec",
    "unverified_trans",
    "book_closure",
    "gallery",
    "dpm3",
    "edis_call",
    "live_rm",
    "client_comm",
    "bro_limit",
    "bro_targets",
    "rm_tag",
    "kyc_modify",
    "demat_records",
    "transaction_monitoring",
    "create_user",
    "active_session",
    "meroshare",
    "automation",
    "tri_projects",
    "profile",
    "communication_report",
    "project_request",
    "digital_vault",
    "uarf",
    "cache",
    "feedback",
    "view_feedback",
    "access_management",
    "cashin_out",
    "trade_history",
    "tms_code",
}

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
                    ("demat_records", "🧾", "Demat records"),
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

def _resolve_permissions(role: str, db_perms: dict) -> dict:
    """
    Merge role defaults with DB overrides.
      DB True    → grant access
      DB False   → fall back to role default (DB cannot revoke a role default)
      DB missing → use role default
    """
    role_key = str(role).upper().strip()
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
    role_key = str(role).upper().strip()
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
            del st.session_state[k]


def _seed_widget_state(username: str, effective: dict):
    """Seed toggle state only on first render after a user change."""
    for key, val in effective.items():
        wk = _widget_key(key, username)
        if wk not in st.session_state:
            st.session_state[wk] = val


# ==========================================================
# Section renderer helpers
# ==========================================================

def _render_section_header(label: str, badge: str, badge_color: str, badge_text: str):
    """Render a colored badge + section title."""
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:7px;margin-bottom:6px;'>"
        f"<span style='background:{badge_color};color:{badge_text};"
        f"font-size:10px;padding:2px 7px;border-radius:4px;font-weight:500;"
        f"'>{badge}</span>"
        f"<span style='font-size:13px;font-weight:500;'>{label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_toggles(items: list, username: str, user_role: str):
    """Render a list of toggle rows for the given items."""
    for menu_key, icon, label in items:
        wk        = _widget_key(menu_key, username)
        is_locked = _is_role_default(menu_key, user_role)
        display   = f"{icon} {label}"
        if is_locked:
            display += "  🔒"

        st.toggle(
            display,
            key=wk,
            # disabled=is_locked,
            help="Granted by role default — cannot be revoked here." if is_locked else None,
        )


def _render_column(section: dict, username: str, user_role: str):
    """
    Render one full column: the primary section header + toggles,
    then any sub-sections separated by a divider.
    """
    _render_section_header(
        section["label"],
        section["badge"],
        section["badge_color"],
        section["badge_text"],
    )
    _render_toggles(section["items"], username, user_role)

    for sub in section.get("sub", []):
        st.markdown(
            "<hr style='margin:10px 0 8px 0;border:none;"
            "border-top:0.5px solid var(--color-border-tertiary);'>",
            unsafe_allow_html=True,
        )
        _render_section_header(
            sub["label"],
            sub["badge"],
            sub["badge_color"],
            sub["badge_text"],
        )
        _render_toggles(sub["items"], username, user_role)


# ==========================================================
# Page class
# ==========================================================

class AccessManagement(BasePage):
    def __init__(self):
        super().__init__()
        auth_utils.ensure_admin()
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

        st.subheader("User details", anchor=False)
        c1, c2, c3, c4 = st.columns(4)
        c1.text_input("Username",  username,    disabled=True)
        c2.text_input("Full name", full_name,   disabled=True)
        c3.text_input("Email",     email or "", disabled=True)
        c4.text_input("Role",      user_role,   disabled=True)

        # ── Resolve & seed permissions ──────────────────────
        db_perms  = _load_db_permissions(username)
        effective = _resolve_permissions(user_role, db_perms)
        _seed_widget_state(username, effective)

        # ── Organized 3-column toggle grid ──────────────────
        with st.container(border=True):
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