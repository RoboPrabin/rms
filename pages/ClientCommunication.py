# from datetime import datetime, time, timedelta
# from time import sleep
# import pandas as pd
# import streamlit as st
# from streamlit_bridge.navigation import render_sidebar
# import streamlit_bridge.app_state as app_state
# from db import db
# from sqlalchemy import create_engine, text
# from utils import auth_utils, helper

# def get_doable():
#     return ['None', 'BUY', 'SELL', 'FOLLOW-UP']


# class ClientCommunication:
#     def __init__(self):
#         st.session_state.active_menu = "rm"
#         st.set_page_config(page_title="Client Communication", page_icon="📅", layout="wide")
#         user = auth_utils.ensure_logged_in()
#         self.username= user['username']
#         self.role= user['role']
#         self.branch = user['branch']
#         st.header(f"📅 Client Communication", anchor=False)
#         render_sidebar()


#     def entry(self):
#         rows = db.get_clients_by_rm_for_client_comm(rm_name='SAJAN')
#         # rows = db.get_clients_by_rm_for_client_comm(rm_name=self.username)
#         df = pd.DataFrame(rows, columns=['Client Code', 'Client Name'])
#         selected_action = st.selectbox("Action", get_doable())
#         if selected_action != 'None':
#             container = st.container(border=True)
#             dt = None
#             selected_time = None
#             script = None
#             remarks = None
#             with container:
#                 df['display'] = (df['Client Code'] + " - " + df['Client Name']).to_list() 
#                 df_scripts = db.get_scripts()
#                 df_scripts['scripts'] = (df_scripts['symbol'] + " - " + df_scripts['securityName']).to_list()
#                 df.sort_values(by="Client Name", inplace=True)
#                 if selected_action == 'FOLLOW-UP':
#                     selected_client = st.selectbox(f"Select Client : {len(df):,.0f}", options=df['display'])
#                 else:
#                     col1, col2 = st.columns(2)
#                     with col1:
#                         selected_client = st.selectbox(f"Select Client : {len(df):,.0f}", options=df['display'])
#                     with col2:
#                         selected_script = st.selectbox("Select Script", options=df_scripts['scripts'])
#                     # with col3:
                
#                 if selected_action == 'BUY' or selected_action == 'SELL':
#                     # ... inside your columns ...
#                     # with col4:
#                     # 1. Date Input
#                     col3, col4 = st.columns(2)
#                     with col3:
#                         dt = st.date_input(
#                             "Select Date", 
#                             value=datetime.now()
#                         )
                    
#                     with col4:
#                         selected_time = st.slider(
#                             "Select a time:",
#                             value=time(12, 0),
#                             format="hh:mm A", # 'TT' displays AM/PM
#                             step=timedelta(minutes=1)
#                         )
#                         selected_time = selected_time.strftime("%I:%M %p")

#                     script = str(selected_script).split("-")[0].strip()
#                 client_code = str(selected_client).split("-")[0].strip()
#                 client_name = str(selected_client).split("-")[1].strip()
#                 remarks = st.text_area("Remarks", value=None)

#                 if st.button("ᯓ➤ Submit"):
#                     if selected_action == "FOLLOW-UP" and remarks == "":
#                         st.error(f"Pleae provide follow up remarks", icon="🚨")
#                         st.stop()
#                     if self.username == None:
#                         st.error(f"Username not found. Contact IT", icon="🚨")
#                         st.stop()
#                     db.insert_client_comm(client_code=client_code, 
#                                           client_name=client_name, 
#                                           comm_date=dt, 
#                                           comm_time=selected_time, 
#                                           script=script, 
#                                           remarks=remarks, 
#                                           action_type=selected_action, 
#                                           created_by=self.username)
#                     st.success("Data submitted successfully.", icon="✅")
#                     sleep(0.5)
#                     st.rerun()


#     def reports(self):
#         if self.role == 'BRO':
#             rows = db.get_client_comm_report_by_bro(rm_name=self.username)
#             df = pd.DataFrame(rows, columns=['Client Code', 'Client Name', 'Script' ,'Date', 'Time', 'Action Type', 'Remarks','Created By'])
#         elif self.role in ['ADMIN', 'MANAGER', 'MANAGEMENT']:
#             rows = db.get_all_client_comm_report()
#             df = pd.DataFrame(rows, columns=['Client Code', 'Client Name', 'Script' ,'Date', 'Time', 'Action Type', 'Remarks','Created By'])
#         if len(df)==0:
#             st.info("No communication records found.", icon="ℹ️")
#             st.stop()
#         df.reset_index(inplace=True, drop=True)
#         df.index = df.index + 1
#         st.badge(f"Total Communication: {len(df):,.0f}", color='green' )
#         st.dataframe(df)
#     def render_page(self):
#         mode = st.radio("Mode", ['Entry', 'Reports'], horizontal=True)
#         if mode == 'Entry':
#             self.entry()
#         elif mode == 'Reports':
#             self.reports()
      

# if __name__ == "__main__":
#     ClientCommunication().render_page()



from datetime import datetime, time, timedelta
from time import sleep

import pandas as pd
import streamlit as st

from streamlit_bridge.navigation import render_sidebar
from utils import auth_utils
from db import db


DOABLE_ACTIONS = ['None', 'BUY', 'SELL', 'FOLLOW-UP']


class ClientCommunication:

    def __init__(self):
        st.session_state.active_menu = "rm"
        st.set_page_config(
            page_title="Client Communication",
            page_icon="📅",
            layout="wide"
        )

        user = auth_utils.ensure_logged_in()
        self.username = user.get('username')
        self.role = user.get('role')
        self.branch = user.get('branch')

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
