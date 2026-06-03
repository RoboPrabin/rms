import streamlit as st
import pandas as pd
from utils import helper
from utils.formatting import accounting_format, highlight_negative
from time import sleep
import streamlit_bridge.navigation as navigation
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage
from db import db


class RiskMonitoring(BasePage):
    def __init__(self):
        st.set_page_config("Risk Monitoring", page_icon="🚨", layout='wide')
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "aml"

        activate_client_code_hotkey()
        navigation.render_sidebar()

        st.header("🚨 Risk Monitoring", anchor=False)
        self.render_page()

    def render_page(self):
        df_dpm3 = self._load_dpm3_data()
        if df_dpm3 is None or df_dpm3.empty:
            st.info("No DPM3 data available.")
            return

        df_prices = self._load_average_prices()
        df_rm = self._load_rm_map()
        df_onhold = self._load_onhold_data(df_prices)

        merged = self._merge_and_compute(df_dpm3, df_prices)
        merged = self._enrich_with_bro(merged, df_rm)

        grouped = self._aggregate_by_client(merged)

        selection = self._display_table(grouped)

        if selection and selection.selection.rows:
            row_idx = selection.selection.rows[0]
            selected_row = grouped.iloc[row_idx]
            self._show_client_dialog(merged, df_onhold, selected_row)

    @staticmethod
    @st.cache_data(ttl=1200)
    def _load_dpm3_data():
        return db.get_dpm3()

    @staticmethod
    @st.cache_data(ttl=1200)
    def _load_average_prices():
        rows = db.get_table_average_price()
        return pd.DataFrame(rows, columns=["symbol", "closePrice"])

    @staticmethod
    @st.cache_data(ttl=1200)
    def _load_rm_map():
        rows = db.get_table_rm_child_map()
        return pd.DataFrame(rows, columns=["BRO", "CLIENT CODE"])

    @staticmethod
    @st.cache_data(ttl=1200)
    def _load_onhold_data(df_prices):
        df = db.get_dpm3_onhold()
        if df is None or df.empty:
            return pd.DataFrame()
        df.rename(columns={
            'client_code': 'CLIENT CODE', 'client_name': 'CLIENT NAME',
            'branch': 'BRANCH', 'symbol': 'SCRIPT',
            'transaction_type': 'TRANSACTION TYPE', 'quantity': 'QUANTITY',
            'status': 'STATUS', 'settlement_date': 'SETTLEMENT DATE'
        }, inplace=True)
        df['CLIENT NAME'] = df['CLIENT NAME'].str.upper()
        df['BRANCH'] = df['BRANCH'].str.upper()
        df = df.merge(
            df_prices[['symbol', 'closePrice']],
            left_on="SCRIPT", right_on="symbol", how="left"
        ).drop(columns=['symbol']).rename(columns={'closePrice': 'CLOSE PRICE'})
        df['QUANTITY'] = pd.to_numeric(df['QUANTITY'], errors="coerce").fillna(0)
        df['CLOSE PRICE'] = pd.to_numeric(df['CLOSE PRICE'], errors="coerce").fillna(0)
        df['TOTAL VALUATION'] = df['QUANTITY'] * df['CLOSE PRICE']
        return df

    @staticmethod
    def _merge_and_compute(df_dpm3, df_prices):
        df_prices = df_prices.rename(columns={"symbol": "SCRIPT"})
        df_prices["closePrice"] = pd.to_numeric(df_prices["closePrice"], errors="coerce").fillna(0.0)

        merged = df_dpm3.merge(df_prices, on="SCRIPT", how="left")

        merged["FREE BALANCE"] = pd.to_numeric(merged["FREE BALANCE"], errors="coerce").fillna(0)
        merged["PLEDGE BALANCE"] = pd.to_numeric(merged["PLEDGE BALANCE"], errors="coerce").fillna(0)

        merged["CLOSING PRICE"] = merged["closePrice"]
        merged["FREE SHARE VALUATION"] = merged["FREE BALANCE"] * merged["CLOSING PRICE"]
        merged["PLEDGE SHARE VALUATION"] = merged["PLEDGE BALANCE"] * merged["CLOSING PRICE"]
        merged["TOTAL VALUATION"] = merged["FREE SHARE VALUATION"] + merged["PLEDGE SHARE VALUATION"]

        return merged

    @staticmethod
    def _enrich_with_bro(df, df_rm):
        merged = df.merge(df_rm, on="CLIENT CODE", how="left")
        merged["BRO"] = merged["BRO"].fillna("N/A")
        return merged

    @staticmethod
    def _aggregate_by_client(df):
        grouped = df.groupby("CLIENT CODE", as_index=False, sort=False).agg(
            BRO=("BRO", "first"),
            CLIENT_NAME=("CLIENT NAME", "first"),
            BRANCH=("BRANCH", "first"),
            SCRIPTS=("SCRIPT", "count"),
            FREE_SHARE_VALUATION=("FREE SHARE VALUATION", "sum"),
            PLEDGE_SHARE_VALUATION=("PLEDGE SHARE VALUATION", "sum"),
        )
        grouped = grouped.sort_values("FREE_SHARE_VALUATION", ascending=False).reset_index(drop=True)
        return grouped

    @staticmethod
    def _display_table(df):
        display = df.copy()
        for col in ["FREE_SHARE_VALUATION", "PLEDGE_SHARE_VALUATION"]:
            display[col] = display[col].apply(lambda x: f"{x:,.2f}")

        bro_col = display.pop("BRO")
        display.insert(0, "BRO", bro_col)

        display.columns = [
            "BRO", "Client Code", "Client Name", "Branch",
            "Total Scripts", "Free Share Val", "Pledge Share Val"
        ]

        selection = st.dataframe(
            display, use_container_width=True, hide_index=True,
            key="risk_monitoring_table",
            selection_mode="single-row",
            on_select="rerun"
        )
        return selection

    @st.dialog("📑 Client Scripts Detail", width="large")
    def _show_client_dialog(self, merged, df_onhold, selected_row):
        client_code = selected_row["CLIENT CODE"]
        client_label = selected_row["CLIENT_NAME"]
        st.subheader(f"👨🏻‍💻 {client_label} - {client_code}")

        detail = merged[merged["CLIENT CODE"] == client_code].copy()
        detail.reset_index(drop=True, inplace=True)
        detail.index += 1

        col1, col2, col3 = st.columns(3)
        with col1:
            st.badge(f"Script Count: {len(detail)}", color="green")
        with col2:
            st.badge(f"Total Free Balance: {detail['FREE BALANCE'].sum()}", color="blue")
        with col3:
            st.badge(f"Total Valuation: {detail['TOTAL VALUATION'].sum():,.2f}", color="yellow")

        st.subheader("📦 Current Holdings")
        view_cols = [
            "SCRIPT", "FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE",
            "CLOSING PRICE", "FREE SHARE VALUATION",
            "PLEDGE SHARE VALUATION", "TOTAL VALUATION"
        ]
        detail = detail[[c for c in view_cols if c in detail.columns]]
        st.dataframe(detail, use_container_width=True)

        if df_onhold is not None and not df_onhold.empty:
            onhold_client = df_onhold[df_onhold["CLIENT CODE"] == client_code].copy()
            if not onhold_client.empty:
                onhold_client.reset_index(drop=True, inplace=True)
                onhold_client.index += 1
                st.subheader("⏳ On Hold Scripts")
                oh_cols = [
                    "SCRIPT", "QUANTITY", "CLOSE PRICE", "TOTAL VALUATION",
                    "TRANSACTION TYPE", "STATUS", "SETTLEMENT DATE"
                ]
                onhold_client = onhold_client[[c for c in oh_cols if c in onhold_client.columns]]
                for c in ["QUANTITY", "CLOSE PRICE", "TOTAL VALUATION"]:
                    if c in onhold_client.columns:
                        onhold_client[c] = onhold_client[c].map(
                            lambda x: f"{x:,.2f}" if pd.notnull(x) else ""
                        )
                st.dataframe(onhold_client, use_container_width=True)
if __name__ == "__main__":
    RiskMonitoring()
