from datetime import datetime, time, timedelta
from time import sleep
import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
from utils import auth_utils
from db import db
from pages.BasePage import BasePage


DOABLE_ACTIONS = ['None', 'BUY', 'SELL', 'FOLLOW-UP']


class ClientCommunication(BasePage):

    def __init__(self):
        super().__init__()
        st.session_state.active_menu = "rm"
        st.set_page_config(
            page_title="Client Communication",
            page_icon="📅",
            layout="wide"
        )

        # user = auth_utils.ensure_logged_in()
        # self.username = user.get('username')
        # self.role = user.get('role')
        # self.branch = user.get('branch')

        st.header("📅 Client Communication", anchor=False)
        render_sidebar()

        self._load_master_data()

    # -------------------------
    # Session-Level Data Loader
    # -------------------------

    def _load_master_data(self):
        """
        Session reuse, NOT caching.
        Loaded once per user session.
        """
        if "clients_df" not in st.session_state:
            rows = db.get_clients_by_rm_for_client_comm(rm_name='SAJAN')
            df = pd.DataFrame(rows, columns=['Client Code', 'Client Name'])
            df['display'] = df['Client Code'] + " - " + df['Client Name']
            df.sort_values(by="Client Name", inplace=True)
            st.session_state.clients_df = df

        if "scripts_df" not in st.session_state:
            df_scripts = db.get_scripts()
            df_scripts['display'] = (
                df_scripts['symbol'] + " - " + df_scripts['securityName']
            )
            st.session_state.scripts_df = df_scripts

    # -------------------------
    # Helpers
    # -------------------------

    @staticmethod
    def _split_display(value: str) -> tuple[str, str]:
        code, name = value.split("-", 1)
        return code.strip(), name.strip()

    @staticmethod
    def _format_time(t: time) -> str:
        return t.strftime("%I:%M %p")

    # -------------------------
    # Entry Mode
    # -------------------------

    def entry(self):
        df_clients = st.session_state.clients_df
        df_scripts = st.session_state.scripts_df

        action = st.selectbox("Action", DOABLE_ACTIONS)
        if action == 'None':
            return

        with st.container(border=True):

            col1, col2 = st.columns(2)
            with col1:
                selected_client = st.selectbox(
                    f"Select Client : {len(df_clients):,.0f}",
                    options=df_clients['display']
                )

            selected_script = None
            comm_date = None
            comm_time = None

            if action in ('BUY', 'SELL'):

                with col2:
                    selected_script = st.selectbox(
                        "Select Script",
                        options=df_scripts['display']
                    )

                with col1:
                    comm_date = st.date_input(
                        "Select Date",
                        value=datetime.now()
                    )
                with col2:
                    selected_time = st.slider(
                        "Select Time",
                        value=time(12, 0),
                        step=timedelta(minutes=1),
                        format="hh:mm A"
                    )
                    comm_time = self._format_time(selected_time)

            remarks = st.text_area("Remarks")

            if st.button("ᯓ➤ Submit"):
                self._handle_submit(
                    action=action,
                    client_display=selected_client,
                    script_display=selected_script,
                    comm_date=comm_date,
                    comm_time=comm_time,
                    remarks=remarks
                )

    # -------------------------
    # Submission Handler
    # -------------------------

    def _handle_submit(
        self,
        *,
        action: str,
        client_display: str,
        script_display: str | None,
        comm_date,
        comm_time,
        remarks: str
    ):
        if not self.username:
            st.error("Username not found. Contact IT.", icon="🚨")
            return

        if action == "FOLLOW-UP" and not remarks.strip():
            st.error("Please provide follow-up remarks.", icon="🚨")
            return

        client_code, client_name = self._split_display(client_display)
        script = (
            script_display.split("-")[0].strip()
            if script_display else None
        )

        db.insert_client_comm(
            client_code=client_code,
            client_name=client_name,
            comm_date=comm_date,
            comm_time=comm_time,
            script=script,
            remarks=remarks.strip(),
            action_type=action,
            created_by=self.username
        )

        st.success("Data submitted successfully.", icon="✅")
        sleep(0.4)
        st.rerun()

    # -------------------------
    # Reports Mode
    # -------------------------

    # def reports(self):
    #     if self.role == 'BRO':
    #         rows = db.get_client_comm_report_by_bro(self.username)
    #     else:
    #         rows = db.get_all_client_comm_report()

    #     if not rows:
    #         st.info("No communication records found.", icon="ℹ️")
    #         return

    #     df = pd.DataFrame(
    #         rows,
    #         columns=[
    #             'Client Code',
    #             'Client Name',
    #             'Script',
    #             'Date',
    #             'Time',
    #             'Action Type',
    #             'Remarks',
    #             'Created By'
    #         ]
    #     )

    #     df.index = df.index + 1
    #     st.badge(f"Total Communication: {len(df):,.0f}", color="green")
    #     st.dataframe(df, use_container_width=True)



    def reports(self):
        if self.role == 'BRO':
            rows = db.get_client_comm_report_by_bro(self.username)
        else:
            rows = db.get_all_client_comm_report()

        if not rows:
            st.info("No communication records found.", icon="ℹ️")
            return

        df = pd.DataFrame(
            rows,
            columns=[
                'Client Code',
                'Client Name',
                'Script',
                'Date',
                'Time',
                'Action Type',
                'Remarks',
                'Created By'
            ]
        )

        # -------------------------
        # Filters UI
        # -------------------------
        # with st.container(border=True):
        col1, col2 = st.columns(2)

        with col1:
            filter_type = st.selectbox(
                "Filter By",
                options=['None', 'Date', 'Client Code', 'Client Name', 'Action Type']
            )

        filtered_df = df.copy()

        if filter_type == 'Date':
            with col2:
                selected_date = st.date_input("Select Date")
            filtered_df = filtered_df[
                pd.to_datetime(filtered_df['Date']).dt.date == selected_date
            ]

        elif filter_type == 'Client Code':
            with col2:
                client_code = st.selectbox(
                    "Client Code",
                    options=sorted(filtered_df['Client Code'].unique())
                )
            filtered_df = filtered_df[
                filtered_df['Client Code'] == client_code
            ]

        elif filter_type == 'Client Name':
            with col2:
                client_name = st.selectbox(
                    "Client Name",
                    options=sorted(filtered_df['Client Name'].unique())
                )
            filtered_df = filtered_df[
                filtered_df['Client Name'] == client_name
            ]

        elif filter_type == 'Action Type':
            with col2:
                action_type = st.selectbox(
                    "Action Type",
                    options=sorted(filtered_df['Action Type'].unique())
                )
            filtered_df = filtered_df[
                filtered_df['Action Type'] == action_type
            ]

        # -------------------------
        # Report Output
        # -------------------------
        if filtered_df.empty:
            st.warning("No records found for selected filter.", icon="⚠️")
            return

        filtered_df = filtered_df.reset_index(drop=True)
        filtered_df.index = filtered_df.index + 1

        st.badge(
            f"Total Communication: {len(filtered_df):,.0f}",
            color="green"
        )

        st.dataframe(filtered_df, use_container_width=True)



    # -------------------------
    # Page Router
    # -------------------------

    def render_page(self):
        mode = st.radio("Mode", ['Entry', 'Reports'], horizontal=True)
        if mode == 'Entry':
            self.entry()
        else:
            self.reports()


if __name__ == "__main__":
    ClientCommunication().render_page()
