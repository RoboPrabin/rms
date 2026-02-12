from db import db
from time import sleep
import streamlit as st
import pandas as pd
import sqlalchemy
import io
from utils import auth_utils, page_url
from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage

from db import profile_repo
class Profile(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin("-10rem")
        st.session_state.active_menu = "utility"
        st.set_page_config(page_title=f"Profile",page_icon="💼",layout="wide")
        activate_client_code_hotkey()
        if 'profile_user' not in st.session_state:
            st.session_state.profile_user = db.get_user_by_username(username=self.username)
        self.user =st.session_state.profile_user
        navigation.render_sidebar() 
        self.df: pd.DataFrame = None

    
    def header(self):
        st.title("💼 Profile", anchor=False)


    def setup_pin(self):
        st.subheader("Setup/Change PIN", anchor=False)

        # Disclaimer checkbox
        disclaimer = st.checkbox(
            "Disclaimer: Yes, I will be responsible if I lose my PIN or if it is misused.",
            key="pin_disclaimer"
        )
        btn = st.empty()
        # Only enable button if disclaimer is checked
        if btn.button("Generate new PIN", icon="🔄️", disabled=not disclaimer):
            new_pin = profile_repo.generate_pin()
            if new_pin:
                profile_repo.update_pin(username=st.session_state.username, new_pin=new_pin)
                st.success(f"Your Login PIN is: {new_pin}")
                st.info("Please note it down securely. It won't be shown again!", icon="⚠️")
                btn.empty()
            else:
                st.error("Failed to generate new PIN. Please try again later.", icon="❌")

        # st.info("This feature is coming soon! Stay tuned. 🚀", icon="⏳")

    def update_information(self):
        if st.session_state.get("reset_toggle"):
            st.session_state.feature_toggle = False
            st.session_state.reset_toggle = False

        requested_change = False
        enable_feature = st.toggle("Edit My Profile", key="feature_toggle")
        if enable_feature:
            requested_change = True

        with st.form("information_form"):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input(
                    "Username",
                    key="current_password",
                    value=self.username,
                    disabled=True
                )
            with col2:
                role = st.text_input(
                    "Role",
                    # key="role",
                    value=self.role,
                    disabled=True
                )
            with col1:
                password = st.text_input(
                    "Password",
                    type="password",
                    key="password",
                    value=self.user['password'],
                    disabled=not requested_change
                )
            with col2:
                citizenship = st.text_input(
                    "Citizenship",
                    key="citizenship",
                    value=self.user['citizenship'],
                    disabled=not requested_change
                )
            with col1:
                branch = st.text_input(
                    "Branch",
                    key="branch",
                    value=self.user['branch'],
                    disabled=not requested_change
                )
              
            with col2:
                phone = st.text_input(
                    "Phone",
                    key="phone",
                    value=self.user['phone'],
                    disabled=not requested_change
                )
            with col1:
                email = st.text_input(
                    "Email",
                    key="email",
                    value=self.user['email'],
                    disabled=not requested_change
                )
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Update Information", disabled=not requested_change, icon="🔄️")
            if submitted:
                result = db.change_user_info(
                    username=self.username,
                    password=password,
                    phone=phone,
                    email=email,
                    citizenship=citizenship
                )
                if result:
                    st.success("Information updated successfully.")
                    st.balloons()
                    st.session_state.reset_toggle = True
                    sleep(2)
                    st.rerun()

           




    def render_dashboard(self):
        self.header()
        tab1, tab2 = st.tabs(['Profile Info', "Change PIN"])
        with tab1:
             self.update_information()
        with tab2:
            self.setup_pin()



if __name__ == "__main__":

    dashboad = Profile()
    dashboad.render_dashboard()
    


    