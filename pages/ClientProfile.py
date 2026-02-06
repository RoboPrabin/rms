from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import helper

class ClientRemarks:
    def __init__(self):
        # helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        st.set_page_config(page_title="Client Remarks", page_icon="🖊️", layout="wide")
        # app_state.restore_state_from_query_params()
        # app_state.sync_query_params_from_session()
        # app_state.check_authenticaiton_state()
        app_state.enforce_authentication()
        app_state.sync_local_storage_to_session()
        self.username, self.role, self.branch = app_state.get_current_user_info()
        st.header("🖊️ Client Remarks", anchor=False)

        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())
        self.session_ids = None

    def add_remarks(self):
        if 'client_remarks' not in st.session_state:
                st.session_state.client_remarks = db.get_kyc()
        rows = st.session_state.client_remarks
        df = pd.DataFrame(rows, columns=['Client Code', 'Client Name', 'Branch', 'Boid'])
        df.sort_values(by="Client Name", inplace=True)
        df['Display'] = df['Client Code'].astype(str) + " - " + df['Client Name'].astype(str)
        st.badge(f"Total Clients: {len(df):,.0f}")
        selected_client = st.selectbox("Select Client", [''] + df['Display'].tolist())
        remarks = st.text_area("Remarks")
        st.caption("*Note: Once remarks is added you cannot update or delete the records.")
        if st.button("Add Remarks", icon="🖊️"):
            if remarks.strip() == "":
                st.warning("Please provide remarks", icon="⚠️")
                return

            if len(remarks.strip()) < 6:
                st.warning("Remarks length must be greater than 6.", icon="⚠️")
                return
            client_code = str(selected_client).split("-")[0].strip()
            client_name = str(selected_client).split("-")[1].strip()
            banner = st.empty()
            db.insert_client_remark(client_code=client_code, client_name=client_name, remarks=remarks, created_by=self.username)
            banner.success("Remarks addedd successfully.", icon="✅")
            sleep(0.5)
            banner.empty()
    def render_page(self):
        mode = st.radio("Mode", ['Add Remarks', 'View Remarks'], horizontal=True)
        if mode == "Add Remarks":
            self.add_remarks()
        elif mode == "View Remarks":
            self.show_remarks()
        
    def show_remarks(self):
        # if 'view_remarks' not in st.session_state:
        rows = db.get_client_remarks()
        df = pd.DataFrame(rows, columns=['Client Code', 'Client Name', 'Remarks', 'Created At', 'Created By'])
        # st.session_state.view_remarks = df

        if df.empty:
            st.info("Records not found.", icon="ℹ️")
            return

        # df = st.session_state.view_remarks.copy()
        df.reset_index(drop=True, inplace=True)
        df.index = df.index + 1

        # Convert Created At to date only
        # Ensure Created At is a proper datetime
        df['Created At'] = pd.to_datetime(df['Created At'])

        # Extract just the date
        df['Created Date'] = df['Created At'].dt.date

        # Extract 12-hour time with AM/PM
        df['Created Time'] = df['Created At'].dt.strftime("%I:%M %p")

        # If you want a combined display column (date + time)
        df['Created DateTime'] = df['Created At'].dt.strftime("%Y-%m-%d %I:%M %p")

        col1, col2 = st.columns(2)
        with col1:
            filter_option = st.selectbox(
                "Filter by",
                options=[None, "Client Code", "Client Name", "Created By", "Created Date"],
                index=0,
                format_func=lambda x: "None" if x is None else x
            )

        with col2:
            if filter_option == "Client Code":
                client_code = st.text_input("Enter Client Code")
                if client_code.strip():
                    df = df[df['Client Code'].str.contains(client_code.strip(), case=False, na=False)]

            elif filter_option == "Client Name":
                client_name = st.text_input("Enter Client Name")
                if client_name.strip():
                    df = df[df['Client Name'].str.contains(client_name.strip(), case=False, na=False)]

            elif filter_option == "Created By":
                created_by_options = df['Created By'].dropna().unique().tolist()
                selected_creator = st.selectbox("Select Created By", options=created_by_options)
                if selected_creator:
                    df = df[df['Created By'] == selected_creator]

            elif filter_option == "Created Date":
                created_date_options = df['Created Date'].dropna().unique().tolist()
                selected_date = st.selectbox("Select Created Date", options=created_date_options)
                if selected_date:
                    df = df[df['Created Date'] == selected_date]

        # --- Display filtered dataframe ---
        df.drop(columns=['Created Date', 'Created Time', 'Created At'], inplace=True)
        st.dataframe(df, width="stretch")


if __name__ == "__main__":
    ClientRemarks().render_page()