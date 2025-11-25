import streamlit as st
import pandas as pd
import sqlalchemy
from config import config
from utils import helper
from navigation import render_sidebar
import app_state

class BroSummaryPage:
    def __init__(self):
        st.set_page_config(page_title="Client Summary", layout='wide', page_icon="📃")
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        
        helper.adjust_ui()
        render_sidebar()


    def render(self):
        st.title("🙎🏻 Client Summary", anchor=False)
        df = self.load_data()
        df = df.round(2)
        df = helper.format_negative_numbers(df)
        df = helper.format_dataframe(df)
        # st.badge(f"{len(df)}", color="blue")
        
        df.rename(columns={"Profit Loss Percentage": "Profit (Loss) Percentage", "Profit Loss Amount" : "Profit (Loss) Amount"}, inplace=True)
        search_query = st.text_input("Search in table")

        if search_query:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

        # df.index += 1
        st.dataframe(df, width='stretch')
        # st.dataframe(df, width='stretch')


    @st.cache_data(ttl=helper.default_ttl())
    def load_data(_self):
        engine = sqlalchemy.create_engine(helper.get_holding_engine())
        df = pd.read_sql("SELECT * FROM client_summary", engine)
        df.reset_index(drop=True, inplace=True)
        df.index = df.index + 1  
        return df



# 🔄 Entry point
if __name__ == "__main__":
    BroSummaryPage().render()