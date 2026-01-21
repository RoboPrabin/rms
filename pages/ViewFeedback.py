import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
import streamlit_bridge.app_state as app_state
from db import db
from sqlalchemy import create_engine, text
from utils import helper

class Feedback:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "utility"
        st.set_page_config(page_title="Feedbacks", page_icon="💬", layout="wide")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role, self.branch = app_state.get_current_user_info()
        render_sidebar()
        self.holding_engine = create_engine(helper.get_holding_engine())

    def get_all_feedbacks(self):
        query = text("""
            SELECT *
            FROM feedback
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
            st.dataframe(df)
            st.stop()
        st.info(f"No any feedbacks yet.", icon="📢")



if __name__ == "__main__":
    Feedback().render_page()