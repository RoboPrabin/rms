import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import helper

class Feedback:
    def __init__(self):
        st.set_page_config(page_title="Active Session", page_icon="🕓", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        st.header("🕓 Active Sessions", anchor=False)

        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())

    def get_all_feedbacks(self):
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

    def render_page(self):
        df = self.get_all_feedbacks()
        if df is not None:
            df.drop(columns=["id", "user_agent"], inplace=True)
            total_active = df[df["session_status"] == "ACTIVE"].shape[0]
            df.columns = df.columns.str.upper()
            df.index = df.index + 1
            st.badge(f"Total Active: {total_active}" )
            st.dataframe(df)
            st.stop()
        st.info(f"No any feedbacks yet.", icon="📢")



if __name__ == "__main__":
    Feedback().render_page()