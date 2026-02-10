from datetime import datetime, time, timedelta
from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import auth_utils, helper

def get_doable():
    return ['None', 'BUY', 'SELL', 'FOLLOW-UP']


class ClientCommunication:
    def __init__(self):
        st.session_state.active_menu = ""
        st.set_page_config(page_title="Client Communication", page_icon="📅", layout="wide")
        user = auth_utils.ensure_logged_in()
        self.username= user['username']
        self.role= user['role']
        self.branch = user['branch']
        st.header("📅 Client Communication", anchor=False)
        render_sidebar()


    def entry(self):
        rows = db.get_clients_by_rm_for_client_comm(rm_name="SAJAN")
        df = pd.DataFrame(rows, columns=['Client Code', 'Client Name'])
        selected_action = st.selectbox("Action", get_doable())
        if selected_action != 'None':
            container = st.container(border=True)
            dt = None
            selected_time = None
            script = None
            remarks = None
            with container:
                df['display'] = (df['Client Code'] + " - " + df['Client Name']).to_list() 
                # st.badge(f"Total clients: {len(df):,.0f}", color='green')
                df_scripts = db.get_scripts()
                df_scripts['scripts'] = (df_scripts['symbol'] + " - " + df_scripts['securityName']).to_list()
                df.sort_values(by="Client Name", inplace=True)
                if selected_action == 'FOLLOW-UP':
                    selected_client = st.selectbox(f"Select Client : {len(df):,.0f}", options=df['display'])
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        selected_client = st.selectbox(f"Select Client : {len(df):,.0f}", options=df['display'])
                    with col2:
                        selected_script = st.selectbox("Select Script", options=df_scripts['scripts'])
                    # with col3:
                
                if selected_action == 'BUY' or selected_action == 'SELL':
                    # ... inside your columns ...
                    # with col4:
                    # 1. Date Input
                    col3, col4 = st.columns(2)
                    with col3:
                        dt = st.date_input(
                            "Select Date", 
                            value=datetime.now()
                        )
                    
                    with col4:
                        selected_time = st.slider(
                            "Select a time:",
                            value=time(12, 0),
                            format="hh:mm A", # 'TT' displays AM/PM
                            step=timedelta(minutes=1)
                        )
                        selected_time = selected_time.strftime("%I:%M %p")

                    script = str(selected_script).split("-")[0].strip()
                client_code = str(selected_client).split("-")[0].strip()
                client_name = str(selected_client).split("-")[1].strip()
                remarks = st.text_area("Remarks", value=None)

                if st.button("ᯓ➤ Submit"):
                    if selected_action == "FOLLOW-UP" and remarks == "":
                        st.error(f"Pleae provide follow up remarks", icon="🚨")
                        st.stop()
                    if self.username == None:
                        st.error(f"Username not found. Contact IT", icon="🚨")
                        st.stop()
                    db.insert_client_comm(client_code=client_code, 
                                          client_name=client_name, 
                                          comm_date=dt, 
                                          comm_time=selected_time, 
                                          script=script, 
                                          remarks=remarks, 
                                          action_type=selected_action, 
                                          created_by=self.username)
                    st.success("Data submitted successfully.", icon="✅")
                    sleep(0.5)
                    st.rerun()

    def render_page(self):
        
        mode = st.radio("Mode", ['Entry', 'Reports'], horizontal=True)
        if mode == 'Entry':
            self.entry()

      

if __name__ == "__main__":
    ClientCommunication().render_page()