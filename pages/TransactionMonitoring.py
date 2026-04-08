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
from utils import auth_utils, helper
from datetime import datetime, timedelta
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config
from db import db
import requests
from pages.BasePage import BasePage


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




class TransactionMonitoring(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "aml"
        activate_client_code_hotkey()
        st.set_page_config("AML - Transaction Monitoring", page_icon="🕵🏻", layout='wide')
        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()
        # user = auth_utils.ensure_logged_in()
        # self.username= user['username']
        # self.role= user['role']
        # self.branch = user['branch']
        navigation.render_sidebar()
        # DB
        self.holding_engine = helper.get_holding_engine()
        st.header("🕵🏻 AML - Transaction Monitoring", anchor=False)

    @st.dialog("🔄 Update Client Details", width='medium')
    def show_dialog(self):
        col1, col2 = st.columns(2)
        with col1:
            client_code = st.text_input(
                "Client Code",
                value=st.session_state.dialog_client_code,
                disabled=True
            ).upper()

            company = st.text_input(
                "Company",
                value=st.session_state.dialog_company
            ).upper()

        with col2:
            client_name = st.text_input(
                "Client Name",
                value=st.session_state.dialog_client_name
            ).upper()

            occupation = st.text_input(
                "Occupation",
                value=st.session_state.dialog_occupation
            ).upper()

        if st.button("Update info", icon="🔄"):
            # Compare current input values with original session state values
            changed = (
                company != st.session_state.dialog_company or
                client_name != st.session_state.dialog_client_name or
                occupation != st.session_state.dialog_occupation
            )

            info_banner = st.empty()

            if changed:
                # Only update DB if something changed
                db.update_client_info_aml(
                    client_name=client_name,
                    company=company,
                    occupation=occupation,
                    updated_by=self.username,
                    client_code=client_code.strip()
                )
                info_banner.success("Updated successfully ✅")
                sleep(0.5)
            else:
                info_banner.info("No changes detected — Database not updated.", icon="📌")
                sleep(2)
            info_banner.empty()


            # try:
            #     # Clear session state so dialog disappears
            #     for key in [
            #         'dialog_client_code', 'dialog_company',
            #         'dialog_client_name', 'dialog_occupation',
            #         'show_dialog_flag'
            #     ]:
            #         st.session_state.pop(key, None)
            # except Exception as e:
            #     pass


    def populate_traders_info(self):
        # ─── Session flags ────────────────────────────────────────
        if 'fetch_done' not in st.session_state:
            st.session_state.fetch_done = False

        if 'submit_done' not in st.session_state:
            st.session_state.submit_done = False

        # ─── Init data only once ──────────────────────────────────
        if 'trader_df' not in st.session_state:
            df = db.get_unique_client_code_from_floorsheet()
            if df.empty:
                st.info("No new records yet.", icon="ℹ️")
                st.stop()
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
    
    

    def data_entry(self):
        
        if 'aml_data' not in st.session_state:
            st.session_state.aml_data = db.get_aml_transaction_data()
            st.session_state.count = len(st.session_state.aml_data)
        if 'scripts' not in st.session_state:
            df_scripts = db.get_scripts()
            st.session_state.scripts = (df_scripts['symbol'] + " - " + df_scripts['securityName']).tolist()

        if 'client_options' not in st.session_state:
            df = st.session_state.aml_data

            if df.empty:
                st.info("Data not found.", icon="ℹ️")
                st.stop()

            # Vectorized (fast) — no iterrows
            st.session_state.client_options = (
                df['client_code'].astype(str)
                + " - "
                + df['client_name'].astype(str)
                + " - "
                + df['company'].astype(str)
            ).tolist()

            # Map for instant lookup
            st.session_state.client_map = dict(
                zip(st.session_state.client_options, df.index)
            )

        st.badge(f"Total Traders Count: {st.session_state.count:,.2f}")
        col1, col2 = st.columns(2)
        if 'selected_client' not in st.session_state:
            st.session_state.selected_client = ''
        with col1:
            selected_client = st.selectbox("Select Client", ['None'] + st.session_state.client_options)
        with col2:
            if selected_client != 'None':
                client_code = str(selected_client.split("-")[0].strip())

                # Only set default once per client selection
                if "restricted_scripts" not in st.session_state or st.session_state.selected_client != selected_client:
                    st.session_state.restricted_scripts = db.get_restricted_scripts(client_code)
                    st.session_state.selected_client = selected_client  # track current client
            if selected_client != 'None':
                restricted_scripts = st.multiselect(
                    "Restrict Scripts",
                    st.session_state.scripts,
                    key="restricted_scripts",
                    accept_new_options=True
                )

        if st.button("Restrict now !", icon="🚫"):
            symbols = [item.split(" - ", 1)[0] for item in restricted_scripts]
            if len(symbols) == 0:
                symbols = None
            selected_client = str(selected_client.split("-")[0].strip())
            db.update_restrict_company(client_code=selected_client, updated_by=self.username, restrict_company=symbols)
            st.success("Data updated successfully.", icon="✅")
            sleep(1)
            st.rerun()
    

    def view_restrictions_clients(self):
       
        if 'view_data' not in st.session_state:
            st.session_state.view_data = db.get_aml_transaction_data()
        df = st.session_state.view_data
        df.rename(columns={'client_code':'Client Code', 'client_name': 'Client Name', 
                           'occupation': 'Occupation', 'company':'Company', 
                           'restrict_company':'Restrict Company', 'flag':'Flag'}, inplace=True)
        df.reset_index(inplace=True, drop=True)
        df.index = df.index + 1
        st.badge(f"Total Count: {len(df):,.2f}")
        try:
            df.drop(columns=['Flag'], inplace=True)
        except Exception as e:
            pass
        selection = st.dataframe(st.session_state.view_data, key='view_restriction', selection_mode='single-row', on_select='rerun')
        selection = st.session_state.get("view_restriction", {}).get("selection", {})
        selected_rows = selection.get("rows", [])

        if selected_rows:
            selected_index = selected_rows[0]

            # Fetch raw row (zero-based index)
            selected_row = df.iloc[selected_index].to_dict()
            if len(selected_row)>0:
                # Store values in session state
                st.session_state.dialog_client_code = selected_row['Client Code']
                st.session_state.dialog_company = selected_row.get('Company') or ""
                st.session_state.dialog_client_name = selected_row.get('Client Name') or ""
                st.session_state.dialog_occupation = selected_row.get('Occupation') or ""
                self.show_dialog()

    def show_reports(self):
        try:
            del st.session_state.restrict_script
        except Exception:
            pass
        banner = None
        has_load_button_clicked = False
        with st.expander("Show Date Range", icon="ℹ️"):
            with st.form("Load data", clear_on_submit=False):
                st.caption("*Note: This section loads the floorsheet data of provied data range.")
                col1, col2 = st.columns(2)
                with col1:
                    from_date = st.date_input(label="From Date")
                with col2:
                    to_date = st.date_input(label="To Date")
                submit_btn = st.form_submit_button("Load data")
                if submit_btn:
                    banner = st.empty()
                    has_load_button_clicked = True
                    banner.info("Loading floorsheet. Please wait...", icon="ℹ️")


        # Cache restriction scripts once
        if 'restrict_script' not in st.session_state:
            st.session_state.restrict_script = db.get_clients_with_restriction_scripts()  # has client_code, restrict_company

        # Always refresh floorsheet when date changes
        st.session_state.aml_floorsheet = db.get_floorsheet_range_aml(
            from_selected_date=from_date,
            to_selected_date=to_date
        )


        # Assign local variables
        df_restrict_scripts = st.session_state.restrict_script.copy()
        df_floorsheet = st.session_state.aml_floorsheet.copy()

        # Normalize column names
        df_floorsheet = df_floorsheet.rename(columns={"clientcode": "client_code"})

        # Split restrict_company into lists
        df_restrict_scripts["restrict_list"] = df_restrict_scripts["restrict_company"].str.split(",")

        # Strip whitespace and uppercase for consistency
        df_restrict_scripts["restrict_list"] = df_restrict_scripts["restrict_list"].apply(
            lambda lst: [s.strip().upper() for s in lst] if isinstance(lst, list) else []
        )
        df_floorsheet["symbol"] = df_floorsheet["symbol"].str.upper()
        # Format to 12-hour with seconds and date
        df_floorsheet["tradetime"] = pd.to_datetime(df_floorsheet["tradetime"], errors='coerce')
        df_floorsheet["tradetime"] = df_floorsheet["tradetime"].dt.strftime("%d-%b-%Y %I:%M:%S %p")
        # Build trade time mapping per client + symbol
        # Build FIRST trade-time mapping per client + symbol
        trade_time_map = (
            df_floorsheet
            .sort_values("tradetime")  # ensure chronological order
            .drop_duplicates(subset=["client_code", "symbol"], keep="first")
            .set_index(["client_code", "symbol"])["tradetime"]
            .to_dict()
        )

        # Check if traded restricted symbols
        def check_restricted(row):
            client_trades = df_floorsheet[df_floorsheet["client_code"] == row["client_code"]]["symbol"].tolist()
            return list(set(client_trades) & set(row["restrict_list"]))  # intersection

        df_restrict_scripts["violated_symbols"] = df_restrict_scripts.apply(check_restricted, axis=1)

        # Filter only violators
        df_violations = df_restrict_scripts[
            df_restrict_scripts["violated_symbols"].map(len) > 0
        ].copy()

        df_violations["violated_symbols"] = df_violations["violated_symbols"].apply(
            lambda x: list(x) if isinstance(x, (list, set, tuple)) else []
        )


        trade_days_col = []
        for _, row in df_violations.iterrows():
            trade_days = []
            for symbol in row["violated_symbols"]:
                key = (row["client_code"], symbol)
                if key in trade_time_map:
                    trade_days.append(f"{symbol} ({trade_time_map[key]})")
            trade_days_col.append(trade_days)
        df_violations["Trade Day"] = trade_days_col




        # Drop original restrict_company column (since we now have restrict_list + violated_symbols)
        df_restrict_scripts.drop(columns=['restrict_company'], inplace=True)

        # Show results
        if len(df_violations) > 0:
            st.subheader("🚨 Found Violation", anchor=False)
            df_violations.reset_index(drop=True, inplace=True)
            df_violations.index = df_violations.index + 1
            df_violations.rename(columns={'client_code':'Client Code', 
                                          'client_name':'Client Name', 
                                          'restrict_company':'Restrict Company',
                                          'restrict_list': 'Restrict Scripts',
                                          'violated_symbols': 'Violated Scripts', 
                                          'company':'Workplace'}, inplace=True)
            df_violations.drop(columns=['Restrict Company'], inplace=True)
            st.badge(f"Total Violation: {len(df_violations)}", color='red')
            st.dataframe(df_violations)
            st.divider()
        if len(df_violations)<=0:
            st.info(f"Violation not found. \n\nTotal transactions on selected date range: {len(st.session_state.aml_floorsheet)}.",icon="📢")
            st.divider()

        st.subheader("🚫 Restriction List", anchor=False)
        df_restrict_scripts.reset_index(drop=True, inplace=True)
        df_restrict_scripts.index = df_restrict_scripts.index + 1
        df_restrict_scripts.rename(columns={'client_code':'Client Code', 
                                          'client_name':'Client Name', 
                                          'restrict_company':'Restrict Company',
                                          'restrict_list': 'Restrict List',
                                          'violated_symbols': 'Violated Script', 'company':'Company'}, inplace=True)
        st.badge(f"Total Restrictions Clients: {len(df_restrict_scripts)}", color='blue')
        st.dataframe(df_restrict_scripts)
        if has_load_button_clicked:
            banner.success("Data fetched successfully.", icon="✅")
            sleep(1)
            banner.empty()
            st.session_state.restrict = False


    def render_page(self):
        if self.role == "BRO":
            mode = st.radio(
                "Mode",
                ['Data Entry',  'View All Restrictions'],
                horizontal=True,
                index=0
            )
        else:
            mode = st.radio(
                "Mode",
                ['Data Entry', 'Populate Traders Info', 'View All Restrictions', 'Reports'],
                horizontal=True,
                index=0
            )


        if mode == "Data Entry":
            self.data_entry()
        elif mode == 'Populate Traders Info':
            self.populate_traders_info()
        elif mode == "View All Restrictions":
            self.view_restrictions_clients()
        elif mode == "Reports":
            self.show_reports()


       




if __name__ == "__main__":
    TransactionMonitoring().render_page()    