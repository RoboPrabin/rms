import plotly.express as px
from datetime import datetime, timedelta
from decimal import Decimal
from time import sleep
import pandas as pd
import streamlit as st

from pages.BasePage import BasePage
from streamlit_bridge.navigation import render_sidebar
from db import db
from utils import helper


class TriProjects(BasePage):
    STATUS_OPTIONS = ["PLANNED", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "DROPPED"]
    PRIORITY_OPTIONS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin("-4rem")
        st.session_state.active_menu = "utility"
        st.set_page_config(page_title="Trishakti Projects", page_icon="📁", layout="wide")
        st.header("📁 Trishakti Projects", anchor=False)

        render_sidebar()
        self._initialize_session_state()

    def _initialize_session_state(self):
        defaults = {
            "selected_project_id": None,
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    # -------------------------
    # Database Helpers
    # -------------------------
    def _execute_query(self, query, params=None, fetchone=False, fetchall=False, commit=False):
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params or ())

            result = None
            if fetchone:
                result = cursor.fetchone()
            elif fetchall:
                result = cursor.fetchall()

            if commit:
                conn.commit()

            return result

        except Exception as e:
            if conn:
                conn.rollback()
            st.error(f"Database error: {e}")
            return None

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def _get_all_projects(self, status_filter=None, search_text=None):
        query = """
            SELECT
                id,
                name,
                status,
                priority,
                start_date,
                target_end_date,
                actual_end_date,
                uat_days,
                completion_percentage,
                description,
                remarks,
                owner_name,
                created_at,
                updated_at
            FROM tri_projects
            WHERE 1 = 1
        """
        params = []

        if status_filter and status_filter != "ALL":
            query += " AND status = %s"
            params.append(status_filter)

        if search_text:
            query += """
                AND (
                    name ILIKE %s
                    OR COALESCE(owner_name, '') ILIKE %s
                    OR COALESCE(description, '') ILIKE %s
                    OR COALESCE(remarks, '') ILIKE %s
                )
            """
            like_value = f"%{search_text.strip()}%"
            params.extend([like_value, like_value, like_value, like_value])

        query += " ORDER BY created_at DESC"

        rows = self._execute_query(query, params, fetchall=True)
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(row) for row in rows])

        for col in ["start_date", "target_end_date", "actual_end_date", "created_at", "updated_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        return df

    def _get_project_by_id(self, project_id):
        query = """
            SELECT
                id,
                name,
                status,
                priority,
                start_date,
                target_end_date,
                actual_end_date,
                uat_days,
                completion_percentage,
                description,
                remarks,
                owner_name
            FROM tri_projects
            WHERE id = %s
        """
        row = self._execute_query(query, (str(project_id),), fetchone=True)
        return dict(row) if row else None

    def _insert_project(self, payload):
        query = """
            INSERT INTO tri_projects (
                name,
                status,
                priority,
                start_date,
                target_end_date,
                actual_end_date,
                uat_days,
                completion_percentage,
                description,
                remarks,
                owner_name
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            payload["name"],
            payload["status"],
            payload["priority"],
            payload["start_date"],
            payload["target_end_date"],
            payload["actual_end_date"],
            payload["uat_days"],
            payload["completion_percentage"],
            payload["description"],
            payload["remarks"],
            payload["owner_name"],
        )
        return self._execute_query(query, params, commit=True)

    def _update_project(self, project_id, payload):
        query = """
            UPDATE tri_projects
            SET
                name = %s,
                status = %s,
                priority = %s,
                start_date = %s,
                target_end_date = %s,
                actual_end_date = %s,
                uat_days = %s,
                completion_percentage = %s,
                description = %s,
                remarks = %s,
                owner_name = %s,
                updated_at = NOW()
            WHERE id = %s
        """
        params = (
            payload["name"],
            payload["status"],
            payload["priority"],
            payload["start_date"],
            payload["target_end_date"],
            payload["actual_end_date"],
            payload["uat_days"],
            payload["completion_percentage"],
            payload["description"],
            payload["remarks"],
            payload["owner_name"],
            str(project_id),
        )
        return self._execute_query(query, params, commit=True)

    def _delete_project(self, project_id):
        query = "DELETE FROM tri_projects WHERE id = %s"
        return self._execute_query(query, (str(project_id),), commit=True)

    # -------------------------
    # Validation
    # -------------------------
    def _validate_payload(self, payload):
        if not payload["name"] or not payload["name"].strip():
            return False, "❌ Project name is required."
        
        if not payload["start_date"] or not payload["start_date"]:
            return False, "❌ Start date is required."
        
        if not payload["target_end_date"] or not payload["target_end_date"]:
            return False, "❌ Target end date is required."
        
        if not payload["description"] or not payload["description"].strip():
            return False, "❌ Description is required."
        

        if payload["uat_days"] < 0:
            return False, "❌ UAT days cannot be negative."

        if payload["completion_percentage"] < 0 or payload["completion_percentage"] > 100:
            return False, "❌ Completion percentage must be between 0 and 100."

        start_date = payload["start_date"]
        target_end_date = payload["target_end_date"]
        actual_end_date = payload["actual_end_date"]

        if start_date and target_end_date and target_end_date < start_date:
            return False, "❌ Target end date cannot be before start date."

        if start_date and actual_end_date and actual_end_date < start_date:
            return False, "❌ Actual end date cannot be before start date."

        if payload["status"] == "COMPLETED" and not actual_end_date:
            return False, "❌ Actual end date is required when status is COMPLETED."

        return True, None

    # -------------------------
    # UI Sections
    # -------------------------
    def _render_metrics(self, df):
        st.subheader("Project Snapshot", anchor=False)

        total_projects = len(df)
        planned = len(df[df["status"] == "PLANNED"]) if not df.empty else 0
        completed = len(df[df["status"] == "COMPLETED"]) if not df.empty else 0
        in_progress = len(df[df["status"] == "IN_PROGRESS"]) if not df.empty else 0
        on_hold = len(df[df["status"] == "ON_HOLD"]) if not df.empty else 0
        dropped = len(df[df["status"] == "DROPPED"]) if not df.empty else 0

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Total", total_projects)
        col2.metric("Planned", planned)
        col3.metric("Completed", completed)
        col4.metric("In Progress", in_progress)
        col5.metric("On Hold", on_hold)
        col6.metric("Dropped", dropped)

    def _render_charts(self, df):
        if df.empty:
            st.info("No project data available for charts.")
            return

        col1, col2 = st.columns(2)

        # -------------------------
        # Donut Chart - Status
        # -------------------------
        with col1:
            st.markdown("**Projects by Status**")

            status_order = ["PLANNED", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "DROPPED"]
            status_df = (
                df["status"]
                .value_counts()
                .reindex(status_order)
                .dropna()
                .reset_index()
            )
            status_df.columns = ["status", "count"]

            status_colors = {
                "PLANNED": "#6c757d",
                "IN_PROGRESS": "#0d6efd",
                "ON_HOLD": "#ffc107",
                "COMPLETED": "#198754",
                "DROPPED": "#dc3545"
            }

            fig1 = px.pie(
                status_df,
                names="status",
                values="count",
                hole=0.5,  # 👈 donut
                color="status",
                color_discrete_map=status_colors
            )

            fig1.update_traces(textinfo="percent+label")

            fig1.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=True,
                paper_bgcolor="rgba(0,0,0,0)",   # transparent
                plot_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(fig1, use_container_width=True)

        # -------------------------
        # Donut Chart - Priority
        # -------------------------
        with col2:
            st.markdown("**Projects by Priority**")

            priority_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            priority_df = (
                df["priority"]
                .value_counts()
                .reindex(priority_order)
                .dropna()
                .reset_index()
            )
            priority_df.columns = ["priority", "count"]

            priority_colors = {
                "LOW": "#6c757d",
                "MEDIUM": "#0d6efd",
                "HIGH": "#fd7e14",
                "CRITICAL": "#dc3545"
            }

            fig2 = px.pie(
                priority_df,
                names="priority",
                values="count",
                hole=0.5,  # 👈 donut
                color="priority",
                color_discrete_map=priority_colors
            )

            fig2.update_traces(textinfo="percent+label")

            fig2.update_layout(
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=True,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )

            st.plotly_chart(fig2, use_container_width=True)



    def _render_project_table(self, df):
        st.subheader("Project Data", anchor=False)

        if df.empty:
            st.warning("No projects found.")
            return

        display_df = df.copy()

        # Normalize owner before filtering
        if "owner_name" in display_df.columns:
            display_df["owner_name"] = display_df["owner_name"].apply(
                lambda x: "PRABIN" if x == "ADMIN" else x
            )

        # -------------------------
        # Filters
        # -------------------------
        filter_col1, filter_col2, filter_col3 = st.columns(3)

        owner_options = ["ALL"] + sorted(
            [owner for owner in display_df["owner_name"].dropna().unique().tolist()]
        )

        status_options = ["ALL"] + sorted(
            [status for status in display_df["status"].dropna().unique().tolist()]
        )

        priority_options = ["ALL"] + sorted(
            [priority for priority in display_df["priority"].dropna().unique().tolist()]
        )

        with filter_col1:
            selected_owner = st.selectbox("Filter by Owner", owner_options)

        with filter_col2:
            selected_status = st.selectbox("Filter by Status", status_options)

        with filter_col3:
            selected_priority = st.selectbox("Filter by Priority", priority_options)

        if selected_owner != "ALL":
            display_df = display_df[display_df["owner_name"] == selected_owner]

        if selected_status != "ALL":
            display_df = display_df[display_df["status"] == selected_status]

        if selected_priority != "ALL":
            display_df = display_df[display_df["priority"] == selected_priority]

        if display_df.empty:
            st.warning("No projects found for selected filters.")
            return

        for col in ["start_date", "target_end_date", "actual_end_date"]:
            if col in display_df.columns:
                display_df[col] = pd.to_datetime(display_df[col], errors="coerce").dt.strftime("%Y-%m-%d")

        for col in ["created_at", "updated_at"]:
            if col in display_df.columns:
                display_df[col] = pd.to_datetime(display_df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

        display_df.drop(columns=["id"], inplace=True, errors="ignore")
        display_df.rename(
            columns={
                "owner_name": "Owner",
                "remarks": "Remarks",
                "description": "Description",
                "uat_days": "UAT Days",
                "completion_percentage": "Completion %",
                "status": "Status",
                "priority": "Priority",
                "start_date": "Start Date",
                "target_end_date": "Target End Date",
                "actual_end_date": "Actual End Date",
                "created_at": "Created At",
                "updated_at": "Updated At",
                "name": "Name",
            },
            inplace=True
        )

        display_df.reset_index(drop=True, inplace=True)
        display_df.index += 1
        st.badge(label=f"Total Projects: {len(display_df)}", icon= "📁")
        st.dataframe(display_df, width="stretch")

    def _render_create_form(self):
        st.subheader("Create New Project", anchor=False)

        with st.form("create_project_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                name = st.text_input("Project Name *")
                start_date = st.date_input("Start Date *", value=datetime.now().date(), format="YYYY-MM-DD")
                completion_percentage = st.number_input(
                    "Completion Percentage",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=1.0
                )

            with col2:
                priority = st.selectbox("Priority *", self.PRIORITY_OPTIONS, index=1)
                target_end_date = st.date_input("Target End Date *", value=datetime.now().date() + timedelta(days=10), format="YYYY-MM-DD")
                uat_days = st.number_input(
                    "UAT Days",
                    min_value=0,
                    value=0,
                    step=1
                )

            with col3:
                status = st.selectbox("Status *", self.STATUS_OPTIONS, index=0)
                actual_end_date = st.date_input("Actual End Date", value=None, format="YYYY-MM-DD")
                owner_name = st.text_input("Owner Name *", value=self.username, disabled=True)

            col3, col4 = st.columns(2)
            with col3:
                description = st.text_area("Description *", height=120)
            with col4:
                remarks = st.text_area("Remarks", height=120)

            submitted = st.form_submit_button("Create Project", width='content', icon="➕")

            if submitted:
                payload = {
                    "name": name.strip().title(),
                    "status": status,
                    "priority": priority,
                    "start_date": start_date,
                    "target_end_date": target_end_date,
                    "actual_end_date": actual_end_date,
                    "uat_days": int(uat_days),
                    "completion_percentage": Decimal(str(completion_percentage)),
                    "description": description.strip() if description else None,
                    "remarks": remarks.strip() if remarks else None,
                    "owner_name": owner_name.strip() if owner_name else None,
                }

                is_valid, error_message = self._validate_payload(payload)
                if not is_valid:
                    st.error(error_message)
                    return

                self._insert_project(payload)
                st.success("Project created successfully.", icon="✅")
                sleep(1.2)
                st.rerun()

    def _render_update_delete_tab(self, df):
        st.subheader("Update / Delete Project", anchor=False)

        if df.empty:
            st.info("No projects available.")
            return

        options = {
            f"{row['name']} | {row['status']} | {row['priority']}": row["id"]
            for _, row in df.iterrows()
        }

        selected_label = st.selectbox(
            "Select Project",
            options=list(options.keys()),
            index=None,
            placeholder="Choose a project to edit or delete"
        )

        if not selected_label:
            st.info("Select a project to continue.")
            return

        selected_project_id = options[selected_label]
        project = self._get_project_by_id(selected_project_id)

        if not project:
            st.error("Selected project not found.")
            return

        with st.form("update_project_form", clear_on_submit=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                name = st.text_input("Project Name *", value=project["name"])
                start_date = st.date_input(
                    "Start Date",
                    value=project["start_date"],
                    format="YYYY-MM-DD"
                )
                completion_percentage = st.number_input(
                    "Completion Percentage",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(project["completion_percentage"]) if project["completion_percentage"] is not None else 0.0,
                    step=1.0
                )

            with col2:
                priority = st.selectbox(
                    "Priority *",
                    self.PRIORITY_OPTIONS,
                    index=self.PRIORITY_OPTIONS.index(project["priority"])
                )
                target_end_date = st.date_input(
                    "Target End Date",
                    value=project["target_end_date"],
                    format="YYYY-MM-DD"
                )
                uat_days = st.number_input(
                    "UAT Days",
                    min_value=0,
                    value=int(project["uat_days"]) if project["uat_days"] is not None else 0,
                    step=1
                )

            with col3:
                status = st.selectbox(
                    "Status *",
                    self.STATUS_OPTIONS,
                    index=self.STATUS_OPTIONS.index(project["status"])
                )
                actual_end_date = st.date_input(
                    "Actual End Date",
                    value=project["actual_end_date"],
                    format="YYYY-MM-DD"
                )
                owner_name = st.text_input("Owner Name", value=project["owner_name"] or "", disabled=True)

            col3, col4 = st.columns(2)
            with col3:
                description = st.text_area(
                    "Description",
                    value=project["description"] or "",
                    height=120
                )
            with col4:
                remarks = st.text_area(
                    "Remarks",
                    value=project["remarks"] or "",
                    height=120
                )

            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 3])

            with col_btn1:
                update_clicked = st.form_submit_button("Update Project", width="content", icon="✏️")

            with col_btn2:
                delete_clicked = st.form_submit_button("Delete Project", width="content", icon="🗑️", help="This action cannot be undone")

            if update_clicked:
                payload = {
                    "name": name.strip(),
                    "status": status,
                    "priority": priority,
                    "start_date": start_date,
                    "target_end_date": target_end_date,
                    "actual_end_date": actual_end_date,
                    "uat_days": int(uat_days),
                    "completion_percentage": Decimal(str(completion_percentage)),
                    "description": description.strip() if description else None,
                    "remarks": remarks.strip() if remarks else None,
                    "owner_name": owner_name.strip() if owner_name else None,
                }

                is_valid, error_message = self._validate_payload(payload)
                if not is_valid:
                    st.error(error_message)
                    return

                self._update_project(selected_project_id, payload)
                st.success("Project updated successfully.", icon="✅")
                sleep(1.2)
                st.rerun()

            if delete_clicked:
                self._delete_project(selected_project_id)
                st.success("Project deleted successfully.", icon="✅")
                sleep(1.2)
                st.rerun()

    # -------------------------
    # Main Renderer
    # -------------------------
    def render_page(self):
        st.markdown("---")

        filter_col1, filter_col2 = st.columns([1, 2])

        with filter_col1:
            status_filter = st.selectbox(
                "Filter by Status",
                options=["ALL"] + self.STATUS_OPTIONS
            )

        with filter_col2:
            search_text = st.text_input("Search by name, owner, description, or remarks")

        df = self._get_all_projects(status_filter=status_filter, search_text=search_text)

        tab1, tab2, tab3, tab4 = st.tabs([
            "Dashboard",
            "Create Project",
            "Update/Delete Project",
            "Project Data"
        ])

        with tab1:
            self._render_metrics(df)
            st.markdown("---")
            self._render_charts(df)

        with tab2:
            self._render_create_form()

        with tab3:
            self._render_update_delete_tab(df)

        with tab4:
            self._render_project_table(df)


if __name__ == "__main__":
    TriProjects().render_page()