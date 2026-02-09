from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import auth_utils, helper

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

    def render_page(self):
        mode = st.radio("Mode", ['Entry Mode', 'Reports'], horizontal=True, index=0)
        if mode == 'Entry Mode':
            self.entry_ui
        elif mode == 'Reports':
            self.reports_ui()
    
    def entry_ui(self):
        if 'clients' not in st.session_state:
            st.session_state.clients = db.get_clients_by_rm_for_client_comm(rm_name='SAJAN')
            df = pd.DataFrame(st.session_state.clients, columns=['Client Code', 'Client Name'])
        st.dataframe(df)


    def reports_ui(self):
        if 'clients' not in st.session_state:
            df = db.get_clients_by_rm_for_client_comm(rm_name='SAJAN')
            st.session_state.clients = pd.DataFrame(st.session_state.clients, columns=['Client Code', 'Client Name'])
        st.dataframe(st.session_state.clients)


if __name__ == "__main__":
    ClientCommunication().render_page()