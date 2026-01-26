from utils.custom_hotkey import activate_client_code_hotkey
from time import sleep
import secrets
import string
from utils.mailer import *

from db import db
from nepali_datetime import date as nepali_date
from datetime import date

import numpy as np
import streamlit as st
import pandas as pd
from utils import helper
from datetime import datetime, timedelta
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config
from db import db
import requests


# ---------------- API HELPERS ----------------
def get_token(username=config.dg_api_userName, password=config.dg_api_password):
    resp = requests.post(
        config.LOGIN_API,
        json={"userName": username, "password": password},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json().get("token")


def get_accode(nepse_code, token):
    resp = requests.get(
        config.AC_CODE_API,
        headers={"Authorization": f"Bearer {token}"},
        params={"nepseCode": nepse_code},
        timeout=30
    )
    resp.raise_for_status()
    return resp.text

def get_kyc_details(ac_code, token):
    resp = requests.get(
        config.KYC_API,
        headers={"Authorization": f"Bearer {token}"},
        params={"acCode": ac_code},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()


class TransactionMonitoring:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "aml"
        activate_client_code_hotkey()

        st.set_page_config("AML - Transaction Monitoring", page_icon="🕵🏻", layout='wide')

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()

        # Authentication
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role, self.branch = app_state.get_current_user_info()
        navigation.render_sidebar()


        # DB
        self.holding_engine = helper.get_holding_engine()

        st.header("🕵🏻 AML - Transaction Monitoring", anchor=False)
        st.header("⚠️ Page under construction", anchor=False)


    def render_page(self):
        mode = st.radio(
            "Mode",
            ['Traders Info', 'Populate Traders Info'],
            horizontal=True,
            index=1
        )

        if mode != 'Populate Traders Info':
            return

        # ─── Session flags ────────────────────────────────────────
        if 'fetch_done' not in st.session_state:
            st.session_state.fetch_done = False

        if 'submit_done' not in st.session_state:
            st.session_state.submit_done = False

        # ─── Init data only once ──────────────────────────────────
        if 'trader_df' not in st.session_state:
            df = db.get_unique_client_code_from_floorsheet()
            df.rename(columns={'clientcode': 'Client Code'}, inplace=True)
            # After creating/renaming df
            df.columns = [str(col) for col in df.columns]
            df['Client Name'] = ''
            df['Occupation'] = ''
            df['Company'] = ''
            df.index = df.index + 1
            st.session_state.trader_df = df

        df = st.session_state.trader_df

        # ─── UI containers ────────────────────────────────────────
        badge_placeholder   = st.empty()
        table_placeholder   = st.empty()
        progress_placeholder = st.empty()
        button_container    = st.empty()

        def render_kpis():
            total     = len(df)
            completed = df['Client Name'].astype(str).str.strip().ne('').sum()
            remaining = total - completed

            badge_placeholder.empty()
            with badge_placeholder.container():
                col1, col2, col3, _ = st.columns([1,1,1,4])
                col1.badge(f"Total: {total:,}", color='blue')
                col2.badge(f"Completed: {completed:,}", color='green')
                col3.badge(f"Remaining: {remaining:,}", color='red')

            return completed, remaining, total

        # ─── Already submitted ────────────────────────────────────
        if st.session_state.submit_done:
            st.success("Data submitted successfully ✓")
            st.info("Go to 'Traders Info' tab to start working.")
            # if st.button("Start new population"):
            #     for k in ['trader_df', 'fetch_done', 'submit_done']:
            #         if k in st.session_state:
            #             del st.session_state[k]
            #     st.rerun()
            return

        # ─── Already fetched, waiting for submit ──────────────────
        if st.session_state.fetch_done:
            render_kpis()
            table_placeholder.dataframe(df)
            st.badge(f"Note: {len(df)} data is ready to be saved in database.", color='orange')
            if button_container.button("ᯓ➤ Submit to Database"):
                with st.spinner("Inserting..."):
                    inserted, skipped = db.insert_aml_transactions_bulk(df, created_by=self.username)
                st.session_state.submit_done = True
                st.success(f"Inserted {inserted}, skipped {skipped} (already exist)")
                sleep(2)
                st.rerun()   # → shows final success screen
            return

        # ─── Normal flow: show fetch button ───────────────────────
        render_kpis()
        table_placeholder.dataframe(df)

        if button_container.button("Start fetching info", icon="🧲"):
            button_container.button("Processing...", icon="⏳", disabled=True)

            # token = db.get_jwt_token()
            token = get_token()
            completed, _, total = render_kpis()
            progress = progress_placeholder.progress(0)

            for idx, row in df.iterrows():
                if str(row['Client Name']).strip():
                    continue

                nepse_code = str(row['Client Code']).upper()
                accode = get_accode(nepse_code=nepse_code, token=token)
                response = get_kyc_details(ac_code=accode, token=token)

                name = response.get('client', {}).get('clientName', '')
                occ = None
                comp = None

                occ_list = response.get('occupation', [])
                if occ_list and isinstance(occ_list, list):
                    o = occ_list[0]
                    occ  = o.get('occupation', None)
                    comp = o.get('organizationName', None)

                df.loc[idx, 'Client Name'] = name
                df.loc[idx, 'Occupation']  = occ
                df.loc[idx, 'Company']     = comp

                table_placeholder.dataframe(df)
                completed, _, _ = render_kpis()
                progress.progress(completed / total if total > 0 else 0)

            progress_placeholder.empty()
            st.session_state.fetch_done = True
            st.success("Fetch completed ✓ Ready to submit.")
            sleep(1)
            st.rerun()   # → switches to submit view




if __name__ == "__main__":
    TransactionMonitoring().render_page()    