from db import db
from time import sleep
import streamlit as st
import pandas as pd
import sqlalchemy
import io
from utils import page_url
from utils.helper import camel_to_title, format_with_comma, hide_components, get_holding_engine
from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation


class Settings:
    def __init__(self):
        # st.set_page_config(page_title="Dashboard")
        st.set_page_config(page_title=f"Settings |",page_icon="⚙️",layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        self.user =db.get_user_by_username(username=self.username.lower())
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
                    email=email
                )
                st.success("Information updated successfully.")
                st.balloons()
                st.session_state.reset_toggle = True
                sleep(1.6)
                st.rerun()

           




    def render_dashboard(self):
        self.header()
        self.update_information()
        
        # _self.hide_download_csv_button()



if __name__ == "__main__":
    dashboad = Settings()
    dashboad.render_dashboard()
    


    