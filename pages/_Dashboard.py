import numpy as np
import streamlit as st
import pandas as pd
from utils import helper
from datetime import datetime, timedelta
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation

class RMAchievement:
    def __init__(self):
        st.set_page_config("BRO Performance", page_icon="Chart", layout='wide')

        # Authentication & User Info
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()

        # DB Connection
        self.holding_engine = helper.get_holding_engine()

        # Data placeholders
        self.df_floorsheet = None
        self.df_client_summary_map = None
        self.df_floorsheet_summary = None
        self.bro_yearly_target = None

        # Load static data
        self.fetch_client_rm_map_db()
        self.fetch_bro_yearly_target_db()

    def fetch_client_rm_map_db(self):
        self.df_client_summary_map = pd.read_sql("SELECT * FROM client_rm_map", self.holding_engine)

    def fetch_bro_yearly_target_db(self):
        self.bro_yearly_target = pd.read_sql("SELECT * FROM bro_yearly_target", self.holding_engine)

    def fetch_floorsheet_db(self, period):
        conditions = {
            "Today":      '"uploaded_at"::timestamp::date = CURRENT_DATE',
            "Yesterday":  '"uploaded_at"::timestamp::date = CURRENT_DATE - INTERVAL \'1 day\'',
            "1 Week":     '"uploaded_at"::timestamp >= CURRENT_DATE - INTERVAL \'7 days\'',
            "1 Month":    '"uploaded_at"::timestamp >= CURRENT_DATE - INTERVAL \'1 month\'',
            "3 Month":    '"uploaded_at"::timestamp >= CURRENT_DATE - INTERVAL \'3 months\'',
            "6 Month":    '"uploaded_at"::timestamp >= CURRENT_DATE - INTERVAL \'6 months\'',
            "YTD":        '"uploaded_at"::timestamp >= DATE_TRUNC(\'year\', CURRENT_DATE)'
        }

        query = f'SELECT * FROM "floorsheet" WHERE {conditions[period]}'
        self.df_floorsheet = pd.read_sql(query, self.holding_engine)

    def extract_each_client_summary(self):
        df = self.df_floorsheet
        if df.empty:
            self.df_floorsheet_summary = pd.DataFrame()
            return

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

        if self.df_floorsheet_summary is None or self.df_floorsheet_summary.empty:
            return pd.DataFrame()

        df_final = (self.df_floorsheet_summary
            .merge(self.df_client_summary_map[['clientCode', 'rmName']],
                   left_on='client_code', right_on='clientCode', how='left')
            .drop(columns='clientCode', errors='ignore')
            [['client_code', 'rmName', 'total_buy', 'total_sell',
              'total_buy_amount', 'total_sell_amount', 'total_turnover', 'total_commission']]
            .dropna(subset=['rmName'])
        )

        if df_final.empty:
            return pd.DataFrame()

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
                'client_code': 'Total Traders'
            })
        )

        # ROLE-BASED FILTERING: Only show own data if not Manager/Admin
        if self.role not in ['MANAGER', 'ADMIN']:
            rm_summary = rm_summary[rm_summary['BRO'].str.upper() == self.username.upper()]
            if rm_summary.empty:
                return pd.DataFrame()

        # Merge Yearly Target
        if self.bro_yearly_target is not None and not self.bro_yearly_target.empty:
            target_df = self.bro_yearly_target[['bro_code', 'target_amt']].copy()
            target_df.rename(columns={'bro_code': 'BRO'}, inplace=True)
            
            rm_summary = rm_summary.merge(target_df, on='BRO', how='left')
            rm_summary['Total Target'] = rm_summary['target_amt'].fillna(0).astype(float)

            # Achievement %
            rm_summary['Achievement %'] = (
                rm_summary['Total Turnover'] / rm_summary['Total Target'].replace(0, np.nan) * 100
            ).fillna(0).round(2)
            rm_summary['Achievement %'] = rm_summary['Achievement %'].astype(str) + '%'
            rm_summary['Achievement %'] = rm_summary['Achievement %'].replace('0.0%', '0%')

            rm_summary.drop(columns=['target_amt'], inplace=True, errors='ignore')
        else:
            rm_summary['Total Target'] = 0
            rm_summary['Achievement %'] = '0%'

        # Final formatting
        rm_summary = rm_summary.sort_values('Total Turnover', ascending=False)
        rm_summary.reset_index(drop=True, inplace=True)
        rm_summary.index = rm_summary.index + 1

        cols_order = ['BRO', 'Total Turnover', 'Total Buy Amount', 'Total Sell Amount',
                      'Total Commission Gain', 'Total Traders', 'Total Target', 'Achievement %']
        rm_summary = rm_summary[[c for c in cols_order if c in rm_summary.columns]]

        return helper.format_dataframe(rm_summary)

    def show(self):
        st.title("BRO Performance Dashboard")

        view_mode = st.radio(
            "Select Period",
            ["Today", "Yesterday", "1 Week", "1 Month", "3 Month", "6 Month", "YTD"],
            horizontal=True,
            key="period_selection"
        )

        with st.spinner(f"Loading {view_mode} data..."):
            rm_summary = self.extract_rm_sales_summary(view_mode)

        if rm_summary.empty:
            if self.role in ['MANAGER', 'ADMIN']:
                st.warning(f"No floorsheet data found for **{view_mode}**.")
            else:
                st.info(f"You have no trading activity in **{view_mode}**.")
            st.stop()

        # Dynamic title based on role
        title = ("BROs Performance" 
                 if self.role in ['MANAGER', 'ADMIN'] 
                 else f"Your Performance - {self.username.upper()}")

        st.subheader(f"{title} • {view_mode}")
        st.dataframe(rm_summary, use_container_width=True)

if __name__ == "__main__":
    RMAchievement().show()