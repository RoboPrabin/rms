import app_state
import pandas as pd
import streamlit as st
import uuid
from sqlalchemy import create_engine, text
from utils import helper 
from navigation import render_sidebar


class CreateAppUser:
    def __init__(self):
        st.set_page_config(page_title="Create App User", layout="wide", page_icon="➕")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()


        render_sidebar()
        helper.adjust_ui()
        st.title("👤 Create New App User", anchor=False)
        self.engine = create_engine(helper.get_holding_engine())
        self.df_users : pd.DataFrame= None

    def show_creation_form(self):

        with st.form("create_user_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password", help="Password field is case sensitive.")
            email = st.text_input("Email")
            role = st.selectbox("Role", ["MANAGER", "BRO", "ADMIN"])
            submitted = st.form_submit_button("Create User")

            if submitted:
                if not username or not password or not email:
                    st.warning("All fields are required.")
                else:
                    try:
                        encrypted_pw = password
                        user_id = str(uuid.uuid4())

                        with self.engine.begin() as conn:
                            conn.execute(
                                text("""
                                    INSERT INTO app_user (id, username, password, email, role)
                                    VALUES (:id, :username, :password, :email, :role)
                                """),
                                {
                                    "id": user_id,
                                    "username": username.lower(),
                                    "password": encrypted_pw,
                                    "email": email.lower(),
                                    "role": role
                                }
                            )
                        st.success(f"User '{username}' created successfully.")
                    except Exception as e:
                        st.error(f"Error creating user: {e}")


    def show_all_app_users(self):
        st.markdown("---")
        st.subheader("📋 All App Users")

        # Fetch users
        try:
            df_users = pd.read_sql('SELECT * FROM app_user ORDER BY username;', con=self.engine)
            df_users_display = df_users.drop(columns=["id"])  # Hide UUID column
            search_query = st.text_input("Search in table")

            if search_query:
                df_users_display = df_users_display[df_users_display.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

            df_users_display.index += 1
            self.df_users = df_users_display
            st.dataframe(df_users_display, width='stretch')
        except Exception as e:
            st.error(f"Error loading users: {e}")


    def show_update_delete_function(self):
        st.markdown("---")
        st.subheader("✏️ Update or ❌ Delete User")

        selected_user = st.selectbox("Select a user to modify",self.df_users["username"].tolist())

        action = st.radio("Action", ["Update", "Delete"])

        if action == "Update":
            new_email = st.text_input("New Email", value=self.df_users.loc[self.df_users["username"] == selected_user, "email"].values[0])
            new_role = st.selectbox("New Role", ["MANAGER", "BRO", "ADMIN"])
            new_password = st.text_input("New Password", type="password")

            if st.button("Update User"):
                try:
                    with self.engine.begin() as conn:
                        conn.execute(
                            text("""
                                UPDATE app_user
                                SET email = :email, role = :role, password = :password
                                WHERE username = :username
                            """),
                            {
                                "email": new_email.lower(),
                                "role": new_role,
                                "password": new_password,
                                "username": selected_user
                            }
                        )
                    st.success(f"User '{selected_user}' updated successfully.")
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


    def render_page(self):
        self.show_creation_form()
        self.show_all_app_users()
        self.show_update_delete_function()

if __name__ == "__main__":
    app_user = CreateAppUser()
    app_user.render_page()