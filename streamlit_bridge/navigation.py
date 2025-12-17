# navigation.py
import streamlit as st
# from app_state import is_logged_in, current_user, logout_user
import streamlit_bridge.app_state as app_state
from utils import page_url

def render_sidebar():
    """
    Renders the sidebar menus based on login state and role.
    """
    app_state.restore_state_from_query_params()
    app_state.sync_query_params_from_session()
    app_state.check_authenticaiton_state()
    username, role = app_state.get_current_user_info()

    st.markdown("""
        <style>
            [data-testid="stSidebarCollapseButton"] {
                visibility: visible !important;
                opacity: 1 !important;
            }
        </style>
        """, unsafe_allow_html=True)
    st.markdown("""
        <style>
        /* Remove top gap */
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }

        /* Also remove padding inside sidebar content wrapper */
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        </style>
        """, unsafe_allow_html=True)

    st.sidebar.markdown(
            f"""
        <style>
        /* Container */
        .circle-wrapper {{
            position: relative;
            width: 140px;
            height: 140px;
            margin: 0 auto;
            margin-top: -30px !important;

        }}

        /* Rotating Border */
        .circle-wrapper::before {{
            content: "";
            position: absolute;
            top: -3px;
            left: -3px;
            width: 146px;
            height: 146px;
            border-radius: 50%;
            padding: 3px;
            background: conic-gradient(#9e9b9e, #15522c ,#04b347);
            -webkit-mask: 
                radial-gradient(farthest-side, transparent calc(100% - 3px), black 0);
            mask: 
                radial-gradient(farthest-side, transparent calc(100% - 3px), black 0);
            animation: spin 3s linear infinite;
            z-index: 0;
        }}

        /* Actual Image */
        .circle-img {{
            width: 140px;
            height: 140px;
            border-radius: 50%;
            overflow: hidden;
            position: relative;
            z-index: 2;
        }}

        @keyframes spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}
        </style>

        <div style='text-align:center; padding: 20px 0 10px 0;'>
            <div class="circle-wrapper">
                <div class="circle-img">
                    <img src='https://trishakti.com.np/img/logo1.png' 
                        width='110' 
                        style='border-radius: 50%; display: block;margin-top:30px; margin-left:15px;' />
                </div>
            </div>
        </div>

        <div style='text-align:center; margin:15px 0 25px; color:#444;'>
            <div style='font-size:14px;font-weight: bold; color:#a6a6a6; margin-top:0px;'> 
                <span style=''>{username.upper()}</span> | {role.upper()}
            </div>
        </div>

        <hr style='margin: 10px 0 20px 0; border:0; border-top:1px solid #eee;'>
        """,
            unsafe_allow_html=True
        )
    
    # Not in use for some period
    # st.sidebar.page_link(page_url.live_holdings_url, label="‎‎ ‎ Live Holdings", icon="🔴")
    # st.sidebar.page_link(page_url.manager_summary_url, label="‎‎ ‎ Manager Summary", icon="👨‍💼")
    # st.sidebar.page_link(page_url.client_summary_url, label="‎‎ ‎ Client Summary", icon="📃")

    # Authenticated menus
    if role == "USER":
        st.sidebar.page_link(page_url.book_closure_url, label="‎‎ ‎ Book Closure", icon="📫")
        st.sidebar.page_link(page_url.profile_url, label="‎‎ ‎ Profile", icon="💼")
        st.sidebar.page_link(page_url.logout_url, label="‎‎ ‎ Logout", icon="🏃")

    if role == "ADMIN":
        st.sidebar.page_link(page_url.dashbord_url, label="‎‎ ‎ Dashboard", icon="🏠")
        st.sidebar.page_link(page_url.automation_url, label="‎‎ ‎ Automations", icon="🤖")
        st.sidebar.page_link(page_url.bro_targets_and_achievements_url, label="‎‎ ‎ RM Targets & Achievements", icon="🎯")
        st.sidebar.page_link(page_url.live_rm_performance_url, label="‎‎ ‎ Live RM Performance", icon="🟢")
        st.sidebar.page_link(page_url.business_ratio_url, label="‎‎ ‎ Business Ratio", icon="⚖️")
        st.sidebar.page_link(page_url.floorsheet_url, label="‎‎ ‎ Floorsheet", icon="📄")
        st.sidebar.page_link(page_url.rm_tag_url, label="‎‎ ‎ RM Tag", icon="🏷️")
        st.sidebar.page_link(page_url.due_list_url, label="‎‎ ‎ Due List", icon="📋")
        st.sidebar.page_link(page_url.digital_url, label="‎‎ ‎ Digital Vault", icon="🔐")
        st.sidebar.page_link(page_url.book_closure_url, label="‎‎ ‎ Book Closure", icon="📫")
        st.sidebar.page_link(page_url.dpm_3_url, label="‎‎ ‎ DPM3", icon="📦")
        st.sidebar.page_link(page_url.uarf_url, label="‎‎ ‎ UARF", icon="🪪")
        st.sidebar.page_link(page_url.meroshare_url, label="‎‎ ‎ Meroshare", icon="📝")
        st.sidebar.page_link(page_url.bro_limit_url, label="‎‎ ‎ RM Limit", icon="🧑")
        st.sidebar.page_link(page_url.create_app_user_url, label="‎‎ ‎ Create App user", icon="➕")
        st.sidebar.page_link(page_url.communication_report_url, label="‎‎ ‎ Communication Report", icon="📢")
        st.sidebar.page_link(page_url.project_request_url, label="‎‎ ‎ Project Request", icon="🤝🏻")
        st.sidebar.page_link(page_url.profile_url, label="‎‎ ‎ Profile", icon="💼")
        st.sidebar.page_link(page_url.active_session_url, label="‎‎ ‎ Active Sessions", icon="🕓")
        st.sidebar.page_link(page_url.view_feedback_url, label="‎‎ ‎ View Feedback", icon="💬")
        st.sidebar.page_link(page_url.logout_url, label="‎‎ ‎ Logout", icon="🏃")
    
    if role in ["MANAGEMENT", "MANAGER"]:
        st.sidebar.page_link(page_url.dashbord_url, label="‎‎ ‎ Dashboard", icon="🏠")
        st.sidebar.page_link(page_url.bro_targets_and_achievements_url, label="‎‎ ‎ RM Targets & Achievements", icon="🎯")
        st.sidebar.page_link(page_url.live_rm_performance_url, label="‎‎ ‎ Live RM Performance", icon="🟢")
        st.sidebar.page_link(page_url.business_ratio_url, label="‎‎ ‎ Business Ratio", icon="⚖️")
        st.sidebar.page_link(page_url.floorsheet_url, label="‎‎ ‎ Floorsheet", icon="📄")
        st.sidebar.page_link(page_url.rm_tag_url, label="‎‎ ‎ RM Tag", icon="🏷️")
        st.sidebar.page_link(page_url.due_list_url, label="‎‎ ‎ Due List", icon="📋")
        st.sidebar.page_link(page_url.digital_url, label="‎‎ ‎ Digital Vault", icon="🔐")
        st.sidebar.page_link(page_url.book_closure_url, label="‎‎ ‎ Book Closure", icon="📫")
        st.sidebar.page_link(page_url.dpm_3_url, label="‎‎ ‎ DPM3", icon="📦")
        st.sidebar.page_link(page_url.uarf_url, label="‎‎ ‎ UARF", icon="🪪")
        st.sidebar.page_link(page_url.bro_limit_url, label="‎‎ ‎ RM Limit", icon="🧑")
        st.sidebar.page_link(page_url.meroshare_url, label="‎‎ ‎ Meroshare", icon="📝")
        st.sidebar.page_link(page_url.communication_report_url, label="‎‎ ‎ Communication Report", icon="📢")
        st.sidebar.page_link(page_url.project_request_url, label="‎‎ ‎ Project Request", icon="🤝🏻")
        st.sidebar.page_link(page_url.profile_url, label="‎‎ ‎ Profile", icon="💼")
        # st.sidebar.page_link(page_url.active_session_url, label="‎‎ ‎ Active Sessions", icon="🕓")
        st.sidebar.page_link(page_url.feedback_url, label="‎‎ ‎ Feedback", icon="💬")
        st.sidebar.page_link(page_url.logout_url, label="‎‎ ‎ Logout", icon="🏃")

    
    
    
    
    if role == "BRO":
        st.sidebar.page_link(page_url.dashbord_url, label="‎‎ ‎ Dashboard", icon="🏠")
        st.sidebar.page_link(page_url.bro_targets_and_achievements_url, label="‎‎ ‎ RM Targets & Achievements", icon="🎯")
        st.sidebar.page_link(page_url.live_rm_performance_url, label="‎‎ ‎ Live RM Performance", icon="🟢")
        st.sidebar.page_link(page_url.book_closure_url, label="‎‎ ‎ Book Closure", icon="📫")
        st.sidebar.page_link(page_url.bro_limit_url, label="‎‎ ‎ Client Limit", icon="🧑")
        st.sidebar.page_link(page_url.meroshare_url, label="‎‎ ‎ Meroshare", icon="📝")

        st.sidebar.page_link(page_url.due_list_url, label="‎‎ ‎ Due List", icon="📋")
        st.sidebar.page_link(page_url.rm_tag_url, label="‎‎ ‎ RM Tag", icon="🏷️")
        st.sidebar.page_link(page_url.communication_report_url, label="‎‎ ‎ Communication Report", icon="📢")
        st.sidebar.page_link(page_url.project_request_url, label="‎‎ ‎ Project Request", icon="🤝🏻")
        st.sidebar.page_link(page_url.digital_url, label="‎‎ ‎ Digital Vault", icon="🔐")
        st.sidebar.page_link(page_url.profile_url, label="‎‎ ‎ Profile", icon="💼")
        # st.sidebar.page_link(page_url.settings_url, label="‎‎ ‎ Settings", icon="⚙️")
        st.sidebar.page_link(page_url.feedback_url, label="‎‎ ‎ Feedback", icon="💬")
        st.sidebar.page_link(page_url.logout_url, label="‎‎ ‎ Logout", icon="🏃")

    
