from time import sleep
import pandas as pd
import streamlit as st
from pages.BasePage import BasePage
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import auth_utils, helper

class ActiveSession(BasePage):
    def __init__(self):
        super().__init__(require_auth_check=True, required_role="ADMIN")
        st.session_state.active_menu = "user"
        st.set_page_config(page_title="Active Session", page_icon="🕓", layout="wide")
        # user = auth_utils.ensure_logged_in()
        # self.username= user['username']
        # self.role= user['role']
        # self.branch = user['branch']
        st.header("🕓 Active Sessions", anchor=False)

        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())
        self.session_ids = None

    def get_all_active_sessions(self):
        query = text("""
            SELECT *
            FROM user_session
        """)

        with self.holding_engine.begin() as conn:
            result = conn.execute(query, {"created_by": self.username})
            rows = result.fetchall()

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=result.keys())
        return df

    def truncate_query(self):
        with self.holding_engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE user_session"))

    def delete_sessions_by_ids(self, ids: list):
        if not ids:
            return  # defensive programming

        with self.holding_engine.begin() as conn:
            conn.execute(
                text("""
                    DELETE FROM user_session
                    WHERE id = ANY(:ids)
                """),
                {"ids": ids}
            )

    def render_page(self):
        df = self.get_all_active_sessions()
        if df is not None:
            df.drop(columns=["user_agent"], inplace=True)
            total_active = df[df["session_status"] == "ACTIVE"].shape[0]
            df.columns = df.columns.str.upper()
            df.index = df.index + 1
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Truncate session", icon="🚮"):
                    # self.truncate_query()
                    self.delete_sessions_by_ids(st.session_state.session_ids)
                    with col2:
                        st.success("User session terminated.")
                    sleep(0.5)
                    st.rerun()
            st.badge(f"Total Active: {total_active}" )
            selected_state = st.dataframe(df,selection_mode='multi-row', key='truncate_table', on_select='rerun')
            if selected_state.selection.rows:
                selected_df = df.iloc[selected_state.selection.rows]
                st.session_state.session_ids = selected_df["ID"].tolist()
            st.stop()
        st.info(f"No Active Sessions.", icon="📢")



if __name__ == "__main__":
    ActiveSession().render_page()