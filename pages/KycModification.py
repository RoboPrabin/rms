import streamlit as st
import pandas as pd
from datetime import datetime
from time import sleep
from nepali_datetime import date as nepali_date

# Assuming these are your local modules
from db import db
from utils import auth_utils, helper
import streamlit_bridge.navigation as navigation
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage


class KycModification(BasePage):
    def __init__(self):
        super().__init__()
        # 1. Setup Page Config FIRST (Must be the first Streamlit command)
        st.set_page_config("Kyc Modification", page_icon="📚", layout='wide')
        
        helper.eliminate_top_padding()
        st.session_state.active_menu = "kyc"
        activate_client_code_hotkey()

        # 2. Optimized Data Loading (Cache the DB result in session state)
        if 'kyc_data' not in st.session_state:
            raw_data = db.get_kyc_with_rm()
            # Pre-process DataFrame once and store it
            df = pd.DataFrame(raw_data, columns=['Client Code', 'Client Name', 'Branch', 'BOID', 'BRO'])
            df.sort_values(by='Client Name', inplace=True)
            df['Branch'] = df['Branch'].str.upper()
            # Pre-calculate the selectbox label string to avoid doing it during every render
            df['display_label'] = df['Client Code'].astype(str) + " - " + df['Client Name'] + " - " + df['Branch']
            st.session_state.kyc_data = df

        # user = auth_utils.ensure_logged_in()
        # self.username = user['username']
        # self.role = user['role']
        # self.branch = user['branch']
        
        navigation.render_sidebar()
        st.header("📚 KYC Modification", anchor=False)


    def view_clients(self):
        df = st.session_state.kyc_data.copy()
        
        # 1. Total Count Badge

        # 2. Dynamic Branch Badges
        # We calculate counts once using vectorized pandas operations
        branch_counts = df['Branch'].value_counts().to_dict()
        container = st.container(border=True)
        with container:
            st.badge(f"Total Clients: {len(df):,.0f}", color='green')
            # Render badges in a scrolling or wrapped row using columns
            if branch_counts:
                cols = st.columns(len(branch_counts))
                for i, (branch, count) in enumerate(branch_counts.items()):
                    with cols[i]:
                        st.metric(label=branch, value=f"{count:,.0f}")
        

        # Calculate branch counts with In-DP / Out-DP split
        df['DP Type'] = df['BOID'].apply(lambda x: 'IN' if str(x).startswith('13011400') else 'OUT')

        branch_dp_counts = (
            df.groupby(['Branch', 'DP Type'])
            .size()
            .unstack(fill_value=0)
            .to_dict('index')
        )

        container = st.container(border=True)
        with container:
            col1, spacr, col2 = st.columns([1, 0.1, 6])
            with col1:
                st.badge(f"Total IN-DP: {len(df[df['DP Type'] == 'IN']):,.0f}", color='green')
            with col2:
                st.badge(f"Total OUT-DP: {len(df[df['DP Type'] == 'OUT']):,.0f}", color='red')
            if branch_dp_counts:
                cols = st.columns(len(branch_dp_counts))
                for i, (branch, counts) in enumerate(branch_dp_counts.items()):
                    with cols[i]:
                        in_dp = counts.get('IN', 0)
                        out_dp = counts.get('OUT', 0)
                        st.metric(label=f"{branch} (IN)", value=f"{in_dp:,}")
                        st.metric(label=f"{branch} (OUT)", value=f"{out_dp:,}")


        if st.toggle("Show Reference"):
            st.divider()

            # 3. Data Table
            df.sort_values(by="BRO", inplace=True)
            df.reset_index(inplace=True, drop=True)
            df.index = df.index + 1
            
            # st.badge(f"Total Clients: {len(df):,.0f}", color='green')
            st.dataframe(
                df.drop(columns=['display_label']), 
                width='stretch',
                column_config={
                    "BOID": st.column_config.TextColumn("BOID"), # Prevents commas in ID numbers
                    "Client Code": st.column_config.TextColumn("Client Code")
                }
            )


    def update_kyc(self):
        df = st.session_state.kyc_data
        # df.sort_values(by="Client Name", inplace=True)
        # 3. Fast lookup: selectbox uses the pre-calculated column
        selected_label = st.selectbox(
            "Select Client", 
            options=df['display_label'].values,
            index=None,
            placeholder="Search by Code, Name, or Branch..."
        )
        
        if selected_label:
            # Extract client code quickly from the string
            client_code = selected_label.split(" - ")[0]
            
            branch_options = ['NONE'] + sorted(df['Branch'].unique().tolist())
            selected_branch = st.selectbox("Update Branch", branch_options)
            
            if st.button("Update", icon="🔄️"):
                if selected_branch == 'NONE':
                    st.warning("Please select a valid branch", icon="⚠️")
                else:
                    db.update_kyc_branch(client_code=client_code, new_branch=selected_branch.title())
                    # 4. Clear cache so the next run gets fresh data
                    del st.session_state.kyc_data
                    st.success("Branch updated successfully.", icon="✅")
                    sleep(0.5)
                    st.rerun()
            
    def render_page(self):
        mode = st.radio("Mode", ['View Kyc', 'Update Branch'], horizontal=True, index=0)
        if mode == 'View Kyc':
            self.view_clients()
        elif mode == 'Update Branch':
            self.update_kyc()

if __name__ == "__main__":
    KycModification().render_page()