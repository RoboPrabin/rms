import streamlit as st
from datetime import datetime
from time import sleep
from db import db
import streamlit_bridge.app_state as app_state
from sqlalchemy import create_engine, text
from utils import helper 
from streamlit_bridge.navigation import render_sidebar
import pandas as pd
class CommunicationReport:
    def __init__(self):
        st.set_page_config(page_title="Communication Report", layout="wide", page_icon="📢")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()

        render_sidebar()
        helper.adjust_ui()
        st.title(f"📢 Communication Report", anchor=False)
        self.engine = create_engine(helper.get_holding_engine())
        self.user_roles = db.get_user_roles()


    def show_add_communication_report_ui(self):
        st.subheader("Add Communication Report", anchor=False)

        # Horizontal layout for username, organization, status
        username = st.text_input("Username", value=self.username, disabled=True)
        col1, col2 = st.columns(2)
        with col1:
            organization = st.text_input("Organization").title()
        with col2:
            address = st.text_input("Address").title()


        


        # Horizontal layout for from_date and to_date
        col4, col5 = st.columns(2)
        with col4:
            from_date = st.date_input("From Date", value=datetime.now().date())
        with col5:
            to_date = st.date_input("To Date", value=datetime.now().date())
        
        # Horizontal layout for reason_to_visit and feedback
        col6, col7 = st.columns(2)
        with col6:
            reason_to_visit = st.text_area("Reason to Visit")
        with col7:
            feedback = st.text_area("Feedback")
        
        status = st.selectbox(
            "Status",
            options=helper.get_list_of_status_for_communication_report(role=self.role)
        )
        # Submit button
        if st.button("Submit"):
            if username.strip() and organization.strip():
                with self.engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO communication_report 
                            (username, organization, address, from_date, to_date, status, feedback, reason_to_visit)
                            VALUES (:username, :organization, :address ,:from_date, :to_date, :status, :feedback, :reason_to_visit)
                        """),
                        {
                            "username": username.strip(),
                            "organization": organization.strip(),
                            "address": address.strip(),
                            "from_date": datetime.combine(from_date, datetime.min.time()),
                            "to_date": datetime.combine(to_date, datetime.min.time()),
                            "status": status.strip(),
                            "feedback": feedback.strip(),
                            "reason_to_visit": reason_to_visit.strip()
                        }
                    )
                st.success("Communication report added successfully!", icon="ℹ️")
                st.balloons()
                sleep(1)
                st.rerun()
            else:
                st.warning("Please fill in required fields (Username, Organization).")

    def view_communication_report(self):
        st.subheader("📄 Existing Communication Reports", anchor=False)
        with self.engine.begin() as conn:
            if self.role == "BRO":
                result = conn.execute(
                    text("""
                        SELECT id, username, organization, address, from_date, to_date, status, reason_to_visit, feedback, total_days
                        FROM communication_report
                        WHERE username = :username
                        ORDER BY from_date DESC
                    """),
                    {"username": self.username}
                )
                rows = result.fetchall()
            else:
                result = conn.execute(text("""
                    SELECT id, username, organization,address, from_date, to_date, status, reason_to_visit, feedback, total_days
                    FROM communication_report
                    ORDER BY from_date DESC
                """))
                rows = result.fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=[
                "ID", "Username", "Organization", "Address","From Date", "To Date", "Status", "Reason to Visit", "Feedback", "Total Days"
            ])
            df.index = df.index + 1
            st.dataframe(df.drop(columns=["ID"]))  # show table without exposing UUIDs
            st.markdown("---")
            if self.role == "BRO":
                # Select report to update (show organization names instead of UUIDs)
                org_map = {row[2]: row[0] for row in rows}  # {organization: id}
                selected_org = st.selectbox("Select a report to update (by Organization)", options=list(org_map.keys()))
            else:
                org_map = {f"{row[1]} | {row[2]}": row[0] for row in rows} 
                selected_org = st.selectbox("Select a report to update", options=list(org_map.keys()))

            if selected_org:
                selected_id = org_map[selected_org]
                current = next(r for r in rows if r[0] == selected_id)


            if selected_org:
                selected_id = org_map[selected_org]
                current = next(r for r in rows if r[0] == selected_id)

                st.subheader("📝 Update Report", anchor=False)

                col10, col11 = st.columns(2)
                with col10:
                    st.text_input("Organization", value=current[2], disabled=True)
                with col11:
                    st.text_input("Address", value=current[3])

                col1, col2 = st.columns(2)
                with col1:
                    from_date = st.date_input("From Date", value=current[4].date())
                with col2:
                    to_date = st.date_input("To Date", value=current[5].date())


                col4, col5 = st.columns(2)
                with col4:
                    reason_to_visit = st.text_area("Reason to Visit", value=current[6])
                with col5:
                    feedback = st.text_area("Feedback", value=current[7])
                
                status = st.selectbox(
                    "Status",
                    options=helper.get_list_of_status_for_communication_report(role=self.role),
                    index=helper.get_list_of_status_for_communication_report(role=self.role).index(current[6])
                )

                col_update, col_delete = st.columns(2)
                with col_update:
                    if st.button("💡 Update Report"):
                        with self.engine.begin() as conn:
                            conn.execute(
                                text("""
                                    UPDATE communication_report
                                    SET from_date = :from_date,
                                        to_date = :to_date,
                                        status = :status,
                                        reason_to_visit = :reason_to_visit,
                                        feedback = :feedback
                                    WHERE id = :id
                                """),
                                {
                                    "from_date": datetime.combine(from_date, datetime.min.time()),
                                    "to_date": datetime.combine(to_date, datetime.min.time()),
                                    "status": status.strip(),
                                    "reason_to_visit": reason_to_visit.strip(),
                                    "feedback": feedback.strip(),
                                    "id": selected_id
                                }
                            )
                        st.success("Report updated successfully!")
                        sleep(1)
                        st.rerun()

                # Delete button only for ADMIN
                if self.role == "ADMIN":
                    with col_delete:
                        if st.button("⛔ Delete Report"):
                            with self.engine.begin() as conn:
                                conn.execute(
                                    text("DELETE FROM communication_report WHERE id = :id"),
                                    {"id": selected_id}
                                )
                            st.success("Report deleted successfully!")
                            sleep(1)
                            st.rerun()
        else:
            st.write("No reports found.")


    def render_page(self):
        selected_option = st.radio(
            "Choose an option:",
            ("Add Communication Report", "View/Edit Communication Report"),
            horizontal=True
        )
        if selected_option == "Add Communication Report":
            self.show_add_communication_report_ui()
        else:
            self.view_communication_report()
        


if __name__ == "__main__":
    CommunicationReport().render_page()