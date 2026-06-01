import streamlit as st
import pandas as pd
from utils import helper
from utils.formatting import accounting_format, highlight_negative
from time import sleep
import streamlit_bridge.navigation as navigation
from utils.custom_hotkey import activate_client_code_hotkey
from pages.BasePage import BasePage
from db import db


STATUS_OPTIONS = ["Active", "Inactive", "Suspended", "Default", "N/A"]
STATUS_COLORS = {
    "Active": "#27ae60", "Inactive": "#e74c3c",
    "Suspended": "#f39c12", "Default": "#c0392b", "N/A": "#95a5a6",
}
PREFERRED_COLUMNS = [
    "Bro", "Branch", "Client Code", "Client Name", "Boid",
    "Dp In/Out", "Status",
    "Free Share Valuation", "Pledge Share Valuation",
    "Onhold Amount", "Due Amount", "Net Valuation",
]
FINANCIAL_COLUMNS = [
    "Free Share Valuation", "Pledge Share Valuation",
    "Onhold Amount", "Due Amount", "Net Valuation",
]

intranet_engine = helper.get_holding_engine()


@st.cache_data(ttl=300)
def load_risk_monitoring_data():
    query = """
        WITH parsed_due AS (
            SELECT "clientCode", "adjustedBalance",
                   TO_TIMESTAMP(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM') AS uploaded_ts
            FROM due_list
            WHERE uploaded_at IS NOT NULL AND TRIM(uploaded_at) <> ''
              AND TO_TIMESTAMP(uploaded_at, 'YYYY-MM-DD HH12:MI:SS AM')::date = CURRENT_DATE
        )
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
            FROM parsed_due
            ORDER BY "clientCode", uploaded_ts DESC
        ) dl ON r.client_code = dl."clientCode"
        ORDER BY r.client_code
    """
    return pd.read_sql(query, intranet_engine)


@st.cache_data(ttl=300)
def load_dpm3_valuation():
    df = pd.read_sql(
        """SELECT "CLIENT CODE", "FREE SHARE VALUATION", "PLEDGE SHARE VALUATION",
                  "FREE BALANCE", "PLEDGE BALANCE"
           FROM dpm3""",
        intranet_engine,
    )
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
    df = pd.read_sql(
        """SELECT o.client_code, o.quantity, COALESCE(a."closePrice", 0) AS close_price
           FROM dpm3_onhold o
           LEFT JOIN average_price a ON o.symbol = a."symbol" """,
        intranet_engine,
    )
    if df.empty:
        return df
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["Onhold_Amount"] = df["quantity"] * df["close_price"]
    val = df.groupby("client_code").agg(Onhold_Amount=("Onhold_Amount", "sum")).reset_index()
    val["Onhold_Amount"] = val["Onhold_Amount"].round(2)
    return val


@st.cache_data(ttl=300)
def load_merged_risk_data():
    df = load_risk_monitoring_data()
    if df.empty:
        return df

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

    remaining = [c for c in df.columns if c not in PREFERRED_COLUMNS]
    df = df[PREFERRED_COLUMNS + remaining]
    df = df.sort_values("Bro", ascending=True)
    return df


@st.dialog("✏️ Edit Risk Monitoring Record", width="large")
def edit_risk_monitoring_dialog(row):
    client_code = row.get("Client Code", "")
    current_status = row.get("Status", "N/A")
    status_color = STATUS_COLORS.get(current_status, "#95a5a6")

    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between;
                    background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius:12px; padding:18px 22px; margin-bottom:20px;">
            <div>
                <span style="color:rgba(255,255,255,0.7); font-size:13px;">CLIENT CODE</span><br>
                <span style="color:white; font-size:20px; font-weight:700;">{client_code}</span>
            </div>
            <div style="text-align:center;">
                <span style="color:rgba(255,255,255,0.7); font-size:13px;">CURRENT STATUS</span><br>
                <span style="background:{status_color}; color:white; padding:4px 18px;
                      border-radius:20px; font-size:14px; font-weight:600;">
                    ● {current_status}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    client_name = row.get("Client Name", "")
    all_keys = {"Client Code", "Bro", "Branch", "Boid", "Dp In/Out", "Due Amount",
                "Net Valuation", "Free Share Valuation", "Pledge Share Valuation",
                "Onhold Amount", "Client Name", "Status"}
    extra_keys = [k for k in row.keys() if k not in all_keys]

    col_name, col_status = st.columns([3, 1])
    with col_name:
        client_name_val = st.text_input("👤 Client Name", value=client_name)
    with col_status:
        try:
            status_idx = STATUS_OPTIONS.index(current_status)
        except ValueError:
            status_idx = len(STATUS_OPTIONS) - 1
        status_val = st.selectbox("📌 Status", STATUS_OPTIONS, index=status_idx)

    for group in [["Bro", "Branch", "Boid"],
                  ["Dp In/Out", "Free Share Valuation", "Pledge Share Valuation"],
                  ["Onhold Amount", "Due Amount", "Net Valuation"]]:
        cols = st.columns(3)
        for i, key in enumerate(group):
            with cols[i]:
                val = row.get(key, "")
                st.text_input(key, value=str(val) if val not in (None, "", 0) else "N/A", disabled=True)

    for k in extra_keys:
        v = row.get(k, "")
        st.text_input(k, value=str(v) if v is not None else "", disabled=True)

    msg_box = st.empty()

    col_save, col_del, _ = st.columns([1.5, 1.5, 5])
    with col_save:
        if st.button("💾 Save Changes", use_container_width=True, type="primary"):
            try:
                db.update_risk_monitoring(
                    client_code=client_code,
                    client_name=client_name_val,
                    status=status_val,
                    updated_by=st.session_state.get("username", "system"),
                )
                msg_box.success("✅ Record updated successfully!")
                sleep(0.5)
                st.rerun()
            except Exception as e:
                msg_box.error(f"❌ Update failed: {e}")

    with col_del:
        if "risk_mon_delete_step" not in st.session_state:
            st.session_state.risk_mon_delete_step = False

        if not st.session_state.risk_mon_delete_step:
            if st.button("🗑️ Delete", use_container_width=True):
                st.session_state.risk_mon_delete_step = True
                st.rerun()
        else:
            st.warning("⚠️ Proceed with deletion?")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("Yes, delete", type="primary", use_container_width=True):
                    try:
                        db.delete_risk_monitoring(client_code)
                        st.session_state.risk_mon_delete_step = False
                        msg_box.success("✅ Record deleted successfully!")
                        sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        msg_box.error(f"❌ Delete failed: {e}")
            with col_no:
                if st.button("Keep it", use_container_width=True):
                    st.session_state.risk_mon_delete_step = False
                    st.rerun()


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
        with st.spinner("Loading risk monitoring data..."):
            df = load_merged_risk_data()

        if df is None or df.empty:
            st.warning("No risk monitoring data available.")
            return

        col1, col2 = st.columns([1, 3])
        with col1:
            filter_by = st.selectbox("", ["All", "Bro", "Branch", "Client Code", "DP In/Out"], key="filter_by", label_visibility="collapsed")
        with col2:
            if filter_by == "All":
                filter_val = "All"
                st.text_input("", value="No filter", disabled=True, key="fv_all", label_visibility="collapsed")
            elif filter_by == "Bro":
                options = ["All"] + sorted(df["Bro"].dropna().unique().tolist())
                filter_val = st.selectbox("", options, key="fv_bro", label_visibility="collapsed")
            elif filter_by == "Branch":
                options = ["All"] + sorted(df["Branch"].dropna().unique().tolist())
                filter_val = st.selectbox("", options, key="fv_branch", label_visibility="collapsed")
            elif filter_by == "Client Code":
                filter_val = st.text_input("", "", key="fv_client", label_visibility="collapsed").strip()
            elif filter_by == "DP In/Out":
                filter_val = st.selectbox("", ["All", "In", "Out"], key="fv_dp", label_visibility="collapsed")

        display_df = df
        if filter_by == "Bro" and filter_val != "All":
            display_df = display_df[display_df["Bro"] == filter_val]
        elif filter_by == "Branch" and filter_val != "All":
            display_df = display_df[display_df["Branch"] == filter_val]
        elif filter_by == "Client Code" and filter_val:
            display_df = display_df[display_df["Client Code"].astype(str).str.contains(filter_val, case=False, na=False)]
        elif filter_by == "DP In/Out" and filter_val != "All":
            display_df = display_df[display_df["Dp In/Out"] == filter_val]

        existing_financial = [c for c in FINANCIAL_COLUMNS if c in display_df.columns]
        styled_df = display_df.style.format(accounting_format, subset=existing_financial)
        if existing_financial:
            styled_df = styled_df.map(highlight_negative, subset=existing_financial)

        st.badge(f"Total Records: {len(display_df):,}", color="red")
        selection = st.dataframe(
            styled_df,
            use_container_width=True,
            selection_mode="single-row",
            key="risk_monitoring_table",
            on_select="rerun",
            hide_index=True,
        )

        if selection.selection.rows:
            row_idx = selection.selection.rows[0]
            selected = display_df.iloc[row_idx].to_dict()
            edit_risk_monitoring_dialog(selected)


if __name__ == "__main__":
    RiskMonitoring()
