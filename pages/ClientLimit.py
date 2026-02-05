from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import helper
from config.config import credentials_tms_for_collateral_only
from api.tms import api_collateral


def get_client_list():
    rows = db.get_table_rm_child_map_for_client_limit()
    df = pd.DataFrame(rows, columns=['BRO','BROFullName','Client Name', 'Client Code', 'Category'])
    return df





cookies, session_id = db.get_tms_session()

def get_headers(referer:str ='https://tms48.nepsetms.com.np/tms/member/search/client-search',):
    return {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'host-session-id': session_id,
        'origin': 'https://tms48.nepsetms.com.np',
        'priority': 'u=1, i',
        'referer': referer,
        'request-owner': credentials_tms_for_collateral_only['server_id'],
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'x-xsrf-token': cookies['XSRF-TOKEN'],

    }



class ClientLimit:
    def __init__(self):
        # helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        st.set_page_config(page_title="Client Limit", page_icon="💷", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role, self.branch = app_state.get_current_user_info()
        st.header("💷 Client Limit", anchor=False)

        render_sidebar()


    def reports(self):
        pass
    

    def tms_api(self, client_code, limit_amount):
        result = api_collateral.load_collateral_for_specific_client(headers=get_headers(), cookies=cookies, amount=limit_amount, 
            client_code=client_code, loaded_by=self.username.upper())
        if result == None:
            st.error(f"Something went wrong, contat IT Depart.", icon="🚨")
            return
        if result.lower() == "success":
            st.success(f"Client '{client_code}' with amount {limit_amount} updated successfully.", icon="✅")
        else:
            st.error(f"Something went wrong: {result}")
    
    def show_set_limit_ui(self, client):
        with st.expander(f"Set Limit on TMS: {client.upper()}", expanded=True):
            client_code = str(client).split("-")[0].strip()
            has_from_db = False
            category_from_db = db.get_category_client_rm_map(client_code=client_code)
            if category_from_db == None:
                set_category = helper.default_category_list()
            else:
                set_category = category_from_db
                has_from_db = True

            selected_category = st.selectbox("Category", set_category)


            if not has_from_db:
                if st.button("Update category", icon="🗂️"):
                    result = db.update_category_client_rm_map(client_code=client_code, new_category=selected_category)
                    if result == 1:
                        st.success(f"Category updated successfully.", icon="✅")
                        limit_amount = st.number_input("Credit For Sale Limit")
                        if st.button("Update Limit", icon="💷"):
                            self.tms_api(client_code=client_code, limit_amount=limit_amount)
            elif has_from_db:
                limit_amount = st.number_input("Credit For Sale Limit")
                if st.button("Update Limit", icon="💷"):
                    # HIT TMS API FOR CFS
                    self.tms_api(client_code=client_code, limit_amount=limit_amount)
    
    def limiter(self):
        if 'client_map' not in st.session_state:
            st.session_state.client_map = get_client_list()

        df = st.session_state.client_map

        # =====================
        # BRO DROPDOWN
        # =====================
        bro_map = (
            df[['BRO', 'BROFullName']]
            .drop_duplicates()
            .assign(display=lambda x: x['BRO'] + " - " + x['BROFullName'])
        )

        col1, col2 = st.columns(2)

        with col1:
            selected_bro = st.selectbox(
                "BRO",
                bro_map['BRO'],
                format_func=lambda bro: bro_map.loc[
                    bro_map['BRO'] == bro, 'display'
                ].values[0]
            )

        # =====================
        # FILTER CLIENTS BY BRO
        # =====================
        filtered_df = df[df['BRO'] == selected_bro]



        filtered_df = filtered_df.copy()

        filtered_df = filtered_df.sort_values(
            by="Client Name",
            ascending=True
        )

        filtered_df['Display'] = (
            filtered_df['Client Code'].astype(str)
            + " - "
            + filtered_df['Client Name']
        )

        options = filtered_df['Display'].tolist()


        st.badge(
            f"Total Mapped Clients: {len(filtered_df):,.0f}",
            color="green"
        )

        # =====================
        # CLIENT DROPDOWN
        # =====================
        with col2:
            selected_client = st.selectbox("Select Client", options)

        if selected_client != "None":
            self.show_set_limit_ui(client=selected_client)


    def render_page(self):
        mode = st.radio("Mode", ['Limiter', 'Reports'], horizontal=True)
        if mode == 'Limiter':
            self.limiter()
        elif mode == 'Reports':
            self.reports()



if __name__ == "__main__":
    ClientLimit().render_page()