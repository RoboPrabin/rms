from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import auth_utils, helper
import requests
from pages.BasePage import BasePage

class EDISCall(BasePage):
    def __init__(self):
        super().__init__()
        # helper.eliminate_top_padding()
        st.session_state.active_menu = "user"
        st.set_page_config(page_title="EDIS Call", page_icon="📞", layout="wide")
        # user = auth_utils.ensure_logged_in()
        # self.username= user['username']
        # self.role= user['role']
        # self.branch = user['branch']
        st.header("📞 EDIS CAll", anchor=False)

        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())
        self.session_ids = None


    def call_now(self):
        upload = st.file_uploader("Upload .csv file", type='.csv')

        if upload:
            if st.button("Upload now"):
                first_api = "http://10.98.100.48:8000/csv_upload.php"
                second_api = "http://10.98.100.48:8000/process_jobs.php"
                files = {'file': (upload.name, upload, 'text/csv')}
                try:
                    # First API call
                    response1 = requests.post(first_api, files=files)
                    st.success(f"First stage: {response1.json().get('message')}", icon="📢")
                    
                    # Show spinner while second API is processing
                    with st.spinner('Processing second stage, please wait... ⏳', show_time=True):
                        response2 = requests.post(second_api, files=files)
                    
                    # Once done, process the response
                    lines = response2.text.replace(".call", ".call\n").splitlines()
                    call_count = 0
                    for line in lines:
                        if line.strip():   # avoid empty lines
                            call_count += 1
                            st.write(f"{call_count}. {line}")

                    st.success(f"📞 Total call files created: {call_count}")

                except Exception as e:
                    st.error(f"Error uploading file: {e}")


if __name__ == "__main__":
    EDISCall().call_now()