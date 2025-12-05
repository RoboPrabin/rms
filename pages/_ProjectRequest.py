import streamlit as st
from datetime import datetime
from time import sleep
from db import db
import streamlit_bridge.app_state as app_state
from sqlalchemy import create_engine, text
from utils import helper 
from streamlit_bridge.navigation import render_sidebar
import pandas as pd


class ProjectRequest:
    def __init__(self):
        st.set_page_config(page_title="Project Request", layout="wide", page_icon="📢")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()

        render_sidebar()
        helper.adjust_ui()
        st.title(f"📢 Project Request", anchor=False)
        self.engine = create_engine(helper.get_holding_engine())
        self.user_roles = db.get_user_roles()

    def show_add_project_request_ui(self):
        st.subheader("Submit Project Request", anchor=False)

        # Username (auto-filled, disabled)
        username = st.text_input("Username", value=self.username, disabled=True)

        # Project name
        project_name = st.text_input("Project Name")

        # Horizontal layout for project type and priority
        col1, col2 = st.columns(2)
        with col1:
            project_type = st.selectbox(
                "Project Type",
                options=["Automation", "Web App", "Desktop App"]
            )
        with col2:
            project_priority = st.selectbox(
                "Project Priority",
                options=["LOW", "MEDIUM", "HIGH"]
            )

        # # Status dropdown
        # status = st.selectbox(
        #     "Status",
        #     options=["PIPLINE", "IN-PROGRESS", "COMPLETED", "DROPPED"]
        # )

        # Project description (full width)
        project_description = st.text_area("Project Description")

        # Submit button
        if st.button("Submit"):
            if project_name.strip() and project_type.strip() and project_description.strip():
                with self.engine.begin() as conn:
                    conn.execute(
                        text("""
                            INSERT INTO project_request 
                            (username, project_name, project_type, project_description, project_priority, status)
                            VALUES (:username, :project_name, :project_type, :project_description, :project_priority, :status)
                        """),
                        {
                            "username": username.strip(),
                            "project_name": project_name.strip(),
                            "project_type": project_type.strip(),
                            "project_description": project_description.strip(),
                            "project_priority": project_priority.strip(),
                            "status": "PIPELINE"
                        }
                    )
                st.success("Project request added successfully!", icon="✅")
                sleep(1)
                st.rerun()
            else:
                st.warning("Please fill in required fields (Project Name, Project Type, Project Description).")

    def view_project_requests(self):
        st.subheader("📄 Existing Project Requests", anchor=False)
        with self.engine.begin() as conn:
            if self.role == "BRO":
                result = conn.execute(
                    text("""
                        SELECT id, username, project_name, project_type, project_description, project_priority, status
                        FROM project_request
                        WHERE username = :username
                        ORDER BY project_priority DESC
                    """),
                    {"username": self.username}
                )
                rows = result.fetchall()
            elif self.role in ["ADMIN", "MANAGER"]:
                result = conn.execute(
                    text("""
                        SELECT id, username, project_name, project_type, project_description, project_priority, status
                        FROM project_request
                        ORDER BY project_priority DESC
                    """)
                )
                rows = result.fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=[
                "ID", "Username", "Project Name", "Project Type", "Project Description", "Priority", "Status"
            ])
            df.index = df.index + 1
            st.dataframe(df.drop(columns=["ID"]))  # hide UUIDs in table

            st.markdown("---")
            # Build mapping for dropdown labels
            label_map = {f"{row[1]} - {row[2]}": row[0] for row in rows}  
            # "username - project_name - project_type"
            selected_label = st.selectbox("Select a request to manage", options=list(label_map.keys()))

            if selected_label:
                selected_id = label_map[selected_label]
                current = next(r for r in rows if r[0] == selected_id)

                st.subheader("📝 Manage Project Request", anchor=False)

                # Username shown but disabled
                st.text_input("Username", value=current[1], disabled=True)

                # Project name editable
                project_name = st.text_input("Project Name", value=current[2])

                col1, col2 = st.columns(2)
                with col1:
                    project_type = st.text_input("Project Type", value=current[3])
                with col2:
                    project_priority = st.selectbox(
                        "Priority",
                        options=["HIGH", "MEDIUM", "LOW"],
                        index=["HIGH", "MEDIUM", "LOW"].index(current[5])
                    )

                # # Status dropdown
                
                if self.role in ["ADMIN", "MANAGER"]:
                    status = st.selectbox(
                        "Status",
                        options=helper.get_list_of_status_for_project_request(),
                        index=helper.get_list_of_status_for_project_request().index(current[6])
                    )
                else:
                    # Show status as read-only for BRO
                    status = current[6]

                project_description = st.text_area("Project Description", value=current[4])

                col_update, col_delete = st.columns(2)

                # Update option for all roles
                with col_update:
                    if st.button("💡 Update Request"):
                        with self.engine.begin() as conn:
                            conn.execute(
                                text("""
                                    UPDATE project_request
                                    SET project_name = :project_name,
                                        project_type = :project_type,
                                        project_description = :project_description,
                                        project_priority = :project_priority,
                                        status = :status
                                    WHERE id = :id
                                """),
                                {
                                    "project_name": project_name.strip(),
                                    "project_type": project_type.strip(),
                                    "project_description": project_description.strip(),
                                    "project_priority": project_priority.strip(),
                                    "status": status.strip(),
                                    "id": selected_id
                                }
                            )
                        st.success("Project request updated successfully!")
                        sleep(1)
                        st.rerun()

                # Delete option only for ADMIN and MANAGER
                if self.role in ["ADMIN", "MANAGER"]:
                    with col_delete:
                        if st.button("⛔ Delete Request"):
                            with self.engine.begin() as conn:
                                conn.execute(
                                    text("DELETE FROM project_request WHERE id = :id"),
                                    {"id": selected_id}
                                )
                            st.success("Project request deleted successfully!")
                            sleep(1)
                            st.rerun()
        else:
            st.write("No project requests found.")

    def render_page(self):
        selected_option = st.radio(
            "Choose an option:",
            ("Add Project Request", "View Project Requests"),
            horizontal=True
        )
        if selected_option == "Add Project Request":
            self.show_add_project_request_ui()
        else:
            self.view_project_requests()


if __name__=="__main__":
    ProjectRequest().render_page()