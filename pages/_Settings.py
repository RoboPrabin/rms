from db import db
from time import sleep
import streamlit as st
import pandas as pd
import sqlalchemy
import io
from utils import page_url
from utils.helper import camel_to_title, format_with_comma, hide_components, get_holding_engine
from utils import helper
import app_state
import navigation


class Settings:
    def __init__(self):
        # st.set_page_config(page_title="Dashboard")
        st.set_page_config(page_title=f"Settings |",page_icon="⚙️",layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()

        
        navigation.render_sidebar() 
        self.df: pd.DataFrame = None

    
    def header(self):
        st.title("⚙️ Settings", anchor=False)


    def change_password(self):
        # STEP 1: Handle incoming clear-flag before showing the form
        if st.session_state.get("clear_password_form"):
            st.session_state.current_password = ""
            st.session_state.new_password = ""
            st.session_state.confirm_password = ""
            st.session_state.clear_password_form = False

        st.subheader("Change App Password", anchor=False)

        with st.form("change_password_form"):
            current_password = st.text_input(
                "Current Password",
                type="password",
                key="current_password",
            )
            new_password = st.text_input(
                "New Password",
                type="password",
                key="new_password",
            )
            confirm_password = st.text_input(
                "Confirm New Password",
                type="password",
                key="confirm_password",
            )



            submitted = st.form_submit_button("Change Password")
            msg = st.empty()   # placeholder for success/error messages
            if submitted:    
                # Basic validations
                if not current_password or not new_password or not confirm_password:
                    msg.warning("‎‎‎‎‎‎  All fields are required.", icon="⚠️")
                elif not helper.is_valid_password(new_password):
                    msg.error("Password must be at least 6 characters long and include 1 capital letter, 1 digit, and 1 symbol.", icon="❌")
                elif new_password != confirm_password:
                    msg.error("‎‎‎‎‎‎ New and Confirm password do not match.", icon="❌")
                else:
                    # Backend: verify + update password
                    success = db.change_password(
                        username=self.username,
                        current_password=current_password,
                        new_password=new_password
                    )

                    if not success:
                        msg.error("Current password is incorrect.")
                    else:
                        msg.success("Password changed successfully.")
                        st.balloons()

                        # Clear the form fields in the next rerun
                        st.session_state.clear_password_form = True

                        sleep(1.6)
                        msg.empty()
                        st.rerun()




    def render_dashboard(self):
        self.header()
        self.change_password()
        
        # _self.hide_download_csv_button()



if __name__ == "__main__":
    dashboad = Settings()
    dashboad.render_dashboard()
    


    