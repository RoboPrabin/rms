from datetime import date, timedelta
import re
import pandas as pd
import requests
import streamlit as st
from config import config
from pages.BasePage import BasePage
from streamlit_bridge.navigation import render_sidebar
from db import db
from utils import helper


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_client_rm_map_cached():
    query = """SELECT "clientName", "clientCode", "rmName" FROM client_rm_map"""
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
        conn.close()
        return pd.DataFrame(results, columns=["Client Name", "Client Code", "BRO"])
    except Exception:
        st.error("Unable to fetch client data. Please contact IT department.", icon="❌")
        st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_kyc_cached():
    query = """SELECT clientfullname, clientmembercode, clientbranch from kyc"""
    try:
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()
        conn.close()
        return pd.DataFrame(results, columns=["Client Name", "Client Code", "Branch"])
    except Exception:
        st.error("Unable to fetch KYC data. Please contact IT department.", icon="❌")
        st.stop()


@st.cache_data(ttl=300, show_spinner=False)
def get_ledger_data(ac_code, date_from, date_to):
    token = db.get_jwt_token()
    resp = requests.get(
        config.LEDGER_API,
        headers={"Authorization": f"Bearer {token}"},
        params={"acCode": ac_code, "dateFrom": date_from, "dateTo": date_to},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _clean_code(code):
    s = str(code).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


class CashInOut(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin("-4rem")
        st.session_state.active_menu = "account"
        st.set_page_config(page_title="Cash In/Out", page_icon="📖", layout="wide")
        st.header("📖 Cash In/Out", anchor=False)
        render_sidebar()

    def show_expander_with_date_range(self):
        st.session_state.from_str = date.today() - timedelta(days=1)
        st.session_state.to_str = date.today()
        with st.expander("Filter Date Range", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                from_date = st.date_input("From Date", value=date.today() - timedelta(days=1))
            with col2:
                to_date = st.date_input("To Date", value=date.today())

            if st.button("Fetch Data", icon="🧲"):
                st.session_state.from_str = from_date.strftime("%Y-%m-%d")
                st.session_state.to_str = to_date.strftime("%Y-%m-%d")

        with st.container(border=True):
            self.fetch_data_logic(from_date=st.session_state.from_str, to_date=st.session_state.to_str)
        st.toast("Data fetched successfully.", icon="✅")

    def fetch_data_logic(self, from_date, to_date):
        try:
            ledger_data = get_ledger_data("1020201", from_date, to_date)
        except Exception:
            st.error("Unable to fetch ledger data. Please contact IT department.", icon="❌")
            st.stop()

        try:
            pattern = re.compile(r'\[(.*?)\]')
            extracted_list = []
            for entry in ledger_data.get("data", []):
                particulars = entry.get("particulars", "")
                if "received" in particulars.lower():
                    match = pattern.search(particulars)
                    extracted_list.append({
                        "Client Code": match.group(1) if match else None,
                        "drAmount": entry.get("drAmount"),
                        "Clearance Date": entry.get("clearanceDate"),
                        "Transaction Date": entry.get("transactionDate"),
                    })

            df_ct = pd.DataFrame(extracted_list)
            df_ct = df_ct[df_ct["Client Code"].notna() & (df_ct["Client Code"] != "")]
            df_ct["Client Code"] = df_ct["Client Code"].map(_clean_code)

            df_kyc = fetch_kyc_cached()
            df_rm = fetch_client_rm_map_cached()

            df_kyc["Client Code"] = df_kyc["Client Code"].map(_clean_code)
            df_rm["Client Code"] = df_rm["Client Code"].map(_clean_code)

            df_merged = df_ct.merge(
                df_rm[["Client Code", "Client Name", "BRO"]],
                on="Client Code", how="left",
            )
            df_merged[["Client Name", "BRO"]] = df_merged[["Client Name", "BRO"]].fillna("N/A")

            df_final = df_merged[["Client Code", "Client Name", "BRO", "drAmount", "Clearance Date", "Transaction Date"]]
            df_final = df_final.drop(columns=["Client Name"])

            df_final = df_final.merge(
                df_kyc[["Client Code", "Client Name", "Branch"]],
                on="Client Code", how="left",
            )
            df_final["BRO"] = df_final["BRO"].fillna("N/A")
            df_final.sort_values(by="BRO", inplace=True)
            df_final["Branch"] = df_final["Branch"].fillna("UNKNOWN").astype(str).str.upper().str.strip()
            df_final["Branch"] = df_final["Branch"].replace(helper.get_branch_code_mapping())
            df_final["Client Name"] = df_final["Client Name"].str.upper().str.strip()

            df_final = df_final[["BRO", "Client Code", "Client Name", "Branch", "drAmount", "Clearance Date", "Transaction Date"]]
            df_final.rename(columns={"drAmount": "Cash In Amount"}, inplace=True)
            df_final.drop(columns=["Clearance Date", "Transaction Date"], inplace=True)

            all_branches = [b.upper() for b in helper.get_work_locations()]
            branch_grouped = df_final.groupby("Branch")["Cash In Amount"].sum().reset_index()
            missing = [b for b in all_branches if b not in branch_grouped["Branch"].values]
            if missing:
                branch_grouped = pd.concat([branch_grouped, pd.DataFrame({"Branch": missing, "Cash In Amount": 0.0})], ignore_index=True)
            branch_grouped.sort_values(by="Cash In Amount", ascending=False, inplace=True)

            if self.role == "BRO":
                alias = helper.get_alias_name(self.username)
                df_final = df_final[df_final["BRO"] == alias]
            elif self.role == "BM":
                branch_val = (self.branch or "").strip().upper()
                df_final = df_final[df_final["Branch"] == branch_val]

            bro_summary = df_final.groupby("BRO")["Cash In Amount"].sum().reset_index()
            bro_summary.sort_values(by="Cash In Amount", ascending=False, inplace=True)

            self.show_tabbed_dataframes(df_final, bro_summary, branch_grouped)

        except Exception:
            st.error("An unexpected error occurred. Please contact IT department.", icon="❌")
            st.stop()

    def show_tabbed_dataframes(self, df_final, bro_summary, branch_summary):
        st.metric("Total Cash In", value=f"Rs. {df_final['Cash In Amount'].sum():,.2f}")

        tabs = st.tabs(["BRANCH", "BRO", "ALL"])
        fmt = {"Cash In Amount": "{:,.2f}"}

        with tabs[0]:
            branch_summary = branch_summary.reset_index(drop=True)
            branch_summary.index += 1
            st.dataframe(branch_summary.style.format(fmt), use_container_width=True)

        with tabs[1]:
            bro_summary = bro_summary.reset_index(drop=True)
            bro_summary.index += 1
            st.dataframe(bro_summary.style.format(fmt), use_container_width=True)

        with tabs[2]:
            df_final = df_final.reset_index(drop=True)
            df_final.index += 1
            st.dataframe(df_final.style.format(fmt), use_container_width=True)

    def render_page(self):
        try:
            self.show_expander_with_date_range()
        except Exception:
            st.error("An unexpected error occurred. Please contact IT department.", icon="❌")
            st.stop()


if __name__ == "__main__":
    CashInOut().render_page()
