import streamlit as st
import pandas as pd
from datetime import date
from utils import helper
import streamlit_bridge.navigation as navigation
from utils.custom_hotkey import activate_client_code_hotkey
from streamlit_autorefresh import st_autorefresh
from pages.BasePage import BasePage
from db import db


VAL_COLS = ["FREE_SHARE_VALUATION", "PLEDGE_SHARE_VALUATION",
            "ONHOLD_AMOUNT", "TOTAL_VALUATION", "DUE_AMOUNT", "NET_VALUATION"]


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
        st_autorefresh(interval=300_000, key="risk_monitoring_refresh")
        df_dpm3 = self._load_dpm3_data()
        if df_dpm3 is None or df_dpm3.empty:
            st.info("No DPM3 data available.")
            return

        df_prices = self._load_average_prices()
        df_rm = self._load_rm_map()
        df_onhold = self._load_onhold_data(df_prices)
        df_due = self._load_due_list()

        role = getattr(self, 'role', None)
        if role == "BRO":
            alias = helper.get_alias_name(self.username.upper()).strip()
            bro_clients = df_rm[df_rm["BRO"].str.strip().str.upper() == alias.upper()]["CLIENT CODE"].unique()
            if len(bro_clients) == 0:
                st.info("No clients assigned to your profile.")
                return
            df_dpm3 = df_dpm3[df_dpm3["CLIENT CODE"].isin(bro_clients)]
        elif role == "BM":
            branch_val = (self.branch or "").strip().upper()
            bm = helper.get_branch_code_mapping()
            rev_bm = {v.upper(): k for k, v in bm.items()}
            possible = {branch_val}
            if branch_val in bm:
                possible.add(bm[branch_val].upper())
            if branch_val in rev_bm:
                possible.add(rev_bm[branch_val])
            df_dpm3 = df_dpm3[df_dpm3["BRANCH"].str.strip().str.upper().isin(possible)]
        if role in ("BRO", "BM") and df_dpm3.empty:
            st.info("No risk data found for your profile.")
            return

        merged = self._merge_and_compute(df_dpm3, df_prices)
        for src, col in [(df_rm, "BRO"), (df_due, "DUE AMOUNT"), (df_onhold, "ONHOLD AMOUNT")]:
            merged = self._enrich(merged, src, col)
        grouped = self._aggregate_by_client(merged)

        grouped = self._apply_filter(grouped)
        st.badge(f"Total Clients: {len(grouped):,}", color="green")
        selection = self._display_table(grouped)

        if selection and selection.selection.rows:
            row_idx = selection.selection.rows[0]
            self._show_client_dialog(merged, df_onhold, grouped.iloc[row_idx])

    # ------------------------------------------------------------------
    # Data loaders (cached)
    # ------------------------------------------------------------------
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
    def _load_due_list():
        _, df = db.get_due_list_for_dpm3(date.today())
        return df

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
        for c in ["QUANTITY", "CLOSE PRICE"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        df['TOTAL VALUATION'] = df['QUANTITY'] * df['CLOSE PRICE']
        return df

    # ------------------------------------------------------------------
    # Computation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _merge_and_compute(df_dpm3, df_prices):
        df_prices = df_prices.rename(columns={"symbol": "SCRIPT"})
        df_prices["closePrice"] = pd.to_numeric(df_prices["closePrice"], errors="coerce").fillna(0.0)
        merged = df_dpm3.merge(df_prices, on="SCRIPT", how="left")
        for c in ["FREE BALANCE", "PLEDGE BALANCE"]:
            merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0)
        merged["CLOSING PRICE"] = merged["closePrice"]
        merged["FREE SHARE VALUATION"] = merged["FREE BALANCE"] * merged["CLOSING PRICE"]
        merged["PLEDGE SHARE VALUATION"] = merged["PLEDGE BALANCE"] * merged["CLOSING PRICE"]
        merged["TOTAL VALUATION"] = merged["FREE SHARE VALUATION"] + merged["PLEDGE SHARE VALUATION"]
        return merged

    @staticmethod
    def _enrich(df, src_df, col_name):
        if col_name == "BRO":
            merged = df.merge(src_df, on="CLIENT CODE", how="left")
            merged["BRO"] = merged["BRO"].fillna("N/A")
            return merged
        default = 0.0
        if src_df is None or src_df.empty:
            df[col_name] = default
            return df
        if col_name == "DUE AMOUNT":
            src = src_df.rename(columns={"clientCode": "CLIENT CODE", "adjustedBalance": "DUE AMOUNT"})
            src["DUE AMOUNT"] = pd.to_numeric(src["DUE AMOUNT"], errors="coerce").fillna(0)
            merged = df.merge(src[["CLIENT CODE", "DUE AMOUNT"]], on="CLIENT CODE", how="left")
        else:
            agg = src_df.groupby("CLIENT CODE", as_index=False)["TOTAL VALUATION"].sum().rename(
                columns={"TOTAL VALUATION": "ONHOLD AMOUNT"})
            merged = df.merge(agg[["CLIENT CODE", "ONHOLD AMOUNT"]], on="CLIENT CODE", how="left")
        merged[col_name] = merged[col_name].fillna(default)
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
            ONHOLD_AMOUNT=("ONHOLD AMOUNT", "first"),
            DUE_AMOUNT=("DUE AMOUNT", "first"),
        )
        grouped["TOTAL_VALUATION"] = grouped[["FREE_SHARE_VALUATION", "ONHOLD_AMOUNT"]].sum(axis=1)
        grouped["NET_VALUATION"] = grouped["TOTAL_VALUATION"] - grouped["DUE_AMOUNT"]
        mask = grouped["TOTAL_VALUATION"] != 0
        grouped["PERCENTAGE"] = 0.0
        grouped.loc[mask, "PERCENTAGE"] = (grouped["NET_VALUATION"] / grouped["TOTAL_VALUATION"] * 100).loc[mask]
        return grouped.sort_values("FREE_SHARE_VALUATION", ascending=False).reset_index(drop=True)

    @staticmethod
    def _apply_filter(df):
        opts = {"BRO": "BRO", "Client Code": "CLIENT CODE", "Branch": "BRANCH"}
        col1, col2 = st.columns(2)
        with col1:
            k = st.selectbox("Filter by", options=["ALL"] + list(opts.keys()), key="risk_filter_by")
        if k != "ALL":
            col = opts[k]
            with col2:
                v = st.selectbox(f"Select {k}", options=sorted(df[col].dropna().unique()), key="risk_filter_val")
            df = df[df[col] == v].reset_index(drop=True)
        return df

    @staticmethod
    def _display_table(df):
        ORDER = ["BRANCH", "BRO", "CLIENT CODE", "CLIENT_NAME",
                 "SCRIPTS", "FREE_SHARE_VALUATION", "PLEDGE_SHARE_VALUATION",
                 "ONHOLD_AMOUNT", "TOTAL_VALUATION", "DUE_AMOUNT", "NET_VALUATION", "PERCENTAGE"]
        LABELS = ["Branch", "BRO", "Client Code", "Client Name",
                  "Total Scripts", "Free Share Val", "Pledge Share Val",
                  "On Hold Amount", "Total Valuation", "Due Amount",
                  "Net Valuation", "Percentage"]

        display = df[ORDER].copy()
        for c in VAL_COLS:
            display[c] = display[c].apply(lambda x: f"{x:,.2f}")
        display["PERCENTAGE"] = display["PERCENTAGE"].apply(lambda x: f"{x:.2f}%")
        display.columns = LABELS

        selection = st.dataframe(
            display, use_container_width=True, hide_index=True,
            key="risk_monitoring_table", selection_mode="single-row", on_select="rerun"
        )
        return selection

    @st.dialog("📑 Client Scripts Detail", width="large")
    def _show_client_dialog(self, merged, df_onhold, selected_row):
        client_code = selected_row["CLIENT CODE"]
        client_label = selected_row["CLIENT_NAME"]
        st.subheader(f"👨🏻‍💻 {client_label} - {client_code}")

        detail = merged[merged["CLIENT CODE"] == client_code].copy()
        detail = detail[~((detail["FREE BALANCE"] == 0) & (detail["PLEDGE BALANCE"] == 0) & (detail.get("LOCKIN BALANCE", 0) == 0))]
        detail.reset_index(drop=True, inplace=True)
        detail.index += 1

        col1, col2, col3 = st.columns(3)
        with col1:
            st.badge(f"Script Count: {len(detail)}", color="green")
        with col2:
            st.badge(f"Total Free Balance: {detail['FREE BALANCE'].sum():,.0f}", color="blue")
        with col3:
            st.badge(f"Total Valuation: {detail['TOTAL VALUATION'].sum():,.2f}", color="yellow")

        st.subheader("📦 Current Holdings")
        detail = detail[[c for c in [
            "SCRIPT", "FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE",
            "CLOSING PRICE", "FREE SHARE VALUATION",
            "PLEDGE SHARE VALUATION", "TOTAL VALUATION"
        ] if c in detail.columns]]
        st.dataframe(detail, use_container_width=True)

        if df_onhold is not None and not df_onhold.empty:
            oh = df_onhold[df_onhold["CLIENT CODE"] == client_code].copy()
            if not oh.empty:
                oh.reset_index(drop=True, inplace=True)
                oh.index += 1
                st.subheader("⏳ On Hold Scripts")
                oh = oh[[c for c in [
                    "SCRIPT", "QUANTITY", "CLOSE PRICE", "TOTAL VALUATION",
                    "TRANSACTION TYPE", "STATUS", "SETTLEMENT DATE"
                ] if c in oh.columns]]
                for c in ["QUANTITY", "CLOSE PRICE", "TOTAL VALUATION"]:
                    if c in oh.columns:
                        oh[c] = oh[c].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
                st.dataframe(oh, use_container_width=True)


if __name__ == "__main__":
    RiskMonitoring()
