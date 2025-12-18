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

class Dashboard:
    def __init__(self):
        st.set_page_config("Dashboard", page_icon="🏠", layout='wide')

        # Dates
        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_date = datetime.now().strftime("%Y-%m-%d")
        self.today_np_date = nepali_date.today()

        # Authentication
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()

        self.username, self.role = app_state.get_current_user_info()

        # Sidebar
        navigation.render_sidebar()

        # DB Engine
        self.engine = helper.get_holding_engine()
        if self.has_today_floorsheet_data():
            yesterday = datetime.now() - timedelta(days=0)
        else:
            yesterday = datetime.now() - timedelta(days=1)


        self.yesterday_date = yesterday.strftime("%Y-%m-%d")
        self.week_day = yesterday.strftime("%A")

    def has_today_floorsheet_data(self):
        query = """
            SELECT 1
            FROM floorsheet
            WHERE DATE(uploaded_at) = %s
            LIMIT 1;
        """

        df = pd.read_sql(query, self.engine, params=(self.today_date,))

        return not df.empty
    # ---------------------------------------------------------
    # ✅ SQL Queries
    # ---------------------------------------------------------
    @st.cache_data(ttl=3600)
    def get_top_buy_sell_commission(_self):

        query_buy = """
            SELECT 
                f.clientcode,
                f.clientname,
                f.branch,
                COALESCE(crm."rmName", 'N/A') AS rmName,
                SUM(f.amount) AS total_buy
            FROM floorsheet f
            LEFT JOIN client_rm_map crm 
                ON crm."clientCode" = f.clientcode
            WHERE f.transaction_type = 'Buy'
            AND DATE(f.uploaded_at) = %s
            GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
            ORDER BY total_buy DESC
            LIMIT 10;
        """

        query_sell = """
           SELECT 
                f.clientcode,
                f.clientname,
                f.branch,
                COALESCE(crm."rmName", 'N/A') AS rmName,
                SUM(f.amount) AS total_sell
            FROM floorsheet f
            LEFT JOIN client_rm_map crm 
                ON crm."clientCode" = f.clientcode
            WHERE f.transaction_type = 'Sell'
            AND DATE(f.uploaded_at) = %s
            GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
            ORDER BY total_sell DESC
            LIMIT 10;
        """

        query_comm = """
            SELECT 
                f.clientcode,
                f.clientname,
                f.branch,
                COALESCE(crm."rmName", 'N/A') AS rmName,
                SUM(f.stockcomm) AS total_commission
            FROM floorsheet f
            LEFT JOIN client_rm_map crm 
                ON crm."clientCode" = f.clientcode
            WHERE DATE(f.uploaded_at) = %s
            GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
            ORDER BY total_commission DESC
        """

        query_traded = """
            SELECT 
                f.symbol,
                f.transaction_type,
                f.clientcode,
                f.branch,
                f.clientname,
                COALESCE(crm."rmName", 'N/A') AS rmName,
                SUM(f.quantity) AS total_quantity,
                SUM(f.amount) AS total_amount
            FROM floorsheet f
            LEFT JOIN client_rm_map crm 
                ON crm."clientCode" = f.clientcode
            WHERE DATE(f.uploaded_at) = %s
            GROUP BY 
                f.symbol,
                f.transaction_type,
                f.clientcode,
                f.branch,
                f.clientname,
                rmName
            ORDER BY total_amount DESC
            LIMIT 20;
        """

        df_traded = pd.read_sql(query_traded, _self.engine, params=(_self.yesterday_date,))
        df_buy = pd.read_sql(query_buy, _self.engine, params=(_self.yesterday_date,))
        df_sell = pd.read_sql(query_sell, _self.engine, params=(_self.yesterday_date,))
        df_comm = pd.read_sql(query_comm, _self.engine, params=(_self.yesterday_date,))

        return df_buy, df_sell, df_comm, df_traded
    # ---------------------------------------------------------
    # ✅ SQL Queries
    # ---------------------------------------------------------
    @st.cache_data(ttl=3600)
    def get_top_buy_sell_commission_of_loggedin_user(_self, username):
        # GET Alias
        alias = helper.get_alias_name(_self.username)
        # 1) Get all clientCodes assigned to this RM
        query_clients = """
            SELECT "clientCode"
            FROM client_rm_map
            WHERE "rmName" = %s
        """
        df_clients = pd.read_sql(query_clients, _self.engine, params=(alias,))

        # If RM has no clients, return empty frames
        if df_clients.empty:
            empty = pd.DataFrame()
            return empty, empty, empty, empty

        client_list = tuple(df_clients["clientCode"].tolist())

        # 2) Queries filtered by client_list
        query_buy = """
            SELECT 
                f.clientcode,
                f.clientname,
                f.branch,
                COALESCE(crm."rmName", 'N/A') AS rmName,
                SUM(f.amount) AS total_buy
            FROM floorsheet f
            LEFT JOIN client_rm_map crm 
                ON crm."clientCode" = f.clientcode
            WHERE f.transaction_type = 'Buy'
            AND DATE(f.uploaded_at) = %s
            AND f.clientcode IN %s
            GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
            ORDER BY total_buy DESC
            LIMIT 10;
        """

        query_sell = """
            SELECT 
                f.clientcode,
                f.clientname,
                f.branch,
                COALESCE(crm."rmName", 'N/A') AS rmName,
                SUM(f.amount) AS total_sell
            FROM floorsheet f
            LEFT JOIN client_rm_map crm 
                ON crm."clientCode" = f.clientcode
            WHERE f.transaction_type = 'Sell'
            AND DATE(f.uploaded_at) = %s
            AND f.clientcode IN %s
            GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
            ORDER BY total_sell DESC
            LIMIT 10;
        """

        query_comm = """
            SELECT 
                f.clientcode,
                f.clientname,
                f.branch,
                COALESCE(crm."rmName", 'N/A') AS rmName,
                SUM(f.stockcomm) AS total_commission
            FROM floorsheet f
            LEFT JOIN client_rm_map crm 
                ON crm."clientCode" = f.clientcode
            WHERE DATE(f.uploaded_at) = %s
            AND f.clientcode IN %s
            GROUP BY f.clientcode, f.clientname, f.branch, crm."rmName"
            ORDER BY total_commission DESC
            LIMIT 10;
        """

        query_traded = """
            SELECT 
                f.symbol,
                f.transaction_type,
                f.clientcode,
                f.branch,
                f.clientname,
                COALESCE(crm."rmName", 'N/A') AS rmName,
                SUM(f.quantity) AS total_quantity,
                SUM(f.amount) AS total_amount
            FROM floorsheet f
            LEFT JOIN client_rm_map crm 
                ON crm."clientCode" = f.clientcode
            WHERE DATE(f.uploaded_at) = %s
            AND f.clientcode IN %s
            GROUP BY 
                f.symbol,
                f.transaction_type,
                f.clientcode,
                f.branch,
                f.clientname,
                rmName
            ORDER BY total_amount DESC
            LIMIT 20;
        """

        params = (_self.yesterday_date, client_list)

        df_buy = pd.read_sql(query_buy, _self.engine, params=params)
        df_sell = pd.read_sql(query_sell, _self.engine, params=params)
        df_comm = pd.read_sql(query_comm, _self.engine, params=params)
        df_traded = pd.read_sql(query_traded, _self.engine, params=params)

        return df_buy, df_sell, df_comm, df_traded

    # ---------------------------------------------------------
    # ✅ UI Rendering
    # ---------------------------------------------------------
    def show(self):
        st.title("🏠 Dashboard", anchor=False)
        st.subheader(f"Traders Summary : {self.yesterday_date} ({self.week_day})", anchor=False)
        if self.role == "BRO":
            df_buy, df_sell, df_comm, df_traded = self.get_top_buy_sell_commission_of_loggedin_user(username=self.username)
        else:
            df_buy, df_sell, df_comm, df_traded = self.get_top_buy_sell_commission()

        if self.role in ["MANAGEMENT", "ADMIN"]:
            mode = st.radio("Mode", ["Top Performers", "Top Commission Providers", "Top Traded Stocks"], horizontal=True, index=0)
        else:
            mode = st.radio("Mode", ["Top Performers", "Top Traded Stocks"], horizontal=True, index=0)

        if mode=="Top Performers":
            # Two-column layout for buyers & sellers
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 Top 10 Buyers")
                df_buy.index = df_buy.index + 1
                df_buy.rename(columns={"clientcode":"Client Code","clientname":"Client Name" ,"branch":"Branch" ,"total_buy":"Total Buy", "rmname":"BRO"}, inplace=True)
                # st.dataframe(df_buy, use_container_width=True, column_order=["BRO", "Client Code", "Client Name", "Branch", "Total Buy"])
                df_buy = df_buy[["BRO", "Client Code", "Client Name", "Branch", "Total Buy"]]
                df_buy = coerce_numeric_columns(df_buy, ["Total Buy"])

                # fig = px.pie(
                # df_buy,
                # names="Client Name",
                # values="Total Buy",
                # title="Top 10 Buyers",
                # hole=0.4  
                # )
                # fig.update_traces(textposition='outside', textinfo='percent+label')
                # st.plotly_chart(fig, use_container_width=True,)
                
                st.dataframe(
                    df_buy.style
                    .format({col: accounting_format for col in ['Total Buy'] if col in df_buy.columns})
                    .map(highlight_negative, subset=[c for c in ['Total Buy'] if c in df_buy.columns]),
                    width='stretch',
                    hide_index=True
                )

            with col2:
                # st.markdown("### 📉 Top 10 Sellers")
                st.subheader("📉 Top 10 Sellers")
                df_sell.index = df_sell.index + 1
                df_sell.rename(columns={"clientcode":"Client Code","clientname":"Client Name" ,"branch":"Branch" ,"total_sell":"Total Sell","rmname":"BRO"}, inplace=True)

                df_sell = df_sell[["BRO", "Client Code", "Client Name", "Branch", "Total Sell"]]
                df_sell = coerce_numeric_columns(df_sell, ["Total Sell"])


                # fig = px.pie(
                # df_sell,
                # names="Client Name",
                # values="Total Sell",
                # title="Top 10 Sellers",
                # hole=0.4  
                # )
                # fig.update_traces(textposition='outside', textinfo='percent+label')
                # st.plotly_chart(fig, use_container_width=True,)


                st.dataframe(
                    df_sell.style
                    .format({col: accounting_format for col in ['Total Sell'] if col in df_sell.columns})
                    .map(highlight_negative, subset=[c for c in ['Total Sell'] if c in df_sell.columns]),
                    width='stretch',
                    hide_index=True
                )
        elif mode == "Top Commission Providers":
            # Commission providers
            st.markdown(f"### 💰 Total Commission Earned")
            # st.markdown(f"### 💰 Total Commission earned on {self.yesterday_date}, {self.week_day}")
            df_comm.index = df_comm.index + 1
            df_comm.rename(columns={"clientcode":"Client Code","clientname":"Client Name" ,"branch":"Branch" , "total_commission":"Total Commission","rmname":"BRO"}, inplace=True)
            total_comm = round(df_comm['Total Commission'].sum(), 2)
            df_comm = df_comm[["BRO", "Client Code", "Client Name", "Branch", "Total Commission"]]
            df_comm = coerce_numeric_columns(df_comm, ["Total Commission"])

            # fig = px.pie(
            #     df_comm,
            #     names="Client Name",
            #     values="Total Commission",
            #     title="Commission Contribution Share",
            #     hole=0.4  
            # )
            # fig.update_traces(textposition='outside', textinfo='percent+label')
            # st.plotly_chart(fig, use_container_width=True,)

            st.markdown("---")
            st.badge(f"Total Commission: {total_comm:,.2f}", color='green')
            st.dataframe(
                df_comm.style
                .format({col: accounting_format for col in ['Total Commission'] if col in df_comm.columns})
                .map(highlight_negative, subset=[c for c in ['Total Commission'] if c in df_comm.columns]),
                width='stretch'
            )

            

        elif mode == "Top Traded Stocks":
            st.markdown("### 📊 Top Traded Stocks")

            # --- Split Buy/Sell ---
            df_buy_traded = df_traded[df_traded["transaction_type"] == "Buy"].copy()
            df_sell_traded = df_traded[df_traded["transaction_type"] == "Sell"].copy()

            # --- Rename columns ---
            rename_map = {
                "symbol": "Symbol",
                "transaction_type": "Type",
                "branch": "Branch",
                "clientcode": "Client Code",
                "clientname": "Client Name",
                "rmname": "BRO",
                "total_quantity": "Total Quantity",
                "total_amount": "Total Amount"
            }

            df_buy_traded.rename(columns=rename_map, inplace=True)
            df_sell_traded.rename(columns=rename_map, inplace=True)

            # --- Column order ---
            cols = [
                "BRO", "Branch", "Client Code", "Client Name",
                "Symbol", "Type", "Total Quantity", "Total Amount"
            ]

            df_buy_traded = df_buy_traded[cols]
            df_sell_traded = df_sell_traded[cols]

            # --- Tabs for clean UI ---
            tab1, tab2 = st.tabs(["🟥 Top 10 Traded — Buyers", "🟩 Top 10 Traded — Sellers"])

            with tab1:
                df_buy_traded.reset_index(inplace=True, drop=True)
                df_buy_traded.index = df_buy_traded.index + 1

                fig = px.pie(
                df_buy_traded,
                names="Symbol",
                values="Total Quantity",
                title="Top Buy",
                hole=0.4  
                )
                fig.update_traces(textposition='outside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True,)
                st.badge(f"Top 10 total Buy Amount: {df_buy_traded['Total Amount'].sum():,.2f}", color="red")
                
                st.dataframe(
                    df_buy_traded.style
                    .format({col: accounting_format for col in ['Total Amount', 'Total Quantity'] if col in df_buy_traded.columns})
                    .map(highlight_negative, subset=[c for c in ['Total Amount', 'Total Quantity'] if c in df_buy_traded.columns]),
                    width='stretch',
                    height=388,
                )

            with tab2:
                df_sell_traded.reset_index(inplace=True, drop=True)
                df_sell_traded.index = df_sell_traded.index + 1
                fig = px.pie(
                df_sell_traded,
                names="Symbol",
                values="Total Quantity",
                title="Top Sell",
                hole=0.4  
                )
                fig.update_traces(textposition='outside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True,)
                st.badge(f"Top 10 total Sell Amount: {df_sell_traded['Total Amount'].sum():,.2f}", color="green")
                st.dataframe(
                    df_sell_traded.style
                    .format({col: accounting_format for col in ['Total Amount', 'Total Quantity'] if col in df_sell_traded.columns})
                    .map(highlight_negative, subset=[c for c in ['Total Amount', 'Total Quantity'] if c in df_sell_traded.columns]),
                    width='stretch',
                    height=388,
                )

# ---------------------------------------------------------
# ✅ Run App
# ---------------------------------------------------------
if __name__ == "__main__":
    Dashboard().show()