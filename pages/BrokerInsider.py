from datetime import date
import streamlit as st
import pandas as pd
from db import db
import streamlit_bridge.navigation as navigation
from utils import helper
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage


intranet_engine = helper.get_holding_engine()


@st.cache_data(ttl=120)
def get_floorsheet_by_date(selected_date: date):
    query = """
        SELECT f.*,
            COALESCE(m."rmName", 'N/A') AS "rmName"
        FROM floorsheet f
        LEFT JOIN client_rm_map m ON f.clientcode = m."clientCode"
        WHERE DATE(f.uploaded_at) = %s
        ORDER BY f.uploaded_at DESC;
    """
    return pd.read_sql(query, intranet_engine, params=(selected_date,))


class Insider(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        st.set_page_config(page_title="Insider", page_icon="👻", layout="wide")
        navigation.render_sidebar()
        activate_client_code_hotkey()

    def render_ui(self):
        st.title("📄 Broker Information", anchor=False)

        selected_date = st.date_input("Select Date", value=date.today())

        df = get_floorsheet_by_date(selected_date)

        if df.empty:
            st.warning("No data found for the selected date.")
            st.stop()

        # st.badge(f"**Total rows :** {len(df):,}", color="green")

        # ---------------- Main Floorsheet table ----------------
        display_df = df.copy()
        display_df.index = display_df.index + 1

        display_df.drop(
            columns=['id', 'contractnumber', 'tradetime', 'uploaded_at', 'bankdeposit'],
            inplace=True,
            errors="ignore"
        )

        display_df.rename(columns={
            "quantity": "Quantity",
            "symbol": "Symbol",
            "buyerbrokingfirmcode": "Buyer Broker",
            "sellerbrokingfirmcode": "Seller Broker",
            "clientname": "Client Name",
            "clientcode": "Client Code",
            "rate": "Rate",
            "amount": "Amount",
            "stockcomm": "Commission Gain",
            "branch": "Branch",
            "transaction_type": "Transaction Type",
            "rmName": "BRO"
        }, inplace=True)

        desired = [
            "BRO", "Branch", "Client Code", "Client Name", "Symbol",
            "Transaction Type", "Quantity", "Rate", "Amount",
            "Commission Gain", "Buyer Broker", "Seller Broker"
        ]

        display_df = display_df[desired]

        numeric_cols = display_df.select_dtypes(include=["int64", "float64"]).columns
        display_df[numeric_cols] = display_df[numeric_cols].map(lambda x: f"{x:,}")

        # st.dataframe(display_df, use_container_width=True)

        # ================= Summary reference =================
        base_df = df.copy()
        

        # ---------------- Top summary tables ----------------
        tab1, tab2, tab3 = st.tabs(["Top Turnover", "Top Volume", "Top Transactions"])

        ltp_df = (
            base_df.sort_values("uploaded_at")
            .groupby("symbol")
            .tail(1)[["symbol", "rate"]]
            .rename(columns={"rate": "LTP"})
        )

        # Top Turnover
        with tab1:
            top_turnover = (
                base_df.groupby("symbol", as_index=False)["amount"]
                .sum()
                .rename(columns={"amount": "Turnover"})
                .merge(ltp_df, on="symbol", how="left")
                .sort_values("Turnover", ascending=False)
                
            )

            st.badge(f"**Total rows :** {len(top_turnover):,}", color="green")
            top_turnover["Turnover"] = top_turnover["Turnover"].map(lambda x: f"{x:,.2f}")
            top_turnover["LTP"] = top_turnover["LTP"].map(lambda x: f"{x:,.2f}")

            st.dataframe(
                top_turnover
                    .reset_index(drop=True)
                    .rename(columns={"symbol": "Symbol"})
                    .set_index(pd.RangeIndex(start=1, stop=len(top_turnover)+1)),
                width="stretch",
            )

        # Top Volume
        with tab2:
            top_volume = (
                base_df.groupby("symbol", as_index=False)["quantity"]
                .sum()
                .rename(columns={"quantity": "Shares Traded"})
                .merge(ltp_df, on="symbol", how="left")
                .sort_values("Shares Traded", ascending=False)
            )

            st.badge(f"**Total rows :** {len(top_volume):,}", color="green")

            top_volume["Shares Traded"] = top_volume["Shares Traded"].map(lambda x: f"{x:,}")
            top_volume["LTP"] = top_volume["LTP"].map(lambda x: f"{x:,.2f}")

            st.dataframe(
                top_volume
                    .reset_index(drop=True)
                    .rename(columns={"symbol": "Symbol"})
                    .set_index(pd.RangeIndex(start=1, stop=len(top_volume) + 1)),
                width="stretch",
            )
        # Top Transactions
        with tab3:
            top_transactions = (
                base_df.groupby("symbol")
                .size()
                .reset_index(name="No. of Transactions")
                .merge(ltp_df, on="symbol", how="left")
                .sort_values("No. of Transactions", ascending=False)
                
            )
            st.badge(f"**Total rows :** {len(top_transactions):,}", color="green")
            top_transactions["No. of Transactions"] = top_transactions["No. of Transactions"].map(lambda x: f"{x:,}")
            top_transactions["LTP"] = top_transactions["LTP"].map(lambda x: f"{x:,.2f}")

            st.dataframe(
                top_transactions
                    .reset_index(drop=True)
                    .rename(columns={"symbol": "Symbol"})
                    .set_index(pd.RangeIndex(start=1, stop=len(top_transactions)+1)),
                width="stretch",
            )



if __name__ == "__main__":
    Insider().render_ui()