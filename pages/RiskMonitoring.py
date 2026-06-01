import streamlit as st
import pandas as pd
from utils import helper
from datetime import datetime
import streamlit_bridge.navigation as navigation
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage


intranet_engine = helper.get_holding_engine()


@st.cache_data(ttl=300)
def load_risk_monitoring_data():
    today_str = datetime.now().strftime("%Y-%m-%d")
    query = """
        SELECT r.*, COALESCE(m."rmName", 'N/A') AS "Bro",
               COALESCE(k.clientbranch, 'N/A') AS "Branch",
               COALESCE(k.boid::TEXT, 'N/A') AS "BOID",
               CASE WHEN k.boid::TEXT LIKE '130114%%' THEN 'In' ELSE 'Out' END AS "DP In/Out",
               COALESCE(dl."adjustedBalance", 0) AS "Due Amount"
        FROM risk_monitoring r
        LEFT JOIN client_rm_map m ON r.client_code = m."clientCode"
        LEFT JOIN kyc k ON r.client_code = k.clientmembercode
        LEFT JOIN (
            SELECT DISTINCT ON ("clientCode") "clientCode", "adjustedBalance"
            FROM due_list
            WHERE TO_TIMESTAMP(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM')::DATE = %s
            ORDER BY "clientCode", TO_TIMESTAMP(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM') DESC
        ) dl ON r.client_code = dl."clientCode"
        ORDER BY r.client_code
    """
    df = pd.read_sql(query, intranet_engine, params=(today_str,))
    return df


@st.cache_data(ttl=300)
def load_dpm3_valuation():
    df = pd.read_sql("SELECT * FROM dpm3", intranet_engine)
    if df.empty:
        return df
    df.columns = [c.strip().upper() for c in df.columns]
    if "FREE SHARE VALUATION" in df.columns and "PLEDGE SHARE VALUATION" in df.columns:
        val = df.groupby("CLIENT CODE").agg(
            Free_Share_Valuation=("FREE SHARE VALUATION", "sum"),
            Pledge_Share_Valuation=("PLEDGE SHARE VALUATION", "sum"),
        ).reset_index()
    else:
        df["FREE BALANCE"] = pd.to_numeric(df.get("FREE BALANCE", 0), errors="coerce").fillna(0)
        df["PLEDGE BALANCE"] = pd.to_numeric(df.get("PLEDGE BALANCE", 0), errors="coerce").fillna(0)
        val = df.groupby("CLIENT CODE").agg(
            Free_Share_Valuation=("FREE BALANCE", "sum"),
            Pledge_Share_Valuation=("PLEDGE BALANCE", "sum"),
        ).reset_index()
    val["Free_Share_Valuation"] = val["Free_Share_Valuation"].round(2)
    val["Pledge_Share_Valuation"] = val["Pledge_Share_Valuation"].round(2)
    return val


@st.cache_data(ttl=300)
def load_onhold_valuation():
    query = """
        SELECT o.client_code, o.quantity, COALESCE(a."closePrice", 0) AS close_price
        FROM dpm3_onhold o
        LEFT JOIN average_price a ON o.symbol = a."symbol"
    """
    df = pd.read_sql(query, intranet_engine)
    if df.empty:
        return df
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["Onhold_Amount"] = df["quantity"] * df["close_price"]
    val = df.groupby("client_code").agg(Onhold_Amount=("Onhold_Amount", "sum")).reset_index()
    val["Onhold_Amount"] = val["Onhold_Amount"].round(2)
    return val


class RiskMonitoring(BasePage):
    def __init__(self):
        st.set_page_config("Risk Monitoring", page_icon="🚨", layout='wide')
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "aml"

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")

        activate_client_code_hotkey()
        navigation.render_sidebar()

        self.holding_engine = helper.get_holding_engine()
        st.header("🚨 Risk Monitoring", anchor=False)

        self.render_page()

    def render_page(self):
        with st.spinner("Loading risk monitoring data..."):
            df = load_risk_monitoring_data()

        if df is None or df.empty:
            st.warning("No risk monitoring data available.")
            return

        dpm3 = load_dpm3_valuation()
        if dpm3 is not None and not dpm3.empty:
            df = df.merge(dpm3, left_on="client_code", right_on="CLIENT CODE", how="left")
            df["Free_Share_Valuation"] = df["Free_Share_Valuation"].fillna(0)
            df["Pledge_Share_Valuation"] = df["Pledge_Share_Valuation"].fillna(0)
            df.drop(columns=["CLIENT CODE"], inplace=True)

        onhold = load_onhold_valuation()
        if onhold is not None and not onhold.empty:
            df = df.merge(onhold, on="client_code", how="left")
            df["Onhold_Amount"] = df["Onhold_Amount"].fillna(0)

        df["Net_Valuation"] = df["Free_Share_Valuation"] + df["Onhold_Amount"] - df["Due Amount"]

        df = df.rename(columns=helper.camel_to_title)

        preferred_order = [
            "Bro", "Branch", "Client Code", "Client Name", "Boid",
            "Dp In/Out", "Status",
            "Free Share Valuation", "Pledge Share Valuation",
            "Onhold Amount", "Due Amount", "Net Valuation",
        ]
        remaining = [c for c in df.columns if c not in preferred_order]
        df = df[preferred_order + remaining]

        df = df.sort_values("Bro", ascending=True)
        df.index = range(1, len(df) + 1)

        st.badge(f"Total Records: {len(df):,}", color="red")
        selection = st.dataframe(
            df,
            use_container_width=True,
            selection_mode="single-row",
            key="risk_monitoring_table",
            on_select="rerun",
        )

        if selection.selection.rows:
            row_idx = selection.selection.rows[0]
            selected = df.iloc[row_idx].to_dict()
            with st.expander("Selected Row Details", expanded=True):
                for k, v in selected.items():
                    st.write(f"**{k}:** {v}")


if __name__ == "__main__":
    RiskMonitoring()