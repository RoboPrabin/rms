from nepali_datetime import date as nepali_date
from datetime import date
import numpy as np
import streamlit as st
import pandas as pd
from utils import helper
from datetime import datetime, timedelta
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config
from utils.custom_hotkey import activate_client_code_hotkey
class RMPerformance:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "rm"


        st.set_page_config("BRO Performance", page_icon="📈", layout='wide')

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
        self.holding_engine = helper.get_holding_engine()

        # Data placeholders
        self.df_floorsheet = None
        self.df_client_summary_map = None
        self.df_floorsheet_summary = None
        self.bro_yearly_target = None

        # Load static data once
        self.fetch_client_rm_map_db()
        self.fetch_bro_yearly_target_db()

    def is_trading_hours(self):
        """Returns True only between 11:00 AM and 3:00 PM (Nepal market time)"""
        now = datetime.now()
        start_time = now.replace(hour=11, minute=0, second=0, microsecond=0)
        end_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
        return start_time <= now <= end_time

    def fetch_client_rm_map_db(self):
        self.df_client_summary_map = pd.read_sql("SELECT * FROM client_rm_map", self.holding_engine)

    def fetch_bro_yearly_target_db(self):
        self.bro_yearly_target = pd.read_sql("SELECT * FROM bro_yearly_target", self.holding_engine)

    def fetch_floorsheet_db(self, period):
        conditions = {
            "Today":      '"uploaded_at"::timestamp::date = CURRENT_DATE',
            "Yesterday":  '"uploaded_at"::timestamp::date = CURRENT_DATE - INTERVAL \'1 day\'',
            "1 Week":     '"uploaded_at"::timestamp >= CURRENT_DATE - INTERVAL \'7 days\'',
            "15 Days":     '"uploaded_at"::timestamp >= CURRENT_DATE - INTERVAL \'15 days\'',
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

        if self.df_floorsheet_summary.empty:
            return pd.DataFrame(), pd.DataFrame()

        df_final = (self.df_floorsheet_summary
            .merge(self.df_client_summary_map[['clientCode', 'rmName']],
                   left_on='client_code', right_on='clientCode', how='left')
            .drop(columns='clientCode', errors='ignore')
            [['client_code', 'rmName', 'total_buy', 'total_sell',
              'total_buy_amount', 'total_sell_amount', 'total_turnover', 'total_commission']]
            .dropna(subset=['rmName'])
        )

        if df_final.empty:
            return pd.DataFrame(), pd.DataFrame()

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

        # Role-based filtering
        if self.role not in ['MANAGER', 'ADMIN']:
            rm_summary = rm_summary[rm_summary['BRO'].str.upper() == self.username.upper()]
            if rm_summary.empty:
                return pd.DataFrame(), pd.DataFrame()

        # Merge Target (keep numeric)
        if self.bro_yearly_target is not None and not self.bro_yearly_target.empty:
            target_df = self.bro_yearly_target[['bro_code', 'target_amt']].copy()
            target_df.rename(columns={'bro_code': 'BRO'}, inplace=True)
            rm_summary = rm_summary.merge(target_df, on='BRO', how='left')
            rm_summary['Total Target'] = pd.to_numeric(rm_summary['target_amt'], errors='coerce').fillna(0)
            rm_summary.drop(columns=['target_amt'], inplace=True, errors='ignore')
        else:
            rm_summary['Total Target'] = 0

        # Achievement % (numeric)
        rm_summary['Achievement %'] = (
            rm_summary['Total Turnover'] / rm_summary['Total Target'].replace(0, np.nan) * 100
        ).fillna(0).round(2)

        # Keep a clean numeric copy
        rm_summary_numeric = rm_summary.copy()

        # Format for display only
        # rm_summary_display = helper.format_dataframe(rm_summary_numeric.copy())
        rm_summary_display = rm_summary_numeric
        rm_summary_display['Achievement %'] = rm_summary_numeric['Achievement %'].astype(float)

        # Sort & index
        rm_summary_numeric = rm_summary_numeric.sort_values('Total Turnover', ascending=False).reset_index(drop=True)
        rm_summary_numeric.index += 1
        rm_summary_display = rm_summary_display.iloc[rm_summary_numeric.index - 1]  # align order

        return rm_summary_display, rm_summary_numeric



    def show(self):
        # st.title(f"📈 BRO Performance - {self.today_np_date}", anchor=False)
        title = ("All BROs Performance" if self.role in ['MANAGER', 'ADMIN', 'MANAGEMENT'] else f"{self.username.upper()}'s Performance")
        st.title(f"{title} : {self.today_np_date}", anchor=False)

        view_mode = st.radio(
            "Select Period",
            ["Today", "Yesterday", "1 Week", "15 Days", "1 Month", "3 Month", "6 Month", "YTD"],
            horizontal=True,
            key="period_selection"
        )

        # Load performance data (may be empty on "Today" morning)
        with st.spinner(f"Loading {view_mode} data..."):
            rm_display, rm_numeric = self.extract_rm_sales_summary(view_mode)

        # Always load yearly targets (even if no floorsheet)
        target_df = self.bro_yearly_target[['bro_code', 'target_amt']].copy()
        if target_df.empty:
            st.error("No yearly targets found in database!")
            st.stop()
        target_df.rename(columns={'bro_code': 'BRO'}, inplace=True)
        target_df['Total Target'] = pd.to_numeric(target_df['target_amt'], errors='coerce').fillna(0)
        target_df['Daily Target'] = (target_df['Total Target'] / 220).round(2)

        # Role-based filtering for targets
        if self.role not in ['MANAGER', 'ADMIN', 'MANAGEMENT']:
            target_df = target_df[target_df['BRO'].str.upper() == self.username.upper()]
            if target_df.empty:
                st.error("Your BRO code not found in target list!")
                st.stop()

        # Show main summary (if any activity)
        if not rm_numeric.empty:
            title = ("All BROs Performance" if self.role in ['MANAGER', 'ADMIN', 'MANAGEMENT'] else f"{self.username.upper()}'s Performance")
            st.subheader(f"• {view_mode}", anchor=False)
            rm_display.sort_values(by='Total Turnover', inplace=True, ascending=False)
            rm_display.reset_index(inplace=True, drop=True)
            rm_display.index = rm_display.index + 1
            numeric_cols = ['Total Turnover', 'Total Buy Amount', 'Total Sell Amount', 'Total Commission Gain', 'Total Traders', 'Total Target', 'Achievement %']
            styled_df = rm_display.style.format(
                {col: "{:,.2f}" for col in numeric_cols}
            )
            st.dataframe(styled_df, width='stretch')
        else:
            if view_mode != "Today":
                st.info(f"No trading activity found for **{view_mode}**.")

        # TODAY'S TARGET SECTION — ALWAYS SHOWS
        if view_mode == "Today":
            st.markdown("---")
            st.subheader("🎯 Today's Target (220 Trading Days/Year)", anchor=False)

            # Check if we have turnover today
            has_turnover_today = not rm_numeric.empty and (rm_numeric['Total Turnover'] > 0).any()

            if has_turnover_today:
                # Merge actual performance
                progress = rm_numeric[['BRO', 'Total Turnover', 'Total Target']].copy()
                progress = progress.merge(target_df[['BRO', 'Daily Target']], on='BRO', how='left')
                progress['Today %'] = ((progress['Total Turnover'] / progress['Daily Target']) * 100).round(2)
                progress['Remaining'] = (progress['Daily Target'] - progress['Total Turnover']).clip(lower=0).round(2)

                full_df = pd.DataFrame({
                    'BRO': progress['BRO'],
                    'Daily Target': progress['Daily Target'].apply(lambda x: f"{x:,.2f}"),
                    'Today Turnover': progress['Total Turnover'].apply(lambda x: f"{x:,.2f}"),
                    'Achieved Today': progress['Today %'].astype(str) ,
                    'Remaining': progress['Remaining'].apply(lambda x: f"{x:,.2f}")
                })

                st.success("Floorsheet uploaded — Here's today's performance:")
                full_df.index = full_df.index + 1
                st.dataframe(full_df, width='stretch')

            else:
                if self.role in ["MANAGER", "ADMIN"]:
                    target_only = pd.DataFrame({
                        "BRO": target_df['BRO'],
                        "BRO's Target": target_df['Daily Target']
                    })
                else:
                    target_only = pd.DataFrame({
                        "BRO": target_df['BRO'],
                        "Your Today's Target": target_df['Daily Target']
                    })

                # Show motivational message ONLY during trading hours (11 AM - 3 PM)
                if self.is_trading_hours():
                    if self.role == "BRO":
                        st.success("🔴 Market is LIVE — Crush your daily target today!")
                else:
                    if self.role in ["MANAGER", "ADMIN"]:
                        st.info("👇 Here is BRO's daily target for today:")
                    else:
                        st.info("👇 Here is your daily target for today:")
                target_only.sort_values(by="BRO's Target", inplace=True, ascending=False)
                target_only = target_only.reset_index(drop=True)
                target_only.index = target_only.index + 1
                numeric_cols = target_only.select_dtypes(include="number").columns

                styled_df = target_only.style.format(
                    {col: "{:,.2f}" for col in numeric_cols}
                )
                st.dataframe(styled_df, width=520)
                st.caption(f"*✍️ Performance will update automatically once the floorsheet upload completes ({config.FLOORSHEET_UPLOAD_TIIME}).*")

                
if __name__ == "__main__":
    RMPerformance().show()