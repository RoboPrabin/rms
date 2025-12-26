from db import db
import streamlit_hotkeys as hotkeys
import plotly.express as px
from datetime import datetime, timedelta
from nepali_datetime import date as nepali_date
from datetime import datetime
import streamlit as st
import pandas as pd
from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils.formatting import *
from utils.custom_hotkey import activate_client_code_hotkey
class PayableAndReceivable:
    def __init__(self):
        helper.eliminate_top_padding()
        st.set_page_config("Payable & Receivable", page_icon="💸", layout='wide')

        # Dates
        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_date = datetime.now().strftime("%Y-%m-%d")
        self.today_np_date = nepali_date.today()

        # Authentication
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()


        self.username, self.role = app_state.get_current_user_info()
        activate_client_code_hotkey()

        # Sidebar
        navigation.render_sidebar()
        st.header("💸 Payables & Receivables", anchor=False)

                


    # @st.cache_data(ttl=600)
    def get_today_floorsheet_and_book_closure(_self, from_selected_date, to_selected_date):
        df_floorsheet = db.get_today_floorsheet_range(from_selected_date, to_selected_date)
        df_book_closure = db.get_today_book_closure(from_selected_date)
        return df_floorsheet, df_book_closure


    def calculate_totals(self):
        # --- Fetch data ---
        # df_book_closure = db.get_today_book_closure()
        # df_today = db.get_today_floorsheet(selected_date=self.selected_floorsheet_date)
        df_floorsheet, df_book_closure = pd.DataFrame(), pd.DataFrame()
        col1, col2 , col3= st.columns([1,1,1])
        with st.form("floorsheet_range", border=False):
            with col1:
                self.from_floorsheet_date = st.date_input("From date", width=410)
            with col2:
                self.to_floorsheet_date = st.date_input("To date", width=410)
        # with col3:
            if st.form_submit_button("📥 Fetch Floorsheet"):
                print(self.from_floorsheet_date)
                print(self.to_floorsheet_date)
                df_floorsheet, df_book_closure = self.get_today_floorsheet_and_book_closure(from_selected_date = self.from_floorsheet_date, to_selected_date = self.to_floorsheet_date)
                print(df_floorsheet)
        st.divider()
        if df_floorsheet.empty:
            st.info("Floorsheet not found.", icon="📢")
            st.stop()
            return {}

        scripts = df_book_closure['script'].dropna().unique().tolist()

        # --- Aggregate full floorsheet ---
        totals = (
            df_floorsheet
            .pivot_table(
                index='symbol',
                columns='transaction_type',
                values='amount',
                aggfunc='sum',
                fill_value=0
            )
            .rename(columns={
                'Buy': 'Total_Script_Buy',
                'Sell': 'Total_Script_Sell'
            })
        )

        totals['Net_Amount'] = (
            totals['Total_Script_Buy'] - totals['Total_Script_Sell']
        )

        # --- Book Closure specific totals ---
        bc_totals = totals.loc[totals.index.isin(scripts)]

        total_buy = totals['Total_Script_Buy'].sum()
        total_sell = totals['Total_Script_Sell'].sum()

        total_bc_buy = bc_totals['Total_Script_Buy'].sum()
        total_bc_sell = bc_totals['Total_Script_Sell'].sum()

        # --- Settlement Amount (TODAY) ---
        net_buy = total_buy - total_bc_buy
        net_sell = total_sell - total_bc_sell
        settlement_amount = net_buy - net_sell
        # settlement_amount = (
        #     (total_buy - total_bc_buy) +
        #     (total_sell - total_bc_sell)
        # )

        return {
            "total_buy": total_buy,
            "total_sell": total_sell,
            "total_bc_buy": total_bc_buy,
            "total_bc_sell": total_bc_sell,
            "settlement_amount": settlement_amount
        }, df_floorsheet, df_book_closure



    def render_page(self):
        totals, df_floorsheet, df_bc = self.calculate_totals()
        # t3_day = datetime.now() + timedelta(days=3)
        t3_day = self.from_floorsheet_date + timedelta(days=3)
        t3_weekday = t3_day.strftime('%A')  # Monday, Tuesday, etc.
        st.subheader(f"Settlement Amount for   {t3_weekday},   {t3_day.strftime('%Y-%m-%d')}  : Rs. {(totals['settlement_amount']):,.2f}", anchor=False)
        st.caption(f"BC Buy:   " + str(totals['total_bc_buy']) + ", BC Sell:  " + str(totals['total_bc_sell']))
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Floorsheet")
            st.dataframe(df_floorsheet)
        with col2:
            st.caption("Book Closure")
            st.dataframe(df_bc)

# ---------------------------------------------------------
# ✅ Run App
# ---------------------------------------------------------
if __name__ == "__main__":
    PayableAndReceivable().render_page()