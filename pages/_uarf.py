from time import sleep
from nepali_datetime import date as nepali_date
from datetime import date
from psycopg2.extras import execute_values

import numpy as np
import streamlit as st
import pandas as pd
from utils import helper
from datetime import datetime, timedelta
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config
from utils.custom_hotkey import activate_client_code_hotkey
from db import db
class Uarf:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "utility"
        st.set_page_config("UARF", page_icon="🪪", layout='wide')

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")

        self.today_np_date = nepali_date.today()
        today_np = nepali_date.today()


        activate_client_code_hotkey()
        # Authentication & User Info
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()

        # DB Connection
        self.holding_engine = helper.get_holding_engine()
        st.header("🪪 User Access Request Form", anchor=False)
    


    # MANAGER FUNCTION START ________________________________________
    @st.dialog("Confirmation")
    def confirm_manager(self, full_name, dob_bs, dob_ad, citizenship_number, citizenship_issued_place, personal_phone, personal_email, supervisor_name, selected_platforms, employee_type):
        st.badge("You cant't edit or delete once submitted.", color='red')
        st.write(f"Are you sure you want to submit UARF for **{full_name.title()}**?")
        if st.button("Submit"):
            db.submit_manager_request(
                    full_name,
                    dob_bs,
                    dob_ad,
                    citizenship_number,
                    citizenship_issued_place,
                    personal_phone,
                    personal_email,
                    supervisor_name,
                    selected_platforms,
                    employee_type,
                    self.username
                )
            st.success("✅ UARF submitted successfully and forwarded to HR.")
            sleep(1)
            st.rerun()

    def _get_manager_pending_requests(self):
        return pd.read_sql(F"""
            SELECT id, full_name, status, rejection_reason, created_at
            FROM uarf_request
            WHERE supervisor_name = '{self.username}'
            ORDER BY created_at;
        """, self.holding_engine)

    def manager_edit_form(self, uarf, df_access_platforms:pd.DataFrame):
        card = st.container(border=True)
        with card:
            st.text_area("Rejection reason:", value=uarf['rejection_reason'])
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                full_name = st.text_input("Full Name *", value=uarf["full_name"], key="edit_full_name")
                dob_ad = st.date_input("Date of Birth (AD) *", value=uarf["dob_ad"], key="edit_dob_ad")
                dob_bs = st.text_input("Date of Birth (BS) *", value=uarf["dob_bs"], key="edit_dob_bs")
            with col2:
                citizenship_number = st.text_input("Citizenship Number *", value=uarf["citizenship_number"])
                citizenship_issued_place = st.text_input("Citizenship Issued Place *", value=uarf["citizenship_issued_place"])
                employee_type = st.selectbox("Employee Type *", ["Select"] + helper.get_employee_types(), index=helper.get_employee_types().index(uarf["employee_type"]) + 1)
            with col3:
                personal_email = st.text_input("Personal Email *", value=uarf["personal_email"])
                personal_phone = st.text_input("Personal Phone *", value=uarf["personal_phone"])
                supervisor_name = st.text_input("Supervisor Name", value=uarf["supervisor_name"], disabled=True)


            platform_access_map = (
                df_access_platforms
                .set_index("platform_name")["access_required"]
                .to_dict()
            )
            platforms = helper.get_default_platforms()
            selected_platforms = {}
            cols = st.columns(4)
            for idx, platform in enumerate(platforms):
                with cols[idx % 4]:
                    selected_platforms[platform] = st.checkbox(
                            platform,
                            value=platform_access_map.get(platform, True),
                            # key=f"edit_platform_{platform}"
                        )

            submitted = st.button("📨 Resubmit UARF")

            if submitted:
                # call DB update logic
                db.update_manager_request(
                    uarf["id"],
                    full_name,
                    dob_bs,
                    dob_ad,
                    citizenship_number,
                    citizenship_issued_place,
                    personal_phone,
                    personal_email,
                    uarf["supervisor_name"],
                    selected_platforms,
                    employee_type
                )
                st.success("✅ UARF resubmitted successfully.")
                sleep(1)
                st.rerun()

    def manager_ui(self):
        view = st.radio("Select View", ["Submit UARF", "Pending/Approved", "Rejected"], horizontal=True, index=1)
        df = self._get_manager_pending_requests()
        # Normal pending/approved list
        normal_df = df[~df["status"].isin(["REJECTED_BY_HR", "REJECTED_BY_IT"])]
        rejected_df = df[df["status"].isin(["REJECTED_BY_HR", "REJECTED_BY_IT"])]

        if view == "Submit UARF":
            # with st.form("manager_uarf_form", clear_on_submit=True):
            card = st.container(border=True)
            with card:
                st.subheader("👔 Basic Information", anchor=False)
                col1, col2, col3 = st.columns(3)

                with col1:
                    full_name = st.text_input("Full Name *", key="full_name_input")
                    dob_ad = st.date_input("Date of Birth (AD) *", min_value=date(1920, 1, 1),max_value=date.today())
                    dob_bs = st.text_input("Date of Birth (BS) *",value=helper.convert_ad_to_bs(dob_ad.strftime("%Y-%m-%d")))

                with col2:
                    citizenship_number = st.text_input("Citizenship Number *")
                    citizenship_issued_place = st.text_input("Citizenship Issued Place *")
                    employee_type = st.selectbox("Employee Type *", ["Select"] + helper.get_employee_types())
                
                with col3:
                    personal_email = st.text_input("Personal Email *")
                    personal_phone = st.text_input("Personal Phone *")
                    supervisor_name = st.text_input("Supervisor Name",value=self.username,disabled=True)

                st.subheader("🔐 Platform Access Required", anchor=False)

                platforms = helper.get_default_platforms()
                selected_platforms = {}
                cols = st.columns(4)

                for idx, platform in enumerate(platforms):
                    with cols[idx % 4]:
                        selected_platforms[platform] = st.checkbox(platform)

                submitted = st.button("📨 Submit Request")

                if submitted:
                    required_fields = [
                        full_name,
                        dob_ad,
                        dob_bs,
                        citizenship_number,
                        citizenship_issued_place,
                        supervisor_name,
                        personal_email,
                        personal_phone,
                        employee_type != "Select"
                    ]

                    if not all(required_fields):
                        st.error("⚠️ Please fill all required fields.")
                        st.stop()
                        
                    if not any(selected_platforms.values()):
                        st.error("⚠️ Please select at least one platform before submitting.")
                        st.stop()

                    if not helper.validate_phone(personal_phone):
                        st.error("⚠️ Please enter a valid personal phone number (10 digits, starting with 9).")
                        st.stop()
                    if not helper.validate_email(personal_email):
                        st.error("⚠️ Please enter a valid personal email address.")
                        st.stop()
                    
                
                
                    self.confirm_manager(full_name,
                        dob_bs,
                        dob_ad,
                        citizenship_number,
                        citizenship_issued_place,
                        personal_phone,
                        personal_email,
                        supervisor_name,
                        selected_platforms,
                        employee_type
                        )
                
                # db.submit_manager_request(
                    # full_name,
                    # dob_bs,
                    # dob_ad,
                    # citizenship_number,
                    # citizenship_issued_place,
                    # personal_phone,
                    # personal_email,
                    # supervisor_name,
                    # selected_platforms,
                    # self.username
                # )
                # st.success("✅ UARF submitted successfully and forwarded to HR.")
                # sleep(1)
                # st.rerun()
        
        elif view == "Pending/Approved":
            if normal_df.empty and rejected_df.empty:
                st.info("You have no UARFs.", icon="📢")
                st.stop()

            if not normal_df.empty:
                st.subheader("Pending / Approved UARFs", anchor=False)
                normal_df.drop(columns=['id'], inplace=True)
                normal_df.rename(columns={"full_name":"Employee Name", 
                    "status": "Status", 
                    "created_at":"Requested At",
                    "rejection_reason":"Rejection Reason"}, inplace=True)
                normal_df.index = normal_df.index + 1
                st.dataframe(normal_df, width='stretch', hide_index=False)
        
        else:
           if rejected_df.empty:
               st.info("No rejection yet.", icon="📢")
               st.stop()

            # Show rejected UARFs separately
           if not rejected_df.empty:
                st.subheader("Rejected UARFs (Editable)", anchor=False)
                # Create display-only dataframe
                display_df = rejected_df.copy()

                display_df.rename(columns={
                    "full_name": "Employee Name",
                    "status": "Status",
                    "created_at": "Requested At",
                    "rejection_reason": "Rejection Reason"
                }, inplace=True)

                display_df.drop(columns=["id"], inplace=True)
                display_df.index = display_df.index + 1

                st.dataframe(display_df, width="stretch", hide_index=False)

                st.markdown("---")
                st.info("You can now edit the details and resubmit.", icon='📢')

                # Still use original rejected_df for logic
                selected_id = st.selectbox(
                    "Select a rejected UARF to edit",
                    rejected_df["id"],
                    format_func=lambda x: rejected_df.loc[
                        rejected_df["id"] == x, "full_name"
                    ].values[0]
                )

                uarf = self._get_uarf_details(selected_id)
                df_access_platforms = self.get_access_request_platforms(uarf_id=uarf["id"])

                self.manager_edit_form(uarf, df_access_platforms)


    def get_access_request_platforms(self, uarf_id):
        return pd.read_sql(F"""
            SELECT uarf_id, platform_name, access_required
            FROM uarf_platform_access
            WHERE uarf_id = '{uarf_id}'
            ORDER BY created_at;
        """, self.holding_engine)

    # HR FUNCTION START ________________________________________
    @st.dialog("Confirmation")
    def confirm_hr(self,  selected_id,
                    employee_id,
                    office_phone,
                    office_email,
                    department,
                    designation,
                    joining_date,
                    work_location):
        st.badge("You cant't edit or delete once submitted.", color='red')
        st.write(f"Are you sure you want to submit UARF to IT ?")
        if st.button("Submit"):
            if db.approve_by_hr(
                    selected_id,
                    employee_id,
                    office_phone,
                    office_email,
                    department,
                    designation,
                    joining_date,
                    work_location
                ):
                st.success("✅ UARF approved and forwarded to IT.")
                sleep(1)
                st.rerun()
                sleep(2)
                self.selected_index = 1
            else:
                st.error("❌ HR approval failed.")
    
    def _get_hr_pending_requests(self):
        return pd.read_sql("""
            SELECT id, full_name
            FROM uarf_request
            WHERE status = 'PENDING'
            ORDER BY created_at;
        """, self.holding_engine)

    def _get_uarf_details(self, uarf_id):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM uarf_request WHERE id = %s;", (uarf_id,))
        row = cur.fetchone()
        conn.close()
        return row

    def hr_ui(self):
        # st.subheader("🧑‍💼 HR Section", anchor=False)
        view = st.radio("Select View", ["View Pending Requests", "View All UARFs"], horizontal=True, index=0)
        if view == "View Pending Requests":
            # 1️⃣ Load pending UARFs
            df = self._get_hr_pending_requests()
            total_pending_request = len(df)
            if df.empty:
                st.info("No pending requests for HR.", icon="📢")
                return

            st.badge(f"Pending requests: {total_pending_request}", color='green')
            selected_id = st.selectbox(
                "Select Pending UARF",
                df["id"],
                format_func=lambda x: f"{df.loc[df['id'] == x, 'full_name'].values[0]}"
            )

            uarf = self._get_uarf_details(selected_id)

            card = st.container(border=True)
            
            with card:
                st.subheader("👔 Employee Details", anchor=False)
                st.caption("Employee details provided by Supervisor.")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.text_input("Full Name", uarf["full_name"], disabled=True)
                    st.date_input("DOB (AD)", uarf["dob_ad"], disabled=True)
                    st.text_input("DOB (BS)", uarf["dob_bs"], disabled=True)

                with col2:
                    st.text_input("Citizenship No", uarf["citizenship_number"], disabled=True)
                    st.text_input("Issued Place", uarf["citizenship_issued_place"], disabled=True)
                    st.selectbox("Employee Type *", uarf["employee_type"], disabled=True)

                with col3:
                    st.text_input("Personal Phone", uarf["personal_phone"], disabled=True)
                    st.text_input("Personal Email", uarf["personal_email"], disabled=True)
                    st.text_input("Supervisor", uarf["supervisor_name"], disabled=True)


                st.subheader("🔐 Platform Access Requested", anchor=False)
                platforms = self._get_platforms(selected_id)
                platform_flags = {}
                cols = st.columns(3)
                for idx, row in platforms.iterrows():
                    with cols[idx % 3]:
                        platform_flags[row["platform_name"]] = st.checkbox(
                            row["platform_name"],
                            value=row["access_required"],disabled=True
                        )
            st.divider()
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("hr_form", clear_on_submit=False):
                st.subheader("🏢 HR Section", anchor=False)
                st.caption("Fill in the details below to approve the UARF.")
                col1, col2 , col3= st.columns(3)
                with col1:
                    employee_id = st.text_input("Employee ID *")
                    office_phone = st.text_input("Office Phone (optional)")
                    # work_location = st.text_input("Work Location *")
                    work_location = st.selectbox("Work Location *", ["None"]  + helper.get_work_locations())

                with col2:
                    department = st.text_input("Department *")
                    office_email = st.text_input("Office Email (optional)")

                with col3:
                    designation = st.text_input("Designation *")
                    joining_date = st.date_input("Joining Date *")

                rejection_reason = st.text_area("Rejection reason (fill only if you want to reject)", height=80)
                # col_a, col_b = st.columns(2, gap='small')
                st.markdown("<br>", unsafe_allow_html=True)
                col_a, col_b, col3 = st.columns([1, 1, 2.3])
                approve = col_a.form_submit_button("✅ Approve")
                reject = col_b.form_submit_button("❌ Reject")

                if approve:
                    if employee_id.strip() == "" or department.strip() == "" or designation.strip() == "" or joining_date is None or work_location.strip() == "":
                        st.error("⚠️ Please fill all required fields before approving.")
                        st.stop()
                    if office_phone is not None and office_phone.strip() != "":
                        if not helper.validate_phone(office_phone):
                            st.error("⚠️ Please enter a valid office phone number (10 digits, starting with 9).")
                            st.stop()
                    if office_email is not None and office_email.strip() != "":
                        if not helper.validate_email(office_email):
                            st.error("⚠️ Please enter a valid office email address.")
                            st.stop()

                    self.confirm_hr( selected_id,
                        employee_id,
                        office_phone,
                        office_email,
                        department,
                        designation,
                        joining_date,
                        work_location)
                
               

            if reject:
                if rejection_reason is None or rejection_reason == "":
                    st.toast("Please provide rejection reason.", icon="ℹ️")
                    st.stop()
                if db.reject_by_hr(selected_id, rejection_reason=rejection_reason):
                    st.success("✅ UARF Rejected.")
                    sleep(1)
                    st.rerun()
                else:
                    st.error("❌ UARF rejection failed.")
        else:
            df = self.view_all_uarfs()
            if df.empty:
                st.info("No UARFs available.", icon="📢")
                st.stop()
            df = helper.rename_all_columns(df=df)
            df.index = df.index + 1
            st.dataframe(df, width='stretch', hide_index=False)


    # IT FUNCTION START ________________________________________
    def view_all_uarfs(self):
        df = pd.read_sql("""
            SELECT *
            FROM uarf_request
            ORDER BY created_at;
        """, self.holding_engine)
        df.drop(columns=['id'], inplace=True)
        return df
    
    def _get_it_pending_requests(self):
        return pd.read_sql("""
            SELECT id, full_name
            FROM uarf_request
            WHERE status = 'APPROVED_BY_HR'
            ORDER BY created_at;
        """, self.holding_engine)

    def _get_platforms(self, uarf_id):
        return pd.read_sql("""
            SELECT platform_name, access_required, access_created
            FROM uarf_platform_access
            WHERE uarf_id = %s
            AND access_required = TRUE;
        """, self.holding_engine, params=(uarf_id,))

    def it_ui(self):
        st.subheader("💻 IT Section", anchor=False)
        view = st.radio("Select View", ["View Pending Requests", "View UARFs"], horizontal=True,index=0)
        if view == "View Pending Requests":
            # 1️⃣ Load requests approved by HR
            df = self._get_it_pending_requests()
            total_pending_request = len(df)
            if df.empty:
                st.info("No requests pending IT action.", icon="📢")
                return
            st.badge(f"Pending Requests: {total_pending_request}", color='green')
            selected_id = st.selectbox(
                "Select Request",
                df["id"],
                format_func=lambda x: f"{df.loc[df['id'] == x, 'full_name'].values[0]}"
            )

            # 2️⃣ Load full request details
            uarf = self._get_uarf_details(selected_id)
            platforms = self._get_platforms(selected_id)
            
            card = st.container(border=True)
            with card:
                st.subheader("👔 Employee Details", anchor=False)
                st.caption("Employee details provided by Supervisor.")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Full Name", uarf["full_name"], disabled=True)
                    st.text_input("DOB (BS)", uarf["dob_bs"], disabled=True)
                    st.text_input("Citizenship No", uarf["citizenship_number"], disabled=True)
                    st.text_input("Personal Phone", uarf["personal_phone"], disabled=True)
                    st.text_input("Supervisor", uarf["supervisor_name"], disabled=True)

                with col2:
                    st.date_input("DOB (AD)", uarf["dob_ad"], disabled=True)
                    st.text_input("Issued Place", uarf["citizenship_issued_place"], disabled=True)
                    st.text_input("Personal Email", uarf["personal_email"], disabled=True)
                    st.text_input("Employee Type", uarf["employee_type"], disabled=True) 
                st.subheader("🔐 Platform Access Requested", anchor=False)
                platforms = self._get_platforms(selected_id)
                platform_flags = {}
                cols = st.columns(3)
                for idx, row in platforms.iterrows():
                    with cols[idx % 3]:
                        platform_flags[row["platform_name"]] = st.checkbox(
                            row["platform_name"],
                            value=row["access_required"],disabled=True
                        )
                        
            st.divider()
            card2 = st.container(border=True)
            with card2:
                st.subheader("🏢 HR Section", anchor=False)
                st.caption("Details filled by HR.")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Employee ID", uarf["employee_id"], disabled=True)
                    st.text_input("Office Phone", uarf["office_phone"], disabled=True)
                    st.text_input("Office Email", uarf["office_email"], disabled=True)
                    st.text_input("Department", uarf["department"], disabled=True)

                with col2:
                    st.text_input("Designation", uarf["designation"], disabled=True)
                    st.date_input("Joining Date", uarf["joining_date"], disabled=True)
                    st.text_input("Work Location", uarf["work_location"], disabled=True)

            st.divider()
            st.subheader("🔐 Platform Access", anchor=False)

            with st.form("it_form"):
                platform_flags = {}
                cols = st.columns(3)
                for idx, row in platforms.iterrows():
                    with cols[idx % 3]:
                        platform_flags[row["platform_name"]] = st.checkbox(
                            row["platform_name"],
                            value=row["access_required"]
                        )

                # submitted = st.form_submit_button("💾 Mark Completed")
                # col_a, col_f col3 = st.columns([1, 1, 2.3])
                approve = st.form_submit_button("✅ Mark as Created")
                reject = st.form_submit_button("❌ Reject")

            if approve:
                if db.update_it_platforms(selected_id, platform_flags):
                    st.success("✅ UARF processed successfully.")
                    sleep(1)
                    st.rerun()
                else:
                    st.error("❌ UARF processing failed.")
            if reject:
                if db.reject_by_it(selected_id):
                    st.success("❌ UARF rejected successfully.")
                    sleep(1)
                    st.rerun()
                else:
                    st.error("❌ UARF rejection failed.")
        else:
            df = self.view_all_uarfs()

            if df.empty:
                st.info("No UARFs available.", icon="ℹ️")
                st.stop()
                
            df = helper.rename_all_columns(df=df)
            df.index = df.index + 1
            st.dataframe(df, width='stretch', hide_index=False)


    
    # MAIN RENDER FUNCTION ________________________________________
    def render_page(self):
        if self.role in  ["MANAGER", "MANAGEMENT", "BRO"]:
            self.manager_ui()
        elif self.role == "HR":
            self.hr_ui()
        elif self.role in ['IT', 'ADMIN']:
            self.it_ui()
        elif self.role in ['USER']:
            df = self.view_all_uarfs()
            df = helper.rename_all_columns(df=df)
            df.index = df.index + 1
            st.badge(f"Total: {len(df)}", color='green')
            st.dataframe(df)
        else:
            st.info("Role not found. Contact your admin", icon="📢")
            st.stop()
        
if __name__ == "__main__":
    Uarf().render_page()