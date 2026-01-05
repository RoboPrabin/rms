import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from nepali_datetime import date as nepali_date

from db import db
from utils import helper
from utils.formatting import *
from utils.custom_hotkey import activate_client_code_hotkey
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation


# ---------------------------------------------------------
# 🔥 CACHED DATA LAYER (PURE FUNCTIONS ONLY)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def load_floorsheet_base(engine, selected_date):
    start_ts = f"{selected_date} 00:00:00"
    end_ts = f"{selected_date + timedelta(days=1)} 00:00:00"

    query = """
        SELECT
            f.clientcode,
            f.clientname,
            f.branch,
            f.symbol,
            f.transaction_type,
            f.quantity,
            f.amount,
            f.stockcomm,
            COALESCE(crm."rmName", 'N/A') AS rmName
        FROM floorsheet f
        LEFT JOIN client_rm_map crm
            ON crm."clientCode" = f.clientcode
        WHERE f.uploaded_at >= %s
        AND f.uploaded_at < %s
    """
    return pd.read_sql(query, engine, params=(start_ts, end_ts))



def enrich_with_rm(floorsheet_df: pd.DataFrame, client_rm_map_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds rmName to floorsheet dataframe by matching clientcode.
    """

    # Normalize column names (defensive programming)
    floorsheet_df = floorsheet_df.copy()
    client_rm_map_df = client_rm_map_df.copy()

    floorsheet_df.columns = floorsheet_df.columns.str.lower()
    client_rm_map_df.columns = client_rm_map_df.columns.str.lower()

    # Expected columns in client_rm_map
    # clientcode | rmname
    enriched_df = floorsheet_df.merge(
        client_rm_map_df[["clientcode", "rmname"]],
        on="clientcode",
        how="left"
    )

    # Optional: fill missing RM names
    enriched_df["rmname"] = enriched_df["rmname"].fillna("UNASSIGNED")

    return enriched_df


@st.cache_data(ttl=3600)
def load_rm_clients(engine, alias):
    """
    Load client list for BRO.
    """
    query = """
        SELECT "clientCode"
        FROM client_rm_map
        WHERE "rmName" = %s
    """
    df = pd.read_sql(query, engine, params=(alias,))
    return set(df["clientCode"].tolist())


# ---------------------------------------------------------
# 📊 AGGREGATION LAYER
# ---------------------------------------------------------

def compute_top_buy_sell(df):
    buy = (
        df[df.transaction_type == "Buy"]
        .groupby(["rmname", "clientcode", "clientname", "branch" ], as_index=False)
        .amount.sum()
        .sort_values("amount", ascending=False)
        .head(10)
        .rename(columns={"amount": "Total Buy"})
    )

    sell = (
        df[df.transaction_type == "Sell"]
        .groupby(["rmname", "clientcode", "clientname", "branch"], as_index=False)
        .amount.sum()
        .sort_values("amount", ascending=False)
        .head(10)
        .rename(columns={"amount": "Total Sell"})
    )

    return buy, sell


def compute_commission(df):
    return (
        df.groupby([ "rmname", "clientcode", "clientname", "branch"], as_index=False)
        .stockcomm.sum()
        .sort_values("stockcomm", ascending=False)
        .rename(columns={"stockcomm": "Total Commission"})
    )


def compute_top_traded(df):
    return (
        df.groupby(
            ["rmname", "symbol", "transaction_type", "clientcode", "branch", "clientname"],
            as_index=False
        )
        .agg(
            total_quantity=("quantity", "sum"),
            total_amount=("amount", "sum")
        )
        .sort_values("total_amount", ascending=False)
        .head(20)
    )


# ---------------------------------------------------------
# 🖥️ DASHBOARD CLASS
# ---------------------------------------------------------

class Dashboard:

    def __init__(self):
        # helper.eliminate_top_padding()
        helper.eliminate_top_margin(margin_top="-8rem")
        st.session_state.active_menu = ""
        st.set_page_config("Dashboard", page_icon="🏠", layout="wide")

        # --- Dates ---
        self.today_date = datetime.now().date()
        self.today_np_date = nepali_date.today()

        # --- Auth ---
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()

        self.username, self.role = app_state.get_current_user_info()
        activate_client_code_hotkey()
        navigation.render_sidebar()

        # --- DB ---
        self.engine = helper.get_holding_engine()

        # --- Date selection ---
        yesterday = self.today_date
        st.title("📊 Business Insights", anchor=False)
        self.selected_date = st.date_input(
            "Select Business date",
            value=yesterday,
            width=400
        )
        self.week_day = self.selected_date.strftime("%A")

    # ---------------------------------------------------------
    # 🚀 MAIN RENDER
    # ---------------------------------------------------------

    def show(self):
        with st.spinner("Preparing insights..."):
            df_base = load_floorsheet_base(self.engine, self.selected_date)

            if self.role == "BRO":
                alias = helper.get_alias_name(self.username)
                clients = load_rm_clients(self.engine, alias)
                df_base = df_base[df_base.clientcode.isin(clients)]

        # --- Aggregations ---
        df_buy, df_sell = compute_top_buy_sell(df_base)
        df_comm = compute_commission(df_base)
        df_traded = compute_top_traded(df_base)

        # --- UI Mode ---
        if self.role in ["ADMIN", "MANAGEMENT"]:
            mode = st.radio(
                "Mode",
                ["Top Performers", "Top Traded Stocks", "Top Brokers" ,"Nepse Commission"],
                horizontal=True
            )
        else:
            mode = st.radio(
                "Mode",
                ["Top Performers", "Top Traded Stocks", "Top Brokers"],
                horizontal=True
            )

        # ---------------------------------------------------------
        # 📈 TOP PERFORMERS
        # ---------------------------------------------------------
        if mode == "Top Performers":
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 Top 10 Buyers")
                df_buy = df_buy.rename(columns={
                    "rmname": "BRO", 
                    "clientcode": "Client Code",
                    "clientname": "Client Name",
                    "branch": "Branch",
                })
                st.dataframe(
                    df_buy.style.format({"Total Buy": accounting_format}),
                    width="stretch",
                    hide_index=True
                )

            with col2:
                st.subheader("📉 Top 10 Sellers")
                df_sell = df_sell.rename(columns={
                    "rmname": "BRO",
                    "clientcode": "Client Code",
                    "clientname": "Client Name",
                    "branch": "Branch",
                })
                st.dataframe(
                    df_sell.style.format({"Total Sell": accounting_format}),
                    width="stretch",
                    hide_index=True
                )

        # ---------------------------------------------------------
        # 💰 COMMISSION
        # ---------------------------------------------------------
        elif mode == "Nepse Commission":
            # st.subheader("💰 Total Commission")

            total_comm = df_comm["Total Commission"].sum()
            st.badge(f"Total Nepse Commission: {total_comm:,.2f}", color="green")
            df_comm.reset_index(inplace=True, drop=True)
            df_comm.index = df_comm.index + 1
            df_comm = df_comm.rename(columns={
                "clientcode": "Client Code",
                "clientname": "Client Name",
                "branch": "Branch",
                "rmname": "BRO"
            })

            st.dataframe(
                df_comm.style.format({"Total Commission": accounting_format}),
                width="stretch"
            )

        # ---------------------------------------------------------
        # 📊 TOP TRADED
        # ---------------------------------------------------------
        elif mode == "Top Traded Stocks":
            st.subheader("📊 Top Traded Stocks")

            df_buy_traded = df_traded[df_traded.transaction_type == "Buy"]
            df_sell_traded = df_traded[df_traded.transaction_type == "Sell"]

            tab1, tab2 = st.tabs(["🟥 Buyers", "🟩 Sellers"])

            with tab1:
                fig = px.pie(
                    df_buy_traded,
                    names="symbol",
                    values="total_quantity",
                    title="Top Buy Quantity",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                fig = px.pie(
                    df_sell_traded,
                    names="symbol",
                    values="total_quantity",
                    title="Top Sell Quantity",
                    hole=0.4
                )
                st.plotly_chart(fig, use_container_width=True)

        elif mode == "Top Brokers":
            # date_str = self.selected_date.strftime('%Y-%m-%d')
            df = db.fetch_top_brokers(date=self.selected_date)
            
            df.drop(columns=['date', 'DT_Row_Index'], inplace=True)
            df.rename(columns={"name":"Broker Name", "number": "Broker No.", "buyerAmount": "Buyer Amount (Rs.)", 
                               "sellerAmount": "Seller Amount (Rs.)", "totalAmount":"Total Amount (Rs.)",
                               "differ": "Difference (Rs.)", "matchingAmout": "Matching Amount (Rs.)"}, inplace=True)
            df.index = df.index + 1
            numeric_cols = df.columns.difference(['Broker Name', 'Broker No.'])
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            if not df.empty:
                idx = df.index[df['Broker Name'] == 'Trishakti Securities Public Limited'].tolist()
                st.badge(f"Trishakti's Rank: {idx[0]}", color='green')
                st.dataframe(df.style.format({col: "{:,.0f}" for col in numeric_cols}))
            else:
                st.info("No data available for selected date.")
# ---------------------------------------------------------
# ▶ RUN APP
# ---------------------------------------------------------
if __name__ == "__main__":
    Dashboard().show()













# import streamlit_hotkeys as hotkeys
# import plotly.express as px
# from datetime import datetime, timedelta
# from nepali_datetime import date as nepali_date
# from datetime import datetime
# import streamlit as st
# import pandas as pd
# from utils import helper
# import streamlit_bridge.app_state as app_state
# import streamlit_bridge.navigation as navigation
# from utils.formatting import *
# from utils.custom_hotkey import activate_client_code_hotkey
# class Dashboard:
#     def __init__(self):
#         helper.eliminate_top_padding()
#         st.set_page_config("Dashboard", page_icon="🏠", layout='wide')

#         # Dates
#         self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
#         self.today_date = datetime.now().strftime("%Y-%m-%d")
#         self.today_np_date = nepali_date.today()

#         # Authentication
#         app_state.restore_state_from_query_params()
#         app_state.sync_query_params_from_session()
#         app_state.check_authenticaiton_state()


#         self.username, self.role = app_state.get_current_user_info()
#         activate_client_code_hotkey()

#         # Sidebar
#         navigation.render_sidebar()

#         # DB Engine
#         self.engine = helper.get_holding_engine()
#         if self.has_today_floorsheet_data():
#             yesterday = datetime.now() - timedelta(days=0)
#         else:
#             st.info(f"Todays's floorsheet not uploaded yet. Showing yesterday data.", icon="ℹ️")
#             yesterday = datetime.now() - timedelta(days=1)

#         st.title("📊 Business Insights", anchor=False)

#         self.yesterday_date = yesterday.strftime("%Y-%m-%d")
#         self.yesterday_date_input = st.date_input("Select date", value=yesterday, width=400)
#         self.week_day = self.yesterday_date_input.strftime("%A")




#     def has_today_floorsheet_data(self):
#         query = """
#             SELECT 1
#             FROM floorsheet
#             WHERE DATE(uploaded_at) = %s
#             LIMIT 1;
#         """

#         df = pd.read_sql(query, self.engine, params=(self.today_date,))

#         return not df.empty
    
    
#     # ---------------------------------------------------------
#     # ✅ SQL Queries
#     # ---------------------------------------------------------
#     @st.cache_data(ttl=3600)
#     def get_top_buy_sell_commission(_self, selected_date):

#         query_buy = """
#             SELECT 
#                 f.clientcode,
#                 f.clientname,
#                 f.branch,
#                 COALESCE(crm."rmName", 'N/A') AS rmName,
#                 SUM(f.amount) AS total_buy
#             FROM floorsheet f
#             LEFT JOIN client_rm_map crm 
#                 ON crm."clientCode" = f.clientcode
#             WHERE f.transaction_type = 'Buy'
#             AND DATE(f.uploaded_at) = %s
#             GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
#             ORDER BY total_buy DESC
#             LIMIT 10;
#         """

#         query_sell = """
#            SELECT 
#                 f.clientcode,
#                 f.clientname,
#                 f.branch,
#                 COALESCE(crm."rmName", 'N/A') AS rmName,
#                 SUM(f.amount) AS total_sell
#             FROM floorsheet f
#             LEFT JOIN client_rm_map crm 
#                 ON crm."clientCode" = f.clientcode
#             WHERE f.transaction_type = 'Sell'
#             AND DATE(f.uploaded_at) = %s
#             GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
#             ORDER BY total_sell DESC
#             LIMIT 10;
#         """

#         query_comm = """
#             SELECT 
#                 f.clientcode,
#                 f.clientname,
#                 f.branch,
#                 COALESCE(crm."rmName", 'N/A') AS rmName,
#                 SUM(f.stockcomm) AS total_commission
#             FROM floorsheet f
#             LEFT JOIN client_rm_map crm 
#                 ON crm."clientCode" = f.clientcode
#             WHERE DATE(f.uploaded_at) = %s
#             GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
#             ORDER BY total_commission DESC
#         """

#         query_traded = """
#             SELECT 
#                 f.symbol,
#                 f.transaction_type,
#                 f.clientcode,
#                 f.branch,
#                 f.clientname,
#                 COALESCE(crm."rmName", 'N/A') AS rmName,
#                 SUM(f.quantity) AS total_quantity,
#                 SUM(f.amount) AS total_amount
#             FROM floorsheet f
#             LEFT JOIN client_rm_map crm 
#                 ON crm."clientCode" = f.clientcode
#             WHERE DATE(f.uploaded_at) = %s
#             GROUP BY 
#                 f.symbol,
#                 f.transaction_type,
#                 f.clientcode,
#                 f.branch,
#                 f.clientname,
#                 rmName
#             ORDER BY total_amount DESC
#             LIMIT 20;
#         """
#         print(selected_date)
#         df_traded = pd.read_sql(query_traded, _self.engine, params=(selected_date,))
#         df_buy = pd.read_sql(query_buy, _self.engine, params=(selected_date,))
#         df_sell = pd.read_sql(query_sell, _self.engine, params=(selected_date,))
#         df_comm = pd.read_sql(query_comm, _self.engine, params=(selected_date,))

#         return df_buy, df_sell, df_comm, df_traded
   
   
    
#     # ---------------------------------------------------------
#     # ✅ SQL Queries
#     # ---------------------------------------------------------
#     @st.cache_data(ttl=3600)
#     def get_top_buy_sell_commission_of_loggedin_user(_self, username, selected_date):
#         # GET Alias
#         alias = helper.get_alias_name(_self.username)
#         # 1) Get all clientCodes assigned to this RM
#         query_clients = """
#             SELECT "clientCode"
#             FROM client_rm_map
#             WHERE "rmName" = %s
#         """
#         df_clients = pd.read_sql(query_clients, _self.engine, params=(alias,))

#         # If RM has no clients, return empty frames
#         if df_clients.empty:
#             empty = pd.DataFrame()
#             return empty, empty, empty, empty

#         client_list = tuple(df_clients["clientCode"].tolist())

#         # 2) Queries filtered by client_list
#         query_buy = """
#             SELECT 
#                 f.clientcode,
#                 f.clientname,
#                 f.branch,
#                 COALESCE(crm."rmName", 'N/A') AS rmName,
#                 SUM(f.amount) AS total_buy
#             FROM floorsheet f
#             LEFT JOIN client_rm_map crm 
#                 ON crm."clientCode" = f.clientcode
#             WHERE f.transaction_type = 'Buy'
#             AND DATE(f.uploaded_at) = %s
#             AND f.clientcode IN %s
#             GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
#             ORDER BY total_buy DESC
#             LIMIT 10;
#         """

#         query_sell = """
#             SELECT 
#                 f.clientcode,
#                 f.clientname,
#                 f.branch,
#                 COALESCE(crm."rmName", 'N/A') AS rmName,
#                 SUM(f.amount) AS total_sell
#             FROM floorsheet f
#             LEFT JOIN client_rm_map crm 
#                 ON crm."clientCode" = f.clientcode
#             WHERE f.transaction_type = 'Sell'
#             AND DATE(f.uploaded_at) = %s
#             AND f.clientcode IN %s
#             GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
#             ORDER BY total_sell DESC
#             LIMIT 10;
#         """

#         query_comm = """
#             SELECT 
#                 f.clientcode,
#                 f.clientname,
#                 f.branch,
#                 COALESCE(crm."rmName", 'N/A') AS rmName,
#                 SUM(f.stockcomm) AS total_commission
#             FROM floorsheet f
#             LEFT JOIN client_rm_map crm 
#                 ON crm."clientCode" = f.clientcode
#             WHERE DATE(f.uploaded_at) = %s
#             AND f.clientcode IN %s
#             GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
#             ORDER BY total_commission DESC
#             LIMIT 10;
#         """

#         query_traded = """
#             SELECT 
#                 f.symbol,
#                 f.transaction_type,
#                 f.clientcode,
#                 f.branch,
#                 f.clientname,
#                 COALESCE(crm."rmName", 'N/A') AS rmName,
#                 SUM(f.quantity) AS total_quantity,
#                 SUM(f.amount) AS total_amount
#             FROM floorsheet f
#             LEFT JOIN client_rm_map crm 
#                 ON crm."clientCode" = f.clientcode
#             WHERE DATE(f.uploaded_at) = %s
#             AND f.clientcode IN %s
#             GROUP BY 
#                 f.symbol,
#                 f.transaction_type,
#                 f.clientcode,
#                 f.branch,
#                 f.clientname,
#                 rmName
#             ORDER BY total_amount DESC
#             LIMIT 20;
#         """

#         params = (selected_date, client_list)

#         df_buy = pd.read_sql(query_buy, _self.engine, params=params)
#         df_sell = pd.read_sql(query_sell, _self.engine, params=params)
#         df_comm = pd.read_sql(query_comm, _self.engine, params=params)
#         df_traded = pd.read_sql(query_traded, _self.engine, params=params)

#         return df_buy, df_sell, df_comm, df_traded

    
#     # ---------------------------------------------------------
#     # ✅ UI Rendering
#     # ---------------------------------------------------------
#     def show(self):
#         if self.role == "BRO":
#             df_buy, df_sell, df_comm, df_traded = self.get_top_buy_sell_commission_of_loggedin_user(username=self.username, selected_date = self.yesterday_date_input)
#         else:
#             df_buy, df_sell, df_comm, df_traded = self.get_top_buy_sell_commission(selected_date = self.yesterday_date_input)

#         if self.role in ["MANAGEMENT", "ADMIN"]:
#             mode = st.radio("Mode", ["Top Performers",  "Top Traded Stocks",  "Commission Gained",], horizontal=True, index=0)
#         else:
#             mode = st.radio("Mode", ["Top Performers", "Top Traded Stocks"], horizontal=True, index=0)

#         # st.subheader(f"Traders Summary : {self.yesterday_date} ({self.week_day})", anchor=False)
#         if mode=="Top Performers":
#             # Two-column layout for buyers & sellers
#             col1, col2 = st.columns(2)

#             with col1:
#                 st.subheader("📈 Top 10 Buyers", anchor=False)
#                 df_buy.index = df_buy.index + 1
#                 df_buy.rename(columns={"clientcode":"Client Code","clientname":"Client Name" ,"branch":"Branch" ,"total_buy":"Total Buy", "rmname":"BRO"}, inplace=True)
#                 # st.dataframe(df_buy, use_container_width=True, column_order=["BRO", "Client Code", "Client Name", "Branch", "Total Buy"])
#                 df_buy = df_buy[["BRO", "Client Code", "Client Name", "Branch", "Total Buy"]]
#                 df_buy = coerce_numeric_columns(df_buy, ["Total Buy"])

#                 # fig = px.pie(
#                 # df_buy,
#                 # names="Client Name",
#                 # values="Total Buy",
#                 # title="Top 10 Buyers",
#                 # hole=0.4  
#                 # )
#                 # fig.update_traces(textposition='outside', textinfo='percent+label')
#                 # st.plotly_chart(fig, use_container_width=True,)
                
#                 st.dataframe(
#                     df_buy.style
#                     .format({col: accounting_format for col in ['Total Buy'] if col in df_buy.columns})
#                     .map(highlight_negative, subset=[c for c in ['Total Buy'] if c in df_buy.columns]),
#                     width='stretch',
#                     hide_index=True
#                 )

#             with col2:
#                 # st.markdown("### 📉 Top 10 Sellers")
#                 st.subheader("📉 Top 10 Sellers", anchor=False)
#                 df_sell.index = df_sell.index + 1
#                 df_sell.rename(columns={"clientcode":"Client Code","clientname":"Client Name" ,"branch":"Branch" ,"total_sell":"Total Sell","rmname":"BRO"}, inplace=True)

#                 df_sell = df_sell[["BRO", "Client Code", "Client Name", "Branch", "Total Sell"]]
#                 df_sell = coerce_numeric_columns(df_sell, ["Total Sell"])


#                 # fig = px.pie(
#                 # df_sell,
#                 # names="Client Name",
#                 # values="Total Sell",
#                 # title="Top 10 Sellers",
#                 # hole=0.4  
#                 # )
#                 # fig.update_traces(textposition='outside', textinfo='percent+label')
#                 # st.plotly_chart(fig, use_container_width=True,)


#                 st.dataframe(
#                     df_sell.style
#                     .format({col: accounting_format for col in ['Total Sell'] if col in df_sell.columns})
#                     .map(highlight_negative, subset=[c for c in ['Total Sell'] if c in df_sell.columns]),
#                     width='stretch',
#                     hide_index=True
#                 )
        
#         elif mode == "Commission Gained":
#             # Commission providers
#             st.markdown(f"### 💰 Total Commission Earned")
#             # st.markdown(f"### 💰 Total Commission earned on {self.yesterday_date}, {self.week_day}")
#             df_comm.index = df_comm.index + 1
#             df_comm.rename(columns={"clientcode":"Client Code","clientname":"Client Name" ,"branch":"Branch" , "total_commission":"Total Commission","rmname":"BRO"}, inplace=True)
#             total_comm = round(df_comm['Total Commission'].sum(), 2)
#             df_comm = df_comm[["BRO", "Client Code", "Client Name", "Branch", "Total Commission"]]
#             df_comm = coerce_numeric_columns(df_comm, ["Total Commission"])

#             # fig = px.pie(
#             #     df_comm,
#             #     names="Client Name",
#             #     values="Total Commission",
#             #     title="Commission Contribution Share",
#             #     hole=0.4  
#             # )
#             # fig.update_traces(textposition='outside', textinfo='percent+label')
#             # st.plotly_chart(fig, use_container_width=True,)

#             st.markdown("---")
#             st.badge(f"Total Commission: {total_comm:,.2f}", color='green')
#             st.dataframe(
#                 df_comm.style
#                 .format({col: accounting_format for col in ['Total Commission'] if col in df_comm.columns})
#                 .map(highlight_negative, subset=[c for c in ['Total Commission'] if c in df_comm.columns]),
#                 width='stretch'
#             )

#         elif mode == "Top Traded Stocks":
#             st.markdown("### 📊 Top Traded Stocks")

#             # --- Split Buy/Sell ---
#             df_buy_traded = df_traded[df_traded["transaction_type"] == "Buy"].copy()
#             df_sell_traded = df_traded[df_traded["transaction_type"] == "Sell"].copy()

#             # --- Rename columns ---
#             rename_map = {
#                 "symbol": "Symbol",
#                 "transaction_type": "Type",
#                 "branch": "Branch",
#                 "clientcode": "Client Code",
#                 "clientname": "Client Name",
#                 "rmname": "BRO",
#                 "total_quantity": "Total Quantity",
#                 "total_amount": "Total Amount"
#             }

#             df_buy_traded.rename(columns=rename_map, inplace=True)
#             df_sell_traded.rename(columns=rename_map, inplace=True)

#             # --- Column order ---
#             cols = [
#                 "BRO", "Branch", "Client Code", "Client Name",
#                 "Symbol", "Type", "Total Quantity", "Total Amount"
#             ]

#             df_buy_traded = df_buy_traded[cols]
#             df_sell_traded = df_sell_traded[cols]

#             # --- Tabs for clean UI ---
#             tab1, tab2 = st.tabs(["🟥 Top 10 Traded — Buyers", "🟩 Top 10 Traded — Sellers"])

#             with tab1:
#                 df_buy_traded.reset_index(inplace=True, drop=True)
#                 df_buy_traded.index = df_buy_traded.index + 1

#                 fig = px.pie(
#                 df_buy_traded,
#                 names="Symbol",
#                 values="Total Quantity",
#                 title="Top Buy",
#                 hole=0.4  
#                 )
#                 fig.update_traces(textposition='outside', textinfo='percent+label')
#                 st.plotly_chart(fig, use_container_width=True,)
#                 st.badge(f"Top 10 total Buy Amount: {df_buy_traded['Total Amount'].sum():,.2f}", color="red")
                
#                 st.dataframe(
#                     df_buy_traded.style
#                     .format({col: accounting_format for col in ['Total Amount', 'Total Quantity'] if col in df_buy_traded.columns})
#                     .map(highlight_negative, subset=[c for c in ['Total Amount', 'Total Quantity'] if c in df_buy_traded.columns]),
#                     width='stretch',
#                     height=388,
#                 )

#             with tab2:
#                 df_sell_traded.reset_index(inplace=True, drop=True)
#                 df_sell_traded.index = df_sell_traded.index + 1
#                 fig = px.pie(
#                 df_sell_traded,
#                 names="Symbol",
#                 values="Total Quantity",
#                 title="Top Sell",
#                 hole=0.4  
#                 )
#                 fig.update_traces(textposition='outside', textinfo='percent+label')
#                 st.plotly_chart(fig, use_container_width=True,)
#                 st.badge(f"Top 10 total Sell Amount: {df_sell_traded['Total Amount'].sum():,.2f}", color="green")
#                 st.dataframe(
#                     df_sell_traded.style
#                     .format({col: accounting_format for col in ['Total Amount', 'Total Quantity'] if col in df_sell_traded.columns})
#                     .map(highlight_negative, subset=[c for c in ['Total Amount', 'Total Quantity'] if c in df_sell_traded.columns]),
#                     width='stretch',
#                     height=388,
#                 )

# # ---------------------------------------------------------
# # ✅ Run App
# # ---------------------------------------------------------
# if __name__ == "__main__":
#     Dashboard().show()