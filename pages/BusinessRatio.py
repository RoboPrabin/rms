import numpy as np
from utils.formatting import *
from db import db

import streamlit as st
import pandas as pd
from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils.formatting import *
from datetime import date
from utils.custom_hotkey import activate_client_code_hotkey


class BusinessRatio:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        st.set_page_config("Business Ratio", page_icon="⚖️", layout='wide')
        # Authentication
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        activate_client_code_hotkey()
        self.username, self.role = app_state.get_current_user_info()
        st.title("⚖️ Ratio of Due Amount with Business Turnover", anchor=False)
        # Sidebar
        navigation.render_sidebar()
        self.intranet_engine = helper.get_holding_engine()


    @st.cache_data(ttl=3600)
    def get_floorsheet_by_date(_self, selected_date: date):
        query = """
            SELECT *
            FROM floorsheet
            WHERE DATE(uploaded_at) = %s
            ORDER BY uploaded_at DESC;
        """
        return pd.read_sql(query, _self.intranet_engine, params=(selected_date,))
    
    
    # ✔ Cache branch summary per date
    @st.cache_data(ttl=3600)
    def compute_branch_summary(_self, df: pd.DataFrame):
        if "branch" not in df.columns:
            return pd.DataFrame()

        def branch_summary_func(g):
            buy = g["transaction_type"] == "Buy"
            sell = g["transaction_type"] == "Sell"
            return pd.Series({
                "purchase_turnover": g.loc[buy, "amount"].sum(),
                "sales_turnover": g.loc[sell, "amount"].sum(),
                "total": g["amount"].sum(),
            })

        df2 = (
                df.groupby("branch", group_keys=False, observed=True)
                .apply(lambda g: branch_summary_func(g), include_groups=False)
                .reset_index()
            )
        return df2

    def render_page(self):
        col1, col2, col3,  col5 = st.columns([1, 1, 1, 1])

        with col1:
            selected_date = st.date_input(
                "Select Date",
                value=date.today()
            )

        with col2:
            times = st.number_input(
                "Times",
                value=100
            )

        with col3:
            trade_day = st.number_input(
                "Trade Days",
                value=220
            )

        # with col4:
        #     rate = st.number_input(
        #         "Rate",
        #         value=40
        #     )

        with col5:
            st.markdown("<br>", unsafe_allow_html=True)  # 👈 alignment spacer
            calc_button = st.button(
                "Calculate Now",
                icon="⏳",
                use_container_width=True
            )

            
        df = self.get_floorsheet_by_date(selected_date)
        if df.empty:
            st.warning(f"No Floorsheet data found for {selected_date}. Please upload the floorsheet first or change the date", icon="⚠️")
            st.stop()
            
        display_df = self.compute_branch_summary(df)
        evening_duelist = db.get_due_list(selected_date=selected_date)
        if len(evening_duelist) == 0:
            st.error(f"Evening Due list not found. Please contact your admin.", icon="🚨")
            st.stop()

        branch_due_df = (
                evening_duelist
                    .groupby("branch", as_index=False)
                    .agg(todayAdjustBalanceDueAmount=("adjustedBalance", "sum"))
            )

        final_df = (
                display_df
                    .merge(
                        branch_due_df,
                        on="branch",
                        how="left"
                    )
            )
        final_df["todayAdjustBalanceDueAmount"] = (
            final_df["todayAdjustBalanceDueAmount"]
                .fillna(0)
        )
        if calc_button:
            final_df["volumeRequired"] = final_df["todayAdjustBalanceDueAmount"] * times
            final_df["tradeVolume"] = final_df["total"] * trade_day
            final_df["opportunityCost"] = final_df["total"] * 40
            final_df['expectedVolume'] = final_df["volumeRequired"] / trade_day
            final_df['expectationmet'] = (final_df['total'] > final_df['expectedVolume']).map({True: "YES", False: "NO"})
            final_df['Sortage/Exceed By'] = final_df['expectedVolume'] - final_df["total"]
        else:
            final_df["volumeRequired"] = final_df["todayAdjustBalanceDueAmount"] * 100
            final_df["tradeVolume"] = final_df["total"] * 220
            final_df["opportunityCost"] = final_df["total"] * 40
            final_df['expectedVolume'] = final_df["volumeRequired"] / 220
            final_df['expectationmet'] = (final_df['total'] > final_df['expectedVolume']).map({True: "YES", False: "NO"})
            final_df['Sortage/Exceed By'] = final_df["total"] - final_df['expectedVolume']

  
  
        # final_df['volumeCheck'] = (final_df['todayAdjustBalanceDueAmount'] * 100) / 220
        # print(evening_duelist.columns.tolist())
        # total_adjusted_balance = evening_duelist['adjustedBalance'].sum()
        # total_adjusted_balance_bnp = evening_duelist.query("branch == 'BNP'")['adjustedBalance'].sum()
       
        # st.badge(f"total bnp adjust balance : {total_adjusted_balance_bnp}")
        # st.badge(f"Total Adjusted Balance: {total_adjusted_balance_bnp}")
        column_order = ["branch","purchase_turnover", "sales_turnover", "total", "todayAdjustBalanceDueAmount", "expectedVolume", "expectationmet"  ,"volumeRequired", "tradeVolume", "opportunityCost", "Sortage/Exceed By"]
        final_df = final_df[column_order]
        numeric_cols = ["purchase_turnover", "sales_turnover", "total", "todayAdjustBalanceDueAmount", "expectedVolume", "Sortage/Exceed By"]  # add more if needed
        # numeric_cols = ["purchase_turnover", "sales_turnover", "total", "volumeRequired", "tradeVolume", "opportunityCost" ,"todayAdjustBalanceDueAmount", "expectedVolume"]  # add more if needed
        final_df.drop(columns=["volumeRequired", "tradeVolume", "opportunityCost"], inplace= True)
        # Ensure numeric columns are clean
        final_df = coerce_numeric_columns(final_df, numeric_cols)
        
        
        
        final_df.sort_values(by="total", inplace=True, ascending=False)
        final_df.reset_index(inplace=True, drop=True)
        # final_df = final_df.rename(columns=helper.camel_to_title)
        
        
        
        rename_map = {
            "branch": "Branch",
            "purchase_turnover": "Purchase Turnover",
            "sales_turnover": "Sales Turnover",
            "total": "Total",
            "volumeRequired": "Volume Required (Yearly)",
            "tradeVolume": "Trade Volume",
            "opportunityCost": "Opportunity Cost",
            "todayAdjustBalanceDueAmount": "Today Adjust Balance Due Amount",
            "expectedVolume": "Expected Volume (Daily)",
            "expectationmet": "Expectation Met"
        }

        final_df.rename(columns=rename_map, inplace=True)
        
        numeric_cols_renamed = [rename_map.get(c, c) for c in numeric_cols]
        # ✅ Add total row
        totals = {col: final_df[col].sum() for col in numeric_cols_renamed}
        totals["Branch"] = "TOTAL"
        final_df = pd.concat([final_df, pd.DataFrame([totals])], ignore_index=True)
        
        
        final_df.index = final_df.index + 1
        # After concatenating totals
        final_df.index = final_df.index.astype(str)
        final_df.index = final_df.index[:-1].tolist() + [""]


        def highlight_total_row(row):
            if row["Branch"] == "TOTAL":
                return ["font-weight: bold;"] * len(row)
            return [""] * len(row)


        styled_df = (
            final_df.style
                .apply(highlight_total_row, axis=1)
                .map(highlight_negative, subset=numeric_cols_renamed)
                .format({col: accounting_format for col in numeric_cols_renamed})
                .pipe(right_align_headers)
        )
        
        st.dataframe(styled_df, width="stretch")




if __name__ == "__main__":
    BusinessRatio().render_page()