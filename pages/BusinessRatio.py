import numpy as np
from utils.formatting import *
from db import db

import streamlit as st
import pandas as pd
from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from utils.formatting import *
from datetime import date, timedelta
from utils.custom_hotkey import activate_client_code_hotkey

intranet_engine = helper.get_holding_engine()

# @st.cache_data(ttl=1600)
# def get_floorsheet_by_date( selected_date: date):
#     query = """
#         SELECT *
#         FROM floorsheet
#         WHERE DATE(uploaded_at) = %s
#         ORDER BY uploaded_at DESC;
#     """
#     return pd.read_sql(query, intranet_engine, params=(selected_date,))

@st.cache_data(ttl=1600)
def get_floorsheet_by_date(selected_start_date: date, selected_end_date: date):
    query = """
        SELECT *
        FROM floorsheet
        WHERE DATE(uploaded_at) BETWEEN %s AND %s
        ORDER BY uploaded_at DESC;
    """
    return pd.read_sql(
        query,
        intranet_engine,
        params=(selected_start_date, selected_end_date)
    )




# ✔ Cache branch summary per date
@st.cache_data(ttl=1600)
def compute_branch_summary( df: pd.DataFrame):
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



    def render_page(self):
        mode = st.radio("Mode",["Manual Selection", "Select by Range"], horizontal=True)
        calc_button = st.empty()
        times = 100
        trade_day = 220
        if mode == 'Manual Selection':
            col1, col2, col3, col4,  col5 = st.columns([1.6, 1.6, 1, 1, 1])

            with col1:
                selected_start_date = st.date_input(
                    "Select StartDate",
                    value=date.today()
                )
            with col2:
                selected_end_date = st.date_input(
                    "Select End Date",
                    value=selected_start_date + timedelta(days=1)
                )
            
            manual_toggle = st.toggle("Change times/trade days")


            with col3:
                times = st.number_input(
                    "Times",
                    value=100,
                    disabled= not manual_toggle
                )

            with col4:
                trade_day = st.number_input(
                    "Trade Days",
                    value=220,
                    disabled=not manual_toggle
                )


            with col5:
                st.markdown("<br>", unsafe_allow_html=True)  # 👈 alignment spacer
                calc_button = st.button(
                    "Calculate Now",
                    icon="⏳",
                    width='content',
                    disabled=not manual_toggle
                )
        else:
            mode_range = st.radio("View", ['7 Days', '15 Days', '1 Month', '3 Months', '6 Months', 'YTD'], horizontal=True)
            today = date.today()
            if mode_range == '7 Days':
                selected_start_date = today - timedelta(days=7)
                selected_end_date = today
            elif mode_range == '15 Days':
                selected_start_date = today - timedelta(days=15)
                selected_end_date = today
            elif mode_range == '1 Month':
                selected_start_date = today - timedelta(days=30)
                selected_end_date = today
            elif mode_range == '3 Months':
                selected_start_date = today - timedelta(days=90)
                selected_end_date = today
            elif mode_range == '6 Months':
                selected_start_date = today - timedelta(days=180)
                selected_end_date = today
            elif mode_range == 'YTD':
                selected_start_date = date(2025, 7, 17)
                selected_end_date = today



        if mode == 'Select by Range':
            st.caption(f"Start Date: {selected_start_date} | End Date: {selected_end_date}")
        df = get_floorsheet_by_date(selected_start_date,selected_end_date)
        if df.empty:
            st.warning(f"No Floorsheet data found for {selected_start_date}. Please upload the floorsheet first or change the date", icon="⚠️")
            st.stop()
            
        display_df = compute_branch_summary(df)
        evening_duelist = db.get_due_list(selected_start_date=selected_start_date, selected_end_date=selected_end_date)
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