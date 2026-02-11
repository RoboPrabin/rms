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
import time
from utils.security import decrypt_data
from utils import auth_utils
# ---------------------------------------------------------
# 🛡️ SESSION GUARD (MUST BE AT THE TOP)
# ---------------------------------------------------------


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



def show_notification(message="hy"):
    st.markdown(f"""
        <style>
        /* Container at top-right */
        .top-right-notification {{
            position: fixed;
            top: 80px;
            right: 50px;
            z-index: 9999;
            display: flex;
            align-items: center;
            cursor: pointer;
        }}

        /* Bell icon styling */
        .bell {{
            font-size: 22px;
            padding: 10px 12px 10px 12px;
            border-radius: 50%;
            box-shadow: 0 0 0 rgba(255, 165, 0, 0); /* initial no glow */
            transition: transform 0.2s;
            animation: popIn 0.5s ease-out, glow 2s ease-in-out infinite alternate;
        }}

        .bell:hover {{
            transform: scale(1.3);
        }}

        /* Glow animation */
        @keyframes glow {{
            0% {{ box-shadow: 0 0 5px rgba(255, 165, 0, 0.5); }}
            50% {{ box-shadow: 0 0 20px rgba(255, 165, 0, 1); }}
            100% {{ box-shadow: 0 0 5px rgba(255, 165, 0, 0.5); }}
        }}

        /* Pop-in animation */
        @keyframes popIn {{
            0% {{ transform: scale(0); opacity: 0; }}
            70% {{ transform: scale(1.2); opacity: 1; }}
            100% {{ transform: scale(1); }}
        }}

        /* Notification popup */
        .popup {{
            display: none;
            position: absolute;
            top: 50px;
            right: 0;
            background-color: #ffffff;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            padding: 15px;
            min-width: 220px;
            font-size: 14px;
            color: black;
            animation: fadeIn 0.3s ease-out;
        }}

        /* Show popup on hover with fade-in/fade-out */
        .top-right-notification:hover .popup {{
            display: block;
            animation: fadeIn 0.3s ease-out;
        }}

        @keyframes fadeIn {{
            0% {{ opacity: 0; transform: translateY(-10px); }}
            100% {{ opacity: 1; transform: translateY(0); }}
        }}
        </style>

        <div class="top-right-notification">
            <div class="bell">🔔</div>
            <div class="popup">{message}</div>
        </div>
    """, unsafe_allow_html=True)

    
# ---------------------------------------------------------
# 🖥️ DASHBOARD CLASS
user = auth_utils.ensure_logged_in()
# ---------------------------------------------------------
class Dashboard:
    def __init__(self):
        # self.username= "user['username']"
        # self.role= "user['role']"
        # self.branch = "user['branch']"
        self.username= user['username']
        self.role= user['role']
        self.branch = user['branch']
        print("Dashboard", user)
        # self.branch = app_state.get_current_user_info()
        helper.eliminate_top_margin(margin_top="-8rem")
        st.session_state.active_menu = ""
        st.set_page_config("Dashboard", page_icon="🏠", layout="wide")

        # --- Dates ---
        self.today_date = datetime.now().date()
        self.today_np_date = nepali_date.today()

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
        # show_notification()
        
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
            st.subheader("📊 Top Traded Stocks", anchor=False)

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
                st.info("No data available for selected date.", icon="📢")
# ---------------------------------------------------------
# ▶ RUN APP
# ---------------------------------------------------------
if __name__ == "__main__":
    Dashboard().show()