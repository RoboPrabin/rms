from utils import auth_utils, mailer
from datetime import datetime
from time import sleep
from db import db
import streamlit_bridge.app_state as app_state
import pandas as pd
import streamlit as st
import uuid
from sqlalchemy import create_engine, text
from utils import helper 
from streamlit_bridge.navigation import render_sidebar
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage


class CreateAppUser(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "user"
        self.header = "Create App User"
        st.set_page_config(page_title=self.header, layout="wide", page_icon="➕")
        # user = auth_utils.ensure_logged_in()
        # self.username= user['username']
        # self.role= user['role']
        # self.branch = user['branch']

        activate_client_code_hotkey()

        render_sidebar()
        helper.adjust_ui()
        st.title(f"👤 {self.header}", anchor=False)
        self.engine = create_engine(helper.get_holding_engine())
        self.df_users : pd.DataFrame= None
        self.app_user = self.get_all_app_users()
        self.user_roles = db.get_user_roles()
        self.branch = helper.get_work_locations()

    def show_creation_form(self):
        with st.form("create_user_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                username = st.text_input("User code").upper()
            with col2:
                full_name = st.text_input("Full name").title()
            # full_name = st.text_input("Full name").title()

            col3, col4 = st.columns(2)
            with col3:
                password = st.text_input("Password", type="password", help="Password field is case sensitive.", value=helper.generate_secure_password(), disabled=True)
            with col4:
                phone = st.text_input("Phone", value="9999999999")
            
            col5, col6 = st.columns(2)
            with col5:
                email = st.text_input("Email")
            with col6:
                citizenship = st.text_input("Citizenship No (Optional)", value="99-99-99-99-99")

            df_users = self.app_user
            options = (df_users["username"] + " - " + df_users["full_name"]).tolist()
            col7, col8 = st.columns(2)
            with col7:
                onboarded_by = st.selectbox("Onboarded By", options)
            
            with col8:
                alias = st.selectbox("Alias", options, accept_new_options=True)
                
            col9, col10 = st.columns(2)
            with col9:
                if self.role == "ADMIN":
                    roles = self.user_roles 
                    role = st.selectbox("Role", roles)
                else:
                    roles = self.user_roles
                    roles = [r for r in roles if r not in ("ADMIN", "SYSTEM")]
                    role = st.selectbox("Role", roles)
            with col10:
                branch = st.selectbox("Branch", helper.get_work_locations())
            
            submitted = st.form_submit_button("Create App User", icon="➕")

            if submitted:
                if not username or not password or not phone or not email or not full_name or not onboarded_by or not branch:
                    st.warning("All fields are required.")
                elif db.get_user_by_username(username=username.strip().lower()):
                    st.warning("Username already exists. Please choose a different username.")
                elif not helper.is_valid_password(password=password):
                    st.warning("Password must be at least 8 characters long and include uppercase, lowercase, number, and special character.")
                elif not helper.validate_phone(phone=phone):
                    st.warning("Invalid phone number format.")  
                else:
                    try:
                        encrypted_pw = password
                        user_id = str(uuid.uuid4())

                        with self.engine.begin() as conn:
                            conn.execute(
                                text("""
                                    INSERT INTO app_user ( username, password, full_name, citizenship ,email, role, phone, onboarded_by, created_at, created_by, status, alias, failed_attempts, branch)
                                    VALUES ( :username, :password,:full_name, :citizenship ,:email, :role, :phone, :onboarded_by, :created_at, :created_by, :status, :alias, :failed_attempts, :branch)
                                """),
                                {
                                    # "id": user_id,
                                    "username": username,
                                    "password": encrypted_pw,
                                    "full_name": full_name,
                                    "citizenship": citizenship.lower().strip(),
                                    "email": email.lower(),
                                    "role": role,
                                    "phone": phone,
                                    "onboarded_by": onboarded_by.split("-")[0].strip().upper(),
                                    "alias":alias.split("-")[0].strip().upper(),
                                    "created_at": datetime.now(),
                                    "created_by": self.username.upper(),
                                    "status": "ACTIVE",
                                    "failed_attempts": 0,
                                    "branch": branch
                                }
                            )
                        st.success(f"User '{username}' created successfully.")
                        with st.spinner("Sending Email. Please wait....", show_time=True):
                            mailer.send_email(
                                            to_email=email,
                                            username=username,
                                            password=password,
                                            full_name=full_name
                                            )
                        st.success("Email sent succcessfully", icon="✅")
                        sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating user: {e}")


    def show_all_app_users(self):
        st.markdown("---")
        st.subheader("📋 All App Users", anchor=False)
        # Fetch users
        try:
            df_users = pd.read_sql('SELECT * FROM app_user ORDER BY username;', con=self.engine)
            df_users.columns = df_users.columns.str.capitalize()
            if self.role != "ADMIN":
                df_users_display = df_users.drop(columns=["Id", "Password"])  # Hide UUID column
            else:
                df_users_display = df_users.drop(columns=["Id"])  # Hide UUID column
            search_query = st.text_input("Search in table")
            if search_query:
                df_users_display = df_users_display[df_users_display.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]


            if self.role in ["MANAGER", "BRO"]:
                df_users_display.drop(columns=["Status", "Failed_attempts", "Last_failed_at", "Blocked_at", "Created_by", "Created_at"], inplace=True)


            df_users_display = helper.prettify_columns(df=df_users_display)
            df_users_display.index += 1
            self.df_users = df_users_display
            st.dataframe(df_users_display, width='stretch')
        except Exception as e:
            st.error(f"Error loading users: {e}")


    def show_update_delete_function(self):
        self.df_users["display"] = self.df_users["Username"] + " - " + self.df_users["Full Name"]

        if len(self.df_users["display"]) == 0:
            st.warning("Search result not found.", icon="⚠️")
            st.stop()
       
       
        # st.subheader("✏️ Update or ❌ Delete User", anchor=False)
        # Use that for the selectbox
        selected_user = st.selectbox(
            "Select a user to modify",
            self.df_users["display"].tolist()
        )

        selected_user = str(selected_user).split("-")[0].strip()

        action = st.radio("Action", ["Update", "Delete"], horizontal=True)
        

        if action == "Update":
            # --- Master users list ---
            df_users = self.app_user.copy()
            df_users["display"] = df_users["username"] + " - " + df_users["full_name"]
            options = df_users["display"].tolist()
            # print("Options:", options)
            # print(df_users)
            # --- DB values for current user ---
            db_alias = self.df_users.loc[
                self.df_users["Username"] == selected_user, "Alias"
            ].values[0]

            db_onboarded_by = self.df_users.loc[
                self.df_users["Username"] == selected_user, "Onboarded By"
            ].values[0]
            
            db_role = self.df_users.loc[
                self.df_users["Username"] == selected_user, "Role"
            ].values[0]
            

            db_status = self.df_users.loc[
                self.df_users["Username"] == selected_user, "Status"
            ].values[0]

            db_branch = self.df_users.loc[
                self.df_users["Username"] == selected_user, "Branch"
            ].values[0]
            st.write(db_branch)
            # --- Resolve DB → display for users ---
            alias_matches = df_users.loc[df_users["username"] == db_alias, "display"]
            alias_display = alias_matches.values[0] if len(alias_matches) > 0 and pd.notna(db_alias) else ""

            onboarded_matches = df_users.loc[df_users["username"] == db_onboarded_by, "display"]
            onboarded_by_display = onboarded_matches.values[0] if len(onboarded_matches) > 0 and pd.notna(db_onboarded_by) else ""

            role_matches = df_users.loc[df_users["role"] == db_role, "role"]
            role_display = role_matches.values[0] if len(role_matches) > 0 else db_role

            branch_matches = df_users.loc[df_users["branch"] == db_branch, "branch"]
            branch_display = branch_matches.values[0] if len(branch_matches) > 0 else db_branch
            # --- Resolve display → index (Streamlit requirement) ---
            alias_index = options.index(alias_display) if alias_display in options else 0
            onboarded_by_index = options.index(onboarded_by_display) if onboarded_by_display in options else 0
            role_index = self.user_roles.index(role_display) if role_display in self.user_roles else 0
            update_branches = [b for b in self.branch if b != "OTHER"]
            branch_index = update_branches.index(branch_display) if branch_display in update_branches else 0
            # --- Status options ---
            status_options = ["ACTIVE", "BLOCKED"]
            status_index = status_options.index(db_status) if db_status in status_options else 0

            with st.form("update_form"):
                # --- UI Columns ---
                col1, col2 = st.columns(2)
                with col1:
                    full_name = st.text_input(
                        "Full Name",
                        value=self.df_users.loc[self.df_users["Username"] == selected_user, "Full Name"].values[0]
                    )
                with col2:
                    citizenship = st.text_input(
                        "Citizenship",
                        value=self.df_users.loc[self.df_users["Username"] == selected_user, "Citizenship"].values[0]
                    )

                col3, col4 = st.columns(2)
                with col3:
                    phone = st.text_input(
                        "Phone",
                        value=self.df_users.loc[self.df_users["Username"] == selected_user, "Phone"].values[0]
                    )
                with col4:
                    new_email = st.text_input(
                        "Email",
                        value=self.df_users.loc[self.df_users["Username"] == selected_user, "Email"].values[0]
                    )

                col5, col6 = st.columns(2)
                with col5:
                    new_role = st.selectbox("Role",self.user_roles, index=role_index)
                with col6:
                    new_password = st.text_input(
                        "Password",
                        type="password",
                        value=self.df_users.loc[self.df_users["Username"] == selected_user, "Password"].values[0]
                    )

                col7, col8 = st.columns(2)
                with col7:
                    failed_attempts = st.number_input(
                        "Failed Attempts",
                        value=self.df_users.loc[self.df_users["Username"] == selected_user, "Failed Attempts"].values[0]
                    )
                with col8:
                    status = st.selectbox(
                        "Status",
                        status_options,
                        index=status_index
                    )

                # --- Alias and Onboarded By selectboxes ---
                col9, col10 = st.columns(2)
                with col9:
                    onboarded_by = st.selectbox(
                        "Onboarded By",
                        options,
                        index=onboarded_by_index
                    )
                with col10:
                    alias = st.selectbox(
                        "Alias",
                        options,
                        index=alias_index
                    )

                branch = st.selectbox("Branch", update_branches, index=branch_index)

                if st.form_submit_button("Update User", icon="🔄"):
                    try:
                        with self.engine.begin() as conn:
                            conn.execute(
                                    text("""
                                        UPDATE app_user
                                        SET email = :email, role = :role, password = :password, full_name = :full_name,
                                            phone = :phone, citizenship = :citizenship, onboarded_by = :onboarded_by, 
                                        status = :status, failed_attempts = :failed_attempst, alias = :alias, branch = :branch,
                                         updated_by = :updated_by
                                        WHERE username = :username
                                    """),
                                    {
                                        "email": new_email.lower(),
                                        "role": new_role,
                                        "password": new_password,
                                        "username": selected_user,
                                        "full_name": full_name,
                                        "phone": phone,
                                        "citizenship": citizenship,
                                        "onboarded_by": onboarded_by.split("-", 1)[0].strip().upper(),
                                        "alias":alias.split("-", 1)[0].strip().upper(),
                                        "status": status,
                                        "failed_attempst":failed_attempts,
                                        "branch": branch,
                                        "updated_by": st.session_state.username
                                    }
                                )
                        st.success(f"User '{selected_user}' updated successfully.")
                        sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error updating user: {e}")

        elif action == "Delete":
            if st.button("Delete User"):
                try:
                    with self.engine.begin() as conn:
                        result = conn.execute(
                            text("DELETE FROM app_user WHERE TRIM(username) = :username"),
                            {"username": selected_user.strip()}
                        )
                    if result.rowcount == 0:
                        st.warning(f"No user found with username '{selected_user}'. Searching database for similar...")
                        with self.engine.begin() as conn:
                            similar = conn.execute(
                                text("SELECT username FROM app_user WHERE username ILIKE :pattern"),
                                {"pattern": f"%{selected_user.strip()}%"}
                            ).fetchall()
                        if similar:
                            st.info(f"Found similar usernames: {[row[0] for row in similar]}")
                    else:
                        st.success(f"User '{selected_user}' deleted successfully.")
                        self.app_user = self.get_all_app_users()
                except Exception as e:
                    st.error(f"Error deleting user: {e}")
                else:
                    st.rerun()

    def get_all_app_users(self):
        df_users = pd.read_sql(
            'SELECT username, full_name, role, branch FROM app_user ORDER BY alias;',
            # 'SELECT alias, full_name FROM app_user ORDER BY alias;',
            con=self.engine
        )
        system_row = pd.DataFrame([{"username": "SYSTEM", "full_name": "App System"}])
        df_users = pd.concat([system_row, df_users], ignore_index=True)
        return df_users
    

    def render_page(self):
        # Create radio buttons with horizontal layout
        selected_option = st.radio(
            "Choose an option:",
            ("Create App User", "View App Users" ,"Add/View Role"),
            horizontal=True
        )

        if selected_option == "Create App User":
            self.show_creation_form()
        elif selected_option == "View App Users":
            self.show_all_app_users()
            if self.role == "ADMIN":
                st.markdown("---")
                with st.expander("✏️ Update or ❌ Delete User"):
                    self.show_update_delete_function()
        else:
            new_role = st.text_input("New Role").upper()
            self.header = "Create New Role"

            if st.button("Add New Role", icon="➕"):
                if new_role.strip():
                    engine = create_engine(helper.get_holding_engine())
                    with engine.begin() as conn:
                        # Check if role already exists
                        result = conn.execute(
                            text("SELECT COUNT(*) FROM app_user_role WHERE role_type = :role_type"),
                            {"role_type": new_role.strip()}
                        )
                        exists = result.scalar()  # returns the count

                        if exists > 0:
                            st.error(f"Role '{new_role}' already exists!", icon="⚠️")
                        else:
                            conn.execute(
                                text("INSERT INTO app_user_role (role_type) VALUES (:role_type)"),
                                {"role_type": new_role.strip()}
                            )
                            st.success(f"Role '{new_role}' added successfully!")
                else:
                    st.warning("Please enter a valid role name.", icon="⚠️")

            # Show all roles from app_user_role table
            engine = create_engine(helper.get_holding_engine())
            with engine.begin() as conn:
                result = conn.execute(text("SELECT role_type, description FROM app_user_role ORDER BY role_type"))
                roles = [row for row in result]

            st.markdown("---")
            st.subheader("👨‍💼 Existing Roles", anchor=False)
            if roles:
                df_roles = pd.DataFrame(roles, columns=["Role Type", "Description"])
                df_roles.index += 1
                st.dataframe(df_roles)
            else:
                st.write("No roles found.")



if __name__ == "__main__":
    app_user = CreateAppUser()
    app_user.render_page()