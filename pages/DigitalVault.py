from nepali_datetime import date as nepali_date
import streamlit as st
import pandas as pd
from utils import helper
from datetime import datetime, timedelta
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config
from sqlalchemy import create_engine, text
from utils.custom_hotkey import activate_client_code_hotkey


class DigitalVault:
    def __init__(self):
        st.set_page_config("Digital Vault", page_icon="🔐", layout='wide')

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
        self.holding_engine = create_engine(helper.get_holding_engine())

        st.header("🔐 My Digital Vault", anchor=False)

    def save_to_db(self, platform, username, password, url):
        query = """
            INSERT INTO digital_vault (platform, username, password, url, created_by, created_at)
            VALUES (:platform, :username, :password, :url, :created_by, NOW())
        """

        with self.holding_engine.begin() as conn:
            conn.execute(
                text(query),
                {
                    "platform": platform,
                    "username": username,
                    "password": password,
                    "url": url,
                    "created_by": self.username
                }
            )

    def show_add_credentials_form(self):
        st.subheader("➕Add New Credential", anchor=False)

        platform_dict = helper.get_platform_options()
        platform_list = list(platform_dict.keys())

        # --- Platform Dropdown ---
        selected_platform = st.selectbox("Select Platform", platform_list)

        # Auto-fill URL based on platform
        auto_url = platform_dict.get(selected_platform, "")

        # --- Form Layout ---
        with st.form("vault_form", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                username = st.text_input("Username")

            with col2:
                password = st.text_input("Password", type="password")

            # URL field (auto-filled but editable)
            url = st.text_input("URL", value=auto_url)

            submitted = st.form_submit_button("Save")

            if submitted:
                if not username or not password:
                    st.error("Username and Password are required.")
                else:
                    self.save_to_db(selected_platform, username, password, url)
                    st.success("Credential saved successfully!")


    # def show_credentials(self):
    #     df = self.get_all_credentials()
    #     st.subheader("Saved Credentials")
    #     st.dataframe(df, use_container_width=True)
    def update_credential(self, record_id, platform, username, password, url):
        query = text("""
            UPDATE digital_vault
            SET platform = :platform,
                username = :username,
                password = :password,
                url = :url
            WHERE id = :id AND created_by = :created_by
        """)

        with self.holding_engine.begin() as conn:
            conn.execute(query, {
                "platform": platform,
                "username": username,
                "password": password,
                "url": url,
                "id": record_id,
                "created_by": self.username
            })


    def delete_credential(self, record_id):
        query = text("""
            DELETE FROM digital_vault
            WHERE id = :id AND created_by = :created_by
        """)

        with self.holding_engine.begin() as conn:
            conn.execute(query, {
                "id": record_id,
                "created_by": self.username
            })

    def render_edit_delete_section(self, row):
        st.markdown("---")
        st.subheader("Edit / Delete Credential")

        with st.form(f"edit_form_{row['id']}"):
            platform = st.text_input("Platform", value=row['platform'])
            username = st.text_input("Username", value=row['username'])
            password = st.text_input("Password", value=row['password'])
            url = st.text_input("URL", value=row['url'])

            col1, col2 = st.columns(2)

            with col1:
                update_btn = st.form_submit_button("Update", icon="💡")

            with col2:
                delete_btn = st.form_submit_button("Delete", type="primary", icon='🗑️')

            if update_btn:
                self.update_credential(row['id'], platform, username, password, url)
                st.success("Updated successfully")
                st.rerun()

            if delete_btn:
                self.delete_credential(row['id'])
                st.success("Deleted successfully")
                st.rerun()

    def show_credentials(self):
        # if self.role == "ADMIN":
            # df = self.get_all_credentials()
        # else:
        df = self.get_loggedin_user_credentials()

        if df is None or df.empty:
            return

        st.subheader("Saved Credentials")

        # Add a selection column
        # df_display = df.copy()
        df_display:pd.DataFrame = df.drop(columns=["id", 'created_at'])
        df_display.columns = df_display.columns.str.upper()

        # df_display["Select"] = False

        # Display table
        selected_index = st.dataframe(
            df_display,
            use_container_width=True,
            selection_mode='single-row',
            hide_index=True,
            on_select="rerun"
        )

        # Streamlit returns selected rows differently depending on version
        selected_rows = selected_index.get("selection", {}).get("rows", [])
        if selected_rows:
            row = df.iloc[selected_rows[0]]
            self.render_edit_delete_section(row)


    def get_loggedin_user_credentials(self):
        query = text("""
            SELECT id, platform, username, password, url, created_at
            FROM digital_vault
            WHERE created_by = :created_by
            ORDER BY created_at DESC
        """)

        with self.holding_engine.begin() as conn:
            result = conn.execute(query, {"created_by": self.username})
            rows = result.fetchall()

        if not rows:
            st.info("No credentials found.")
            return

        df = pd.DataFrame(rows, columns=result.keys())
        return df
    
    
    def get_all_credentials(self):
        query = text("""
            SELECT *
            FROM digital_vault
            ORDER BY created_at DESC
        """)

        with self.holding_engine.begin() as conn:
            result = conn.execute(query, {"created_by": self.username})
            rows = result.fetchall()

        if not rows:
            st.info("No credentials found.")
            return

        df = pd.DataFrame(rows, columns=result.keys())
        return df

    
    def render_page(self):
        mode = st.radio("Mode", ['Add Credentials', 'View/Edit credentials'], horizontal=True, index=1)
        if mode == 'Add Credentials':
            self.show_add_credentials_form()
        else:
            self.show_credentials()


if __name__ == "__main__":
    DigitalVault().render_page()