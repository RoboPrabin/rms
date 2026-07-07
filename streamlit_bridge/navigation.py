import base64
import logging
from datetime import datetime

import streamlit as st
from utils import page_url
from db.db import get_connection
from config import config

from streamlit_bridge.permissions import DEFAULT_ROLE_ACCESS, ALL_MENU_KEYS

logger = logging.getLogger(__name__)


# ==========================================================
# Sidebar section → permission key → (url, label) mapping
# ==========================================================

# Business Information
BI_MAP = {
    "reports":           (page_url.reports_url,           "📂 Reports"),
    "client_profile":    (page_url.client_remarks_url,    "🖊️ Client profile"),
    "business_turnover": (page_url.business_turnover_url, "🅱️ Business turnover"),
    "top_broker":        (page_url.top_broker_url,        "🏦 Top brokers"),
    "cbr":               (page_url.cbr_url,               "🌱 Cost benefit"),
    "business_ratio":    (page_url.business_ratio_url,    "⚖️ Business ratio"),
    "floorsheet":        (page_url.floorsheet_url,        "📄 Floorsheet"),
    "due_list":          (page_url.due_list_url,          "📋 Due list"),
    "book_closure":      (page_url.book_closure_url,      "📫 Book closure"),
    "gallery":           (page_url.gallery_url,           "📸 Gallery"),
    "dpm3":              (page_url.dpm_3_url,             "📦 DPM3"),
    "edis_call":         (page_url.edis_call_url,         "📞 EDIS call"),
}

# Accounts
ACCOUNTS_MAP = {
    "cashin_out":       (page_url.cashin_out_url,       "📖 Cash In/Out"),
    "pay_rec":          (page_url.pay_rec_url,           "💸 Payable & receivable"),
    "unverified_trans": (page_url.unverified_trans_url,  "⚠️ Unverified transactions"),
}

# RM Management
RM_MAP = {
    "live_rm":     (page_url.live_rm_performance_url,          "🟢 Live RM performance"),
    "client_comm": (page_url.client_communication,             "📅 Client communication"),
    "client_limit":      (page_url.client_limit_url,      "💷 Client limit"),
    "bro_limit":   (page_url.bro_limit_url,                   "🧮 BRO limit manager"),
    "bro_targets": (page_url.bro_targets_and_achievements_url, "🎯 RM targets & achievements"),
    "rm_tag":      (page_url.rm_tag_url,                      "🏷️ RM tag"),
}

# KYC
KYC_MAP = {
    "kyc_modify":    (page_url.kyc_modify,        "📚 KYC modification"),
    "demat_records": (page_url.demat_records_url, "🧾 TMS and Demat records"),
    "tms_code":      (page_url.tms_code_url,      "🏷️ TMS code"),
}

# AML
AML_MAP = {
    "transaction_monitoring": (page_url.transaction_monitoring_url, "🕵️ Transaction monitoring"),
    "trade_history":          (page_url.trade_history_url,          "🔎 Trade history"),
    "risk_monitoring":        (page_url.risk_monitoring_url,        "🚨 Risk monitoring"),
    "notable_client":         (page_url.notable_client_url,         "⭐ Notable client"),
}

# User Management
UM_MAP = {
    "create_user":    (page_url.create_app_user_url, "➕ Create app user"),
    "active_session": (page_url.active_session_url,  "🕓 Active sessions"),
    "meroshare":      (page_url.meroshare_url,        "📝 Meroshare"),
}

# Utility
UTILITY_MAP = {
    "tri_projects":         (page_url.tri_projects_url,         "📁 Trishakti projects"),
    "profile":              (page_url.profile_url,              "💼 Profile"),
    "communication_report": (page_url.communication_report_url, "📢 Communication report"),
    "project_request":      (page_url.project_request_url,      "🤝 Project request"),
    "mail_cleaner":         (page_url.mail_cleaner_url,         "📧 Mail cleaner"),
    "digital_vault":        (page_url.digital_url,              "🔐 Digital vault"),
    "uarf":                 (page_url.uarf_url,                 "🪪 UARF"),
    "cache":                (page_url.cache_url,                "🗑️ Cache"),
    "feedback":             (page_url.feedback_url,             "💬 Feedback"),
    "view_feedback":        (page_url.view_feedback_url,        "💬 View feedback"),
}


# ==========================================================
# Live clock (1-second fragment)
# ==========================================================

@st.fragment(run_every="1s")
def live_clock():
    now = datetime.now()
    formatted_time = now.strftime("%I:%M:%S %p")
    st.markdown(
        f"<div style='font-size:14px; font-weight:bold; color:#a6a6a6; "
        f"text-align:center; margin-top:-32px;'>{formatted_time}</div>",
        unsafe_allow_html=True,
    )


# ==========================================================
# Image helper
# ==========================================================

def _get_base64_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ==========================================================
# Permission resolver
# ==========================================================

def get_user_menu_permissions(username: str, user_role: str | None = None) -> dict:
    """
    Merge role-level defaults with per-user DB overrides.
    DB True  → grant access regardless of role default.
    DB False / missing → fall back to role default.
    Returns only keys where access is True.
    """
    if not username:
        return {}

    role_key      = str(user_role).upper().strip() if user_role else "DEFAULT"
    role_defaults = DEFAULT_ROLE_ACCESS.get(role_key, DEFAULT_ROLE_ACCESS["DEFAULT"])

    db_permissions: dict = {}
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT menu_item, has_access
                    FROM user_menu_access
                    WHERE username = %s
                """, (username,))
                db_permissions = {row[0]: row[1] for row in cur.fetchall()}
    except Exception as e:
        logger.warning("Could not load menu permissions for %s: %s", username, e)

    merged = {}
    for key in ALL_MENU_KEYS:
        db_val = db_permissions.get(key)
        if db_val is True:
            merged[key] = True
        else:
            merged[key] = role_defaults.get(key, False)

    return {k: v for k, v in merged.items() if v}


# ==========================================================
# Sidebar helpers
# ==========================================================

def _collect(mapping: dict, permissions: dict) -> list[tuple[str, str]]:
    """Return (url, label) pairs for permitted keys."""
    return [
        (url, label)
        for key, (url, label) in mapping.items()
        if permissions.get(key)
    ]


def _render_header(img_base64: str, username: str, role: str, branch: str):
    """Animated spinning-comet logo + user info header."""

    st.markdown("""
        <style>
            [data-testid="stSidebarCollapseButton"] {
                visibility: visible !important;
                opacity: 1 !important;
            }
            section[data-testid="stSidebar"] > div:first-child {
                padding-top: 0 !important;
                margin-top: 0 !important;
            }
            section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                padding-top: 0 !important;
                margin-top: 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(
        f"""
        <style>
        .circle-wrapper {{
            position: relative;
            width: 140px;
            height: 140px;
            margin: 0 auto;
            margin-top: -30px !important;
        }}

        /* ── Static dim track ring ── */
        .circle-wrapper::after {{
            content: "";
            position: absolute;
            top: -4px;
            left: -4px;
            width: 148px;
            height: 148px;
            border-radius: 50%;
            background: rgba(0,63,140,0.15);
            -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 4px), black 0);
            mask:         radial-gradient(farthest-side, transparent calc(100% - 4px), black 0);
            z-index: 0;
        }}

        /* ── Spinning comet arc ── */
        .circle-wrapper::before {{
            content: "";
            position: absolute;
            top: -4px;
            left: -4px;
            width: 148px;
            height: 148px;
            border-radius: 50%;
            background: conic-gradient(
                from 0deg,
                transparent         0deg,
                transparent         260deg,
                rgba(0,63,140,0.2)  275deg,
                #24A148             300deg,
                #F4F4F4             320deg,
                #003F8C             340deg,
                transparent         360deg
            );
            -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 4px), black 0);
            mask:         radial-gradient(farthest-side, transparent calc(100% - 4px), black 0);
            animation: spin 3s linear infinite;
            z-index: 1;
        }}

        /* ── Image circle ── */
        .circle-img {{
            width: 140px;
            height: 140px;
            border-radius: 50%;
            overflow: hidden;
            position: relative;
            z-index: 2;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #F4F4F4;
            box-shadow: 0 0 0 2px rgba(0,63,140,0.15);
        }}

        /* ── Shimmer overlay ── */
        .circle-img::after {{
            content: "";
            position: absolute;
            inset: 0;
            border-radius: 50%;
            background: linear-gradient(
                135deg,
                rgba(244,244,244,0.18) 0%,
                transparent 45%,
                rgba(0,63,140,0.07) 100%
            );
            pointer-events: none;
            z-index: 3;
        }}

        @keyframes spin {{
            from {{ transform: rotate(0deg); }}
            to   {{ transform: rotate(360deg); }}
        }}
        </style>

        <div style='text-align:center; padding: 20px 0 10px 0;'>
            <div class="circle-wrapper">
                <div class="circle-img">
                    <img src="data:image/png;base64,{img_base64}"
                         style="width:auto; height:auto; object-fit:contain;" />
                </div>
            </div>
        </div>

        <div style='text-align:center; margin:15px 0 25px; color:#444;'>
            <div style='font-size:14px; font-weight:bold; color:#a6a6a6; margin-top:0px;'>
                <span>{username.upper()}</span> | {role.upper()} <br> {branch}
            </div>
        </div>

        <hr style='margin:0 0 12px 0; border:0; border-top:1px solid #eee;'>
        """,
        unsafe_allow_html=True,
    )


# ==========================================================
# Main sidebar renderer
# ==========================================================

def render_sidebar():
    if "active_menu" not in st.session_state:
        st.session_state.active_menu = None

    state    = st.session_state
    username = state.get("username", "")
    role     = str(state.get("role", "")).upper().strip()
    branch   = state.get("branch", "")

    is_admin    = role == "ADMIN"
    active_menu = st.session_state.get("active_menu")

    # Admins get every key; all other roles go through the permission resolver
    permissions = (
        {key: True for key in ALL_MENU_KEYS}
        if is_admin
        else get_user_menu_permissions(username, role)
    )

    with st.sidebar:

        # live_clock() 
        
        # ── Animated header ──────────────────────────────────
        try:
            img_base64 = _get_base64_image(config.sidebar_icon)
        except Exception:
            img_base64 = ""

        _render_header(img_base64, username, role, branch)

        # ── Dashboard ────────────────────────────────────────
        st.page_link(page_url.dashbord_url, label="🏠 Dashboard")

        # ── Interest Calculation (non-USER roles) ─────────────
        if permissions.get("interest_calc") and role != "USER":
            st.page_link(page_url.interest_calc_url, label="🧩 Interest calculation")

        # ── Business Information ──────────────────────────────
        bi_items = _collect(BI_MAP, permissions)
        if bi_items:
            with st.expander("🅱️ Business information", expanded=(active_menu == "business")):
                for url, label in bi_items:
                    st.page_link(url, label=label)

        # ── Accounts ─────────────────────────────────────────
        accounts_items = _collect(ACCOUNTS_MAP, permissions)
        if accounts_items:
            with st.expander("📖 Accounts", expanded=(active_menu == "account")):
                for url, label in accounts_items:
                    st.page_link(url, label=label)

        # ── RM Management ─────────────────────────────────────
        rm_items = _collect(RM_MAP, permissions)
        if rm_items:
            with st.expander("🧑 RM management", expanded=(active_menu == "rm")):
                for url, label in rm_items:
                    st.page_link(url, label=label)

        # ── KYC ───────────────────────────────────────────────
        kyc_items = _collect(KYC_MAP, permissions)
        if kyc_items:
            with st.expander("🧾 KYC", expanded=(active_menu == "kyc")):
                for url, label in kyc_items:
                    st.page_link(url, label=label)

        # ── AML ───────────────────────────────────────────────
        aml_items = _collect(AML_MAP, permissions)
        if aml_items:
            with st.expander("🕵️ AML", expanded=(active_menu == "aml")):
                for url, label in aml_items:
                    st.page_link(url, label=label)

        # ── User Management ───────────────────────────────────
        um_items = _collect(UM_MAP, permissions)
        # Automations: only for ADMIN username (matches original navigation.py logic)
        if permissions.get("automation") and username.upper() == "ADMIN":
            um_items.append((page_url.automation_url, "⚡ Automations"))
            
            
        if um_items:
            with st.expander("🤹 User management", expanded=(active_menu == "user")):
                if is_admin or permissions.get("access_management"):
                    st.page_link(page_url.access_management_url, label="📌 Access management")
                for url, label in um_items:
                    st.page_link(url, label=label)

        # ── Utility ───────────────────────────────────────────
        utility_items = _collect(UTILITY_MAP, permissions)
        if utility_items:
            with st.expander("🛠️ Utility", expanded=(active_menu == "utility")):
                for url, label in utility_items:
                    st.page_link(url, label=label)

        # ── Logout ────────────────────────────────────────────
        st.page_link(page_url.logout_url, label="🏃 Logout")