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


class CreateAppUser:
    def __init__(self):
        st.set_page_config(page_title="Create App User", layout="wide", page_icon="➕")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()

        render_sidebar()
        helper.adjust_ui()
        st.title("👤 Create App User", anchor=False)
        self.engine = create_engine(helper.get_holding_engine())
        self.df_users : pd.DataFrame= None
        self.app_user = self.get_all_app_users()
        self.user_roles = db.get_user_roles()

    def show_creation_form(self):
        with st.form("create_user_form"):
            username = st.text_input("User code").upper()
            full_name = st.text_input("Full name").title()
            # full_name = st.text_input("Full name").title()
            password = st.text_input("Password", type="password", help="Password field is case sensitive.")
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            citizenship = st.text_input("Citizenship No (Optional)")
            df_users = self.app_user
            options = (df_users["username"] + " - " + df_users["full_name"]).tolist()
            onboarded_by = st.selectbox("Onboarded By", options)

            if self.role == "ADMIN":
                roles = self.user_roles 
                role = st.selectbox("Role", roles)
            else:
                roles = self.user_roles
                roles = [r for r in roles if r not in ("ADMIN", "SYSTEM")]
                role = st.selectbox("Role", roles)
            submitted = st.form_submit_button("Create User")

            if submitted:
                if not username or not password or not phone or not email or not full_name or not onboarded_by:
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
                                    INSERT INTO app_user (id, username, password, full_name, citizenship ,email, role, phone, onboarded_by, created_at, created_by, status)
                                    VALUES (:id, :username, :password,:full_name, :citizenship ,:email, :role, :phone, :onboarded_by, :created_at, :created_by, :status)
                                """),
                                {
                                    "id": user_id,
                                    "username": username,
                                    "password": encrypted_pw,
                                    "full_name": full_name,
                                    "citizenship": citizenship.lower().strip(),
                                    "email": email.lower(),
                                    "role": role,
                                    "phone": phone,
                                    "onboarded_by": onboarded_by.split("-")[0].strip().upper(),
                                    "created_at": datetime.now(),
                                    "created_by": self.username.upper(),
                                    "status": "ACTIVE",
                                }
                            )
                        st.success(f"User '{username}' created successfully.")
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
        st.markdown("---")
        st.subheader("✏️ Update or ❌ Delete User", anchor=False)
        # selected_user = st.selectbox("Select a user to modify",self.df_users["Username"].tolist())
        # Build a display column
        self.df_users["display"] = self.df_users["Username"] + " - " + self.df_users["Full Name"]

        # Use that for the selectbox
        selected_user = st.selectbox(
            "Select a user to modify",
            self.df_users["display"].tolist()
        )

        selected_user = str(selected_user).split("-")[0].strip()

        action = st.radio("Action", ["Update", "Delete"])


        if action == "Update":
            full_name = st.text_input("Full Name", value=self.df_users.loc[self.df_users["Username"] == selected_user, "Full Name"].values[0])
            phone = st.text_input("Phone", value=self.df_users.loc[self.df_users["Username"] == selected_user, "Phone"].values[0])
            citizenship = st.text_input("Citizenship", value=self.df_users.loc[self.df_users["Username"] == selected_user, "Citizenship"].values[0])
            new_email = st.text_input("Email", value=self.df_users.loc[self.df_users["Username"] == selected_user, "Email"].values[0])
            new_role = st.selectbox("Role", self.user_roles)
            
            new_password = st.text_input("Password", type="password", value=self.df_users.loc[self.df_users["Username"] == selected_user, "Password"].values[0])
            df_users = self.app_user
            options = (df_users["username"] + " - " + df_users["full_name"]).tolist()
            onboarded_by = st.selectbox("Onboarded By", options)
            status = st.selectbox("status", ["ACTIVE", "BLOCKED"])

            if st.button("Update User"):
                try:
                    with self.engine.begin() as conn:
                       conn.execute(
                            text("""
                                UPDATE app_user
                                SET email = :email, role = :role, password = :password, full_name = :full_name,
                                    phone = :phone, citizenship = :citizenship, onboarded_by = :onboarded_by, status = :status
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
                                "status": status
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
                        conn.execute(
                            text("DELETE FROM app_user WHERE username = :username"),
                            {"username": selected_user}
                        )
                    st.success(f"User '{selected_user}' deleted successfully.")
                except Exception as e:
                    st.error(f"Error deleting user: {e}")

    def get_all_app_users(self):
        df_users = pd.read_sql(
            'SELECT username, full_name FROM app_user ORDER BY username;',
            con=self.engine
        )
        system_row = pd.DataFrame([{"username": "SYSTEM", "full_name": "App System"}])
        df_users = pd.concat([system_row, df_users], ignore_index=True)
        return df_users
    

    def render_page(self):
        self.show_creation_form()
        self.show_all_app_users()
        if self.role == "ADMIN":
            self.show_update_delete_function()

if __name__ == "__main__":
    app_user = CreateAppUser()
    app_user.render_page()