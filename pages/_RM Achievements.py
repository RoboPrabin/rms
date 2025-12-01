import numpy as np
import streamlit as st
import pandas as pd
from utils import helper
from datetime import datetime

class RMAchievement:
    def __init__(self):
        st.set_page_config("BRO Performance", page_icon="BRO", layout='wide')
        self.holding_engine = helper.get_holding_engine()
        self.df_floorsheet = None
        self.df_client_summary_map = None
        self.df_floorsheet_summary = None

        self.fetch_client_rm_map_db()

    def fetch_client_rm_map_db(self):
        self.df_client_summary_map = pd.read_sql("""
            SELECT * FROM client_rm_map
        """, self.holding_engine)

    def fetch_floorsheet_db(self, period):
        base_query = 'SELECT * FROM "floorsheet"'
        where_clause = ""
        
        if period == "Today":
            where_clause = 'WHERE "uploaded_at"::timestamp::date = CURRENT_DATE'
        elif period == "Yesterday":
            where_clause = "WHERE \"uploaded_at\"::timestamp::date = CURRENT_DATE - INTERVAL '1 day'"
        elif period == "1 Week":
            where_clause = "WHERE \"uploaded_at\"::timestamp >= CURRENT_DATE - INTERVAL '7 days'"
        elif period == "1 Month":
            where_clause = "WHERE \"uploaded_at\"::timestamp >= CURRENT_DATE - INTERVAL '1 month'"
        elif period == "3 Month":
            where_clause = "WHERE \"uploaded_at\"::timestamp >= CURRENT_DATE - INTERVAL '3 months'"
        elif period == "6 Month":
            where_clause = "WHERE \"uploaded_at\"::timestamp >= CURRENT_DATE - INTERVAL '6 months'"
        elif period == "YTD":
            where_clause = "WHERE \"uploaded_at\"::timestamp >= DATE_TRUNC('year', CURRENT_DATE)"
        
        query = base_query + where_clause
        self.df_floorsheet = pd.read_sql(query, self.holding_engine)

    def extract_each_client_summary(self):
        df = self.df_floorsheet
        summary = (df
            .assign(
                buy_qty=np.where(df['transaction_type'].str.upper() == 'BUY', df['quantity'], 0),
                sell_qty=np.where(df['transaction_type'].str.upper() == 'SELL', df['quantity'], 0),
                buy_amt=np.where(df['transaction_type'].str.upper() == 'BUY', df['amount'], 0),
                sell_amt=np.where(df['transaction_type'].str.upper() == 'SELL', df['amount'], 0)
            )
            .groupby('clientcode', as_index=False)
            .agg(
                total_buy=('buy_qty', 'sum'),
                total_sell=('sell_qty', 'sum'),
                total_buy_amount=('buy_amt', 'sum'),
                total_sell_amount=('sell_amt', 'sum'),
                total_commission=('stockcomm', 'sum')
            )
            .assign(total_turnover=lambda x: x['total_buy_amount'] + x['total_sell_amount'])
            [['clientcode', 'total_buy', 'total_sell', 'total_buy_amount',
              'total_sell_amount', 'total_turnover', 'total_commission']]
        )
        summary.rename(columns={'clientcode': 'client_code'}, inplace=True)
        self.df_floorsheet_summary = summary

    def extract_rm_sales_summary(self, period):
        self.fetch_floorsheet_db(period)
        self.extract_each_client_summary()

        df_final = (self.df_floorsheet_summary
            .merge(self.df_client_summary_map[['clientCode', 'rmName']],
                   left_on='client_code', right_on='clientCode', how='left')
            .drop(columns='clientCode')
            [['client_code', 'rmName', 'total_buy', 'total_sell',
              'total_buy_amount', 'total_sell_amount', 'total_turnover', 'total_commission']]
            .dropna(subset=['rmName'])
        )

        rm_summary = (df_final
            .groupby('rmName', as_index=False)
            .agg({
                'total_turnover': 'sum',
                'total_buy_amount': 'sum',
                'total_sell_amount': 'sum',
                'total_commission': 'sum',
                'client_code': 'nunique'
            })
            .rename(columns={
                'rmName': 'BRO',
                'total_turnover': 'Total Turnover',
                'total_buy_amount': 'Total Buy Amount',
                'total_sell_amount': 'Total Sell Amount',
                'total_commission': 'Total Commission Gain',
                'client_code': 'Total Traders Clients'
            })
            .rename(columns={'client_code': 'Total Traders Clients'})
            .sort_values('Total Turnover', ascending=False)
        )
        rm_summary.reset_index(inplace=True, drop=True)
        rm_summary.index = rm_summary.index + 1
        rm_summary = helper.format_dataframe(rm_summary)
        return rm_summary

    def show(self):
        st.title("BRO Performance Dashboard")

        view_mode = st.radio(
            "Select Period",
            ["Today","Yesterday",  "1 Week", "1 Month", "3 Month", "6 Month", "YTD"],
            horizontal=True,
            key="period_selection"
        )

        with st.spinner(f"Loading {view_mode} data..."):
            rm_summary = self.extract_rm_sales_summary(view_mode)

        if len(rm_summary) >0 :
            st.subheader(f"BRO Summary - {view_mode}", anchor=False)
            st.dataframe(rm_summary, use_container_width=True)
        else:
            st.warning("Floorsheet has not uploaded yet.", icon="⚠️")


if __name__ == "__main__":
    RMAchievement().show()