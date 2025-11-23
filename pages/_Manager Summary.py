import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from config import config
from utils import helper
# from auth_guard import require_role
from navigation import render_sidebar

class ManagerSummaryPage:
    def __init__(self):
        st.set_page_config(page_title="Manager Summary", layout="wide", page_icon="👨‍💼")
        helper.adjust_ui()
        render_sidebar()
        
        # helper.hide_login_page()
        # helper.logout_if_unauthorized()

    def render(self):
        st.title("🧑‍💼 Manager Summary", anchor=False)
        df = self.load_data()
        df = df.round(2)
        df = helper.format_negative_numbers(df)
        df = helper.format_dataframe(df)
        # df = df.map(lambda x: f"({abs(x):,})" if isinstance(x, (int, float)) and x < 0 else f"{x:,}" if isinstance(x, (int, float)) else x)

        df.rename(columns={"Used Limit": "Assigned Limit", "Total Ledger Balance": "Used Limit" , "Unrealised Profit Loss" : "Unrealised Profit (Loss)"}, inplace=True)
        search_query = st.text_input("Search in table")

        if search_query:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

        df.index += 1
        st.dataframe(df, width='stretch')


    def sync_limits_to_manager_summary(self):
        engine = create_engine(helper.get_holding_engine())
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE manager_summary2
                SET 
                    "totalLimit" = bl."totalLimit",
                    "usedLimit" = bl."usedLimit"
                FROM bro_limit bl
                WHERE manager_summary2.bro = bl."broCode"
            """))

    @st.cache_data(ttl=helper.default_ttl())
    def load_data(_self):
        engine = create_engine(helper.get_holding_engine())
        
        # Sync limits from bro_limit
        _self.sync_limits_to_manager_summary()

        df = pd.read_sql("SELECT * FROM manager_summary2", engine)
        df.reset_index(drop=True, inplace=True)
        df.index = df.index + 1  
        return df



# 🔄 Entry point
if __name__ == "__main__":
    ManagerSummaryPage().render()