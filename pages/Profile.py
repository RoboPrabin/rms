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


class Profile(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "utility"
        st.set_page_config(page_title=f"Profile",page_icon="💼",layout="wide")
        # user = auth_utils.ensure_logged_in()
        # self.username= user['username']
        # self.role= user['role']
        # self.branch = user['branch']
        activate_client_code_hotkey()
        self.user =db.get_user_by_username(username=self.username)
        navigation.render_sidebar() 
        self.df: pd.DataFrame = None

    
    def header(self):
        st.title("💼 Profile", anchor=False)
        st.markdown("----")


    def update_information(self):
        if st.session_state.get("reset_toggle"):
            st.session_state.feature_toggle = False
            st.session_state.reset_toggle = False

        
        st.subheader("My Information", anchor=False)
        requested_change = False
        enable_feature = st.toggle(" ", key="feature_toggle")
        if enable_feature:
            requested_change = True

        with st.form("information_form"):
            username = st.text_input(
                "Username",
                key="current_password",
                value=self.username,
                disabled=True
            )
            role = st.text_input(
                "Role",
                # key="role",
                value=self.role,
                disabled=True
            )
            citizenship = st.text_input(
                "Citizenship",
                key="citizenship",
                value=self.user['citizenship'],
                disabled=not requested_change
            )
            password = st.text_input(
                "Password",
                type="password",
                key="password",
                value=self.user['password'],
                disabled=not requested_change
            )
            phone = st.text_input(
                "Phone",
                key="phone",
                value=self.user['phone'],
                disabled=not requested_change
            )
            email = st.text_input(
                "Email",
                key="email",
                value=self.user['email'],
                disabled=not requested_change
            )
            submitted = st.form_submit_button("Update Information", disabled=not requested_change)
            if submitted:
                db.change_user_info(
                    username=self.username,
                    password=password,
                    phone=phone,
                    email=email,
                    citizenship=citizenship
                )
                st.success("Information updated successfully.")
                st.balloons()
                st.session_state.reset_toggle = True
                sleep(0.8)
                st.rerun()

           




    def render_dashboard(self):
        self.header()
        self.update_information()
        
        # _self.hide_download_csv_button()



if __name__ == "__main__":
    dashboad = Profile()
    dashboad.render_dashboard()
    


    