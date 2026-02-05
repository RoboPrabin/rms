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




# # ✔ Cache branch summary per date
# @st.cache_data(ttl=1600)
# def compute_branch_summary( df: pd.DataFrame):
#     if "branch" not in df.columns:
#         return pd.DataFrame()

#     def branch_summary_func(g):
#         buy = g["transaction_type"] == "Buy"
#         sell = g["transaction_type"] == "Sell"
#         return pd.Series({
#             "purchase_turnover": g.loc[buy, "amount"].sum(),
#             "sales_turnover": g.loc[sell, "amount"].sum(),
#             "total": g["amount"].sum(),
#         })

#     df2 = (
#             df.groupby("branch", group_keys=False, observed=True)
#             .apply(lambda g: branch_summary_func(g), include_groups=False)
#             .reset_index()
#         )
#     return df2



# @st.cache_data(ttl=1600)
# def compute_branch_summary(df: pd.DataFrame):
#     if "branch" not in df.columns:
#         return pd.DataFrame()

#     def branch_summary_func(g):
#         buy = g["transaction_type"] == "Buy"
#         sell = g["transaction_type"] == "Sell"
#         return pd.Series({
#             "purchase_turnover": g.loc[buy, "amount"].mean(),
#             "sales_turnover": g.loc[sell, "amount"].mean(),
#             "total": g["amount"].mean(),
#         })

#     df2 = (
#         df.groupby("branch", group_keys=False, observed=True)
#         .apply(lambda g: branch_summary_func(g), include_groups=False)
#         .reset_index()
#     )
#     return df2

@st.cache_data(ttl=1600)
def compute_branch_summary(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = {"branch", "transaction_type", "amount", "quantity"}
    if not required_cols.issubset(df.columns):
        return pd.DataFrame()

    df = df.copy()

    df["buy_amount"] = df["amount"].where(df["transaction_type"] == "Buy")
    df["sell_amount"] = df["amount"].where(df["transaction_type"] == "Sell")
    df["weighted_amount"] = df["amount"] * df["quantity"]

    summary = (
        df.groupby("branch", observed=True)
          .agg(
              purchase_turnover=("buy_amount", "mean"),
              sales_turnover=("sell_amount", "mean"),
              total_weighted=("weighted_amount", "sum"),
              total_qty=("quantity", "sum"),
          )
          .reset_index()
    )

    summary["total"] = summary["total_weighted"] / summary["total_qty"]
    summary["total"] = summary["total"].fillna(0)

    return summary.drop(columns=["total_weighted", "total_qty"])



class BusinessRatio:
    def __init__(self):
        helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        st.set_page_config("Business Ratio", page_icon="⚖️", layout='wide')
        # Authentication
        # app_state.restore_state_from_query_params()
        # app_state.sync_query_params_from_session()
        # app_state.check_authenticaiton_state()
        app_state.enforce_authentication()
        app_state.sync_local_storage_to_session()
        activate_client_code_hotkey()
        self.username, self.role, self.branch = app_state.get_current_user_info()
        st.title("⚖️ Ratio of Due Amount with Business Turnover", anchor=False)
        # Sidebar
        navigation.render_sidebar()
        self.intranet_engine = helper.get_holding_engine()


    def show_manual_selection(self):
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
        numeric_cols = ["purchase_turnover", "sales_turnover", "total", "todayAdjustBalanceDueAmount", "expectedVolume", "Sortage/Exceed By"]  
        final_df.drop(columns=["volumeRequired", "tradeVolume", "opportunityCost"], inplace= True)
        final_df = coerce_numeric_columns(final_df, numeric_cols)
        final_df.sort_values(by="total", inplace=True, ascending=False)
        final_df.reset_index(inplace=True, drop=True)

        rename_map = {
            "branch": "Branch",
            "purchase_turnover": "Purchase Turnover",
            "sales_turnover": "Sales Turnover",
            "total": "Total",
            "volumeRequired": "Volume Required (Yearly)",
            "tradeVolume": "Trade Volume",
            "opportunityCost": "Opportunity Cost",
            "todayAdjustBalanceDueAmount": "Adjusted Balance Due Amount",
            "expectedVolume": "Expected Volume",
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



    def show_range_ui(self):
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
        period = (selected_end_date - selected_start_date).days

        st.caption(f"Start Date: {selected_start_date} | End Date: {selected_end_date} | Period: {period} days")
        
        df = get_floorsheet_by_date(selected_start_date,selected_end_date)
        if df.empty:
            st.warning(f"No Floorsheet data found for {selected_start_date}. Please upload the floorsheet first or change the date", icon="⚠️")
            st.stop()
            
        display_df = compute_branch_summary(df)
        evening_duelist = db.get_due_list(selected_start_date=selected_start_date, selected_end_date=selected_end_date)
        if len(evening_duelist) == 0:
            st.error(f"Evening Due list not found. Please contact your admin.", icon="🚨")
            st.stop()

        # branch_due_df = (
        #         evening_duelist
        #             .groupby("branch", as_index=False)
        #             .agg(todayAdjustBalanceDueAmount=("adjustedBalance", "sum"))
        #     )

        branch_due_df = (
            evening_duelist
                .groupby("branch", as_index=False)
                .agg(todayAdjustBalanceDueAmount=("adjustedBalance", "mean"))
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

        # final_df["volumeRequired"] = final_df["todayAdjustBalanceDueAmount"] * 100
        # final_df["tradeVolume"] = final_df["total"] * total_days
        # final_df["opportunityCost"] = final_df["total"] * 40
        # final_df['expectedVolume'] = final_df["volumeRequired"] / 220
        # final_df['expectationmet'] = (final_df['total'] > final_df['expectedTimes']).map({True: "YES", False: "NO"})

        total_days = 365
        total_expected_times = 120
        final_df['expectedTimes'] = (total_expected_times/total_days) * period
        final_df['Performance in Times'] = (final_df['total']/final_df['todayAdjustBalanceDueAmount']) * period

        final_df['expectationmet'] = (final_df['expectedTimes'] >= final_df['Performance in Times']).map({True: "NO", False: "YES"})
        final_df['Sortage/Exceed By Times'] = final_df['Performance in Times'] - final_df["expectedTimes"]

        column_order = ["branch","purchase_turnover", "sales_turnover", "total", "todayAdjustBalanceDueAmount", "expectedTimes", "Performance in Times" ,"expectationmet", "Sortage/Exceed By Times"]
        final_df = final_df[column_order]
        numeric_cols = ["purchase_turnover", "sales_turnover", "total", "todayAdjustBalanceDueAmount", "expectedTimes", "Performance in Times","Sortage/Exceed By Times"]  
        final_df = coerce_numeric_columns(final_df, numeric_cols)
        final_df.sort_values(by="total", inplace=True, ascending=False)
        final_df.reset_index(inplace=True, drop=True)
        
        rename_map = {
            "branch": "Branch",
            "purchase_turnover": "Average Buy",
            "sales_turnover": "Average Sell",
            "total": "Average Turnover",
            # "volumeRequired": "Volume Required (Yearly)",
            "tradeVolume": "Trade Volume",
            "opportunityCost": "Opportunity Cost",
            "todayAdjustBalanceDueAmount": "Average Adjusted Due",
            "expectedTimes": "Expected Times",
            "expectationmet": "Expectation Met",
            # "Performance in Times":"Performance in Times"
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



    def render_page(self):
        mode = st.radio("Mode",["Manual Selection", "Select by Period"], horizontal=True)
        if mode == 'Manual Selection':
            self.show_manual_selection()
        elif mode == 'Select by Period':
            self.show_range_ui()
        

        




if __name__ == "__main__":
    BusinessRatio().render_page()