import pandas as pd
import streamlit as st
from streamlit_bridge.navigation import render_sidebar
from db import db
from utils import auth_utils, helper
from pages.BasePage import BasePage

st.cache_data(ttl=600)
def get_category_client_data_cached():
    df = db.fetch_category_client_data()
    return df

def prepare_due_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    df["rmName"] = df["rmName"].fillna("Unknown")
    df["clientName"] = df["clientName"].fillna("")
    df["clientCode"] = df["clientCode"].fillna("")
    df["adjustedBalance"] = pd.to_numeric(df["adjustedBalance"], errors="coerce").fillna(0)

    # Null / blank category => UNCATEGORIZED
    df["category"] = df["category"].fillna("").astype(str).str.strip()
    df["category"] = df["category"].replace("", "UNCATEGORIZED")

    # Keep only clients with due
    # df = df[df["adjustedBalance"] > 0].copy()

    return df


def build_rm_due_summary(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = prepare_due_dataframe(df_raw)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "rmName",
                "CASH",
                "T+2",
                "DUE",
                "MTF",
                "UNCATEGORIZED",
                "Adjusted Balance",
                "total_client",
            ]
        )

    summary = (
        df.pivot_table(
            index="rmName",
            columns="category",
            values="adjustedBalance",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    summary.columns.name = None

    expected_categories = ["CASH", "T+2", "DUE", "MTF", "UNCATEGORIZED"]
    for col in expected_categories:
        if col not in summary.columns:
            summary[col] = 0

    total_clients_df = (
        df.groupby("rmName", as_index=False)["clientCode"]
        .nunique()
        .rename(columns={"clientCode": "total_client"})
    )

    summary = summary.merge(total_clients_df, on="rmName", how="left")

    summary["Adjusted Balance"] = (
        summary["CASH"]
        + summary["T+2"]
        + summary["DUE"]
        + summary["MTF"]
        + summary["UNCATEGORIZED"]
    )

    summary["total_client"] = summary["total_client"].fillna(0).astype(int)

    summary = summary[
        [
            "rmName",
            "CASH",
            "T+2",
            "DUE",
            "MTF",
            "UNCATEGORIZED",
            "Adjusted Balance",
            "total_client",
        ]
    ].sort_values(by="Adjusted Balance", ascending=False).reset_index(drop=True)

    return summary


def get_rm_detail_data(df_raw: pd.DataFrame, rm_name: str):
    df = prepare_due_dataframe(df_raw)
    df_rm = df[df["rmName"] == rm_name].copy()

    if df_rm.empty:
        empty_clients = pd.DataFrame(
            columns=["clientName", "clientCode", "category", "adjustedBalance"]
        )
        empty_category = pd.DataFrame(
            {
                "Category": ["CASH", "T+2", "DUE", "MTF", "UNCATEGORIZED"],
                "Due Amount": [0, 0, 0, 0, 0],
                "Client Count": [0, 0, 0, 0, 0],
            }
        )
        return empty_clients, empty_category, 0, 0, {
            "CASH": 0,
            "T+2": 0,
            "DUE": 0,
            "MTF": 0,
            "UNCATEGORIZED": 0,
        }

    client_df = (
        df_rm.groupby(
            ["clientName", "clientCode", "category"], as_index=False
        )["adjustedBalance"]
        .sum()
        .sort_values(by=["category", "adjustedBalance"], ascending=[True, False])
        .reset_index(drop=True)
    )

    category_amount_df = (
        df_rm.groupby("category", as_index=False)["adjustedBalance"]
        .sum()
        .rename(columns={"category": "Category", "adjustedBalance": "Due Amount"})
    )

    category_count_df = (
        df_rm.groupby("category")["clientCode"]
        .nunique()
        .reset_index()
        .rename(columns={"category": "Category", "clientCode": "Client Count"})
    )

    category_df = category_amount_df.merge(category_count_df, on="Category", how="outer")

    expected_categories = ["CASH", "T+2", "DUE", "MTF", "UNCATEGORIZED"]
    category_df = (
        category_df.set_index("Category")
        .reindex(expected_categories, fill_value=0)
        .reset_index()
    )

    total_due_clients = df_rm["clientCode"].nunique()
    total_due_amount = df_rm["adjustedBalance"].sum()

    count_map = {
        row["Category"]: int(row["Client Count"])
        for _, row in category_df.iterrows()
    }

    return client_df, category_df, total_due_clients, total_due_amount, count_map


@st.dialog("BRO Category-wise Insights", width="large", icon="📊")
def show_rm_due_dialog(df_raw: pd.DataFrame, rm_name: str):
    client_df, category_df, total_due_clients, total_due_amount, count_map = get_rm_detail_data(df_raw, rm_name)

    st.subheader(f"BRO: {rm_name}")

    col1, col2 = st.columns(2)
    col1.metric("Total Clients Tagged", f"{total_due_clients:,}")
    col2.metric("Total Due Amount", f"{total_due_amount:,.2f}")
    st.divider()
    st.markdown("### Category-wise Client Count")
    if count_map.get("UNCATEGORIZED", 0) > 0:
        c1, c2, c3, c4, c5 = st.columns(5)
    else:
        c1, c2, c3, c4 = st.columns(4)
    c1.metric("CASH", count_map.get("CASH", 0))
    c2.metric("T+2", count_map.get("T+2", 0))
    c3.metric("DUE", count_map.get("DUE", 0))
    c4.metric("MTF", count_map.get("MTF", 0))
    if count_map.get("UNCATEGORIZED", 0) > 0:
        c5.metric("UNCATEGORIZED", count_map.get("UNCATEGORIZED", 0))

    st.markdown("### Category-wise Due Summary")
    category_df['Due Amount'] = category_df['Due Amount'].apply(lambda x: f"{x:,.2f}")
    category_df['Client Count'] = category_df['Client Count'].apply(lambda x: f"{x:,}")
    category_df.rename(columns={"Due Amount": "ADJUSTED DUE BALANCE", "Client Count": "CLIENT COUNT", "Category":"CATEGORY"}, inplace=True)
    category_df.reset_index(drop=True, inplace=True)
    category_df.index += 1
    st.dataframe(category_df, width="stretch")

    st.markdown("### Client-wise Due Detail")
    # Category filter with default ALL
    categories = sorted(client_df["category"].dropna().unique().tolist())
    filter_options = ["ALL"] + categories
    col1, col2 = st.columns(2)
    with col1:
        selected_category = st.selectbox(
            "Filter by Category",
            options=filter_options,
            index=0
        )

    # Apply filter
    filtered_df = client_df.copy()
    if selected_category != "ALL":
        filtered_df = filtered_df[filtered_df["category"] == selected_category]

    # Format for display
    filtered_df = filtered_df.sort_values(by="adjustedBalance", ascending=False).reset_index(drop=True)
    filtered_df["adjustedBalance"] = filtered_df["adjustedBalance"].apply(lambda x: f"{x:,.2f}")
    filtered_df.index += 1
    filtered_df.rename(columns={"adjustedBalance": "ADJUSTED DUE BALANCE", "category": "CATEGORY", 
                                "clientName": "CLIENT NAME", "clientCode": "CLIENT CODE"}, inplace=True)

    st.badge(f"Total clients in view: {len(filtered_df):,.2f}")
    st.dataframe(filtered_df, width="stretch")


def format_due_summary(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()
    money_cols = ["CASH", "T+2", "DUE", "MTF", "UNCATEGORIZED", "Adjusted Balance"]

    for col in money_cols:
        formatted[col] = pd.to_numeric(formatted[col], errors="coerce").fillna(0).map(lambda x: f"{x:,.2f}")

    formatted["total_client"] = pd.to_numeric(
        formatted["total_client"], errors="coerce"
    ).fillna(0).astype(int)

    return formatted





class Reports(BasePage):
    def __init__(self):
        super().__init__()
        if 'page_config_set' not in st.session_state:
            st.set_page_config(page_title="Reports", page_icon="📂", layout="wide")
            st.session_state.page_config_set = True
        
        st.session_state.active_menu = "business"        
        helper.eliminate_top_margin("-4rem")
        st.header("📂 Reports", anchor=False)
        
        render_sidebar()

    @st.cache_data(ttl=600)
    def get_cached_tms_report(_self):
        df = db.get_tms_limit_report()
        if df is None or df.empty:
            return pd.DataFrame()
            
        df = df.drop(columns=['id'], errors='ignore').rename(columns={
            'client_code': 'Client Code',
            'client_name': 'Client Name',
            'category': 'Category',
            'bro': 'BRO',
            'status': 'Status',
            'reason': 'Reason',
            'ledger_type': 'Ledger Type',
            'ledger_balance': 'Ledger Balance',
            'created_date_time': 'Created Date Time'
        })
        
        # Ensure Ledger Balance is numeric
        df['Ledger Balance'] = pd.to_numeric(df['Ledger Balance'], errors='coerce').fillna(0)
        
        # Convert to proper datetime objects for logical sorting/filtering
        df['Created Date Time'] = pd.to_datetime(df['Created Date Time'], errors='coerce')
        
        cols = ['BRO'] + [c for c in df.columns if c != 'BRO']
        return df[cols]



    def tms_limit_ui(self, col2, col3):
        df = self.get_cached_tms_report()

        if not df.empty:
            # Prepare Date options: "All" + sorted unique dates
            unique_dates = sorted(df['Created Date Time'].dt.strftime('%Y-%m-%d').unique(), reverse=True)
            date_options = ["All"] + unique_dates
            
            # 2. Date Filter (Defaults to Latest Date)
            with col2:
                selected_date = st.selectbox("Select Date", date_options, index=1) # Index 1 is the latest date
            
            if selected_date != "All":
                df = df[df['Created Date Time'].dt.strftime('%Y-%m-%d') == selected_date]

            # 3. Secondary Filter (Specific columns only)
            filter_columns = ['None', 'BRO', 'Client Code', 'Client Name', 'Category', 'Status', 'Ledger Type']
            
            with col3:
                filter_col = st.selectbox("Filter By", filter_columns)
                if filter_col != 'None':
                    unique_values = sorted(df[filter_col].dropna().unique().tolist())
                    selected_val = st.selectbox(f"Select {filter_col}", unique_values)
                    df = df[df[filter_col] == selected_val]

            # --- Data Processing for Display ---
            
            # Calculate sums BEFORE string conversion
            success_sum = df[df['Status'].str.upper() == 'SUCCESS']['Ledger Balance'].sum()
            
            # Format for display
            display_df = df.copy()
            display_df['Ledger Balance'] = display_df['Ledger Balance'].apply(lambda x: f"{x:,.2f}")
            display_df['Created Date Time'] = display_df['Created Date Time'].dt.strftime('%Y-%m-%d')
            
            display_df.reset_index(drop=True, inplace=True)
            display_df.index += 1

            # Display Badges
            col_b1, spacer, col_b2 = st.columns([1, 0.1, 6])
            with col_b1:
                st.badge(f"Total clients: {len(display_df):,.0f}", color='green')
            with col_b2:
                st.badge(f"Total Limit Issued: {success_sum:,.2f}", color='orange')

            # Render Table
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No data found for TMS Limit.")




    @st.cache_data(ttl=600)
    def get_cached_floorsheet_report(_self):
        df = db.get_floorsheet_summary()
        if df.empty:
            return pd.DataFrame()
            
        df.rename(columns={
            'date': 'Date', 
            'branch': 'Branch', 
            'transaction_type': 'Transaction Type', 
            'total_amount': 'Total Amount'
        }, inplace=True)
        
        # --- Update Branch Codes to Full Names ---
        mapping = helper.get_branch_code_mapping()
        # .map() replaces the code with the name; .fillna() keeps the original if not found in dict
        df['Branch'] = df['Branch'].map(mapping).fillna(df['Branch'])
        
        df['Transaction Type'] = df['Transaction Type'].str.upper()
        df['Date'] = df['Date'].astype(str)
        return df

    def branch_turnover_ui(self, col2, col3):
        df = self.get_cached_floorsheet_report()
        
        if df.empty:
            st.info("No floorsheet data found.")
            return

        # col2, col3 = st.columns(2)

        # 1. Date Filter (Latest Date as default is index 1, "All" is index 0)
        unique_dates = sorted(df['Date'].unique().tolist(), reverse=True)
        date_options = ["All"] + unique_dates
        with col2:
            selected_date = st.selectbox("Filter by Date", date_options, index=0)
            if selected_date != "All":
                df = df[df['Date'] == selected_date]

        # 2. Branch Filter (Now shows Full Names)
        unique_branches = sorted(df['Branch'].unique().tolist())
        branch_options = ["All"] + unique_branches
        with col3:
            selected_branch = st.selectbox("Filter by Branch", branch_options, index=0)
            if selected_branch != "All":
                df = df[df['Branch'] == selected_branch]

        # --- Calculations (Numeric) ---
        total_sum = df['Total Amount'].sum()
        buy_sum = df[df['Transaction Type'] == 'BUY']['Total Amount'].sum()
        sell_sum = df[df['Transaction Type'] == 'SELL']['Total Amount'].sum()
        st.divider()
        # --- UI Metrics ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Turnover", f"Rs. {total_sum:,.2f}", border=True)
        m2.metric("Total Buy", f"Rs. {buy_sum:,.2f}", border=True)
        m3.metric("Total Sell", f"Rs. {sell_sum:,.2f}", border=True,)

        # st.divider()

        # --- Display Formatting for Table ---
        display_df = df.copy()
        display_df['Total Amount'] = display_df['Total Amount'].apply(lambda x: f"{x:,.2f}")
        
        display_df.reset_index(drop=True, inplace=True)
        display_df.index += 1

        st.dataframe(display_df, use_container_width=True)

    def render_page(self):
        col1, col2, col3 = st.columns(3)
        report_options = ['Categorized Adjusted Due Balance' ,
                          'TMS Limit','Branch Turnover' , 
                          'EDIS Call', 'Others', 'None']
        with col1:
            selected_type = st.selectbox("Report Type", report_options, index=0)
        with st.spinner(f"Loading {selected_type} report...", show_time=True):
            if selected_type == 'TMS Limit':
                self.tms_limit_ui(col2, col3)
            elif selected_type == 'Branch Turnover':
                self.branch_turnover_ui(col2, col3)
            
            
            # ---------------------------------------------------
            # Streamlit UI
            # ---------------------------------------------------
            elif selected_type == "Categorized Adjusted Due Balance":
                df_raw = get_category_client_data_cached()
                latest_update = df_raw["due_uploaded_at_ts"].dropna().max()
                df_summary = build_rm_due_summary(df_raw).copy()

                display_df = df_summary.copy()

                display_df.rename(columns={
                    "rmName": "BRO",
                    "Adjusted Balance": "ADJUSTED DUE BALANCE",
                    "total_client": "TOTAL CLIENTS"
                }, inplace=True)

                display_df.sort_values(by="ADJUSTED DUE BALANCE", ascending=False, inplace=True)
                display_df.reset_index(drop=True, inplace=True)

                # display_df["TOTAL CLIENTS"] = display_df["TOTAL CLIENTS"].apply(lambda x: f"{x:,}")
                money_cols = ["CASH", "T+2", "DUE", "MTF", "UNCATEGORIZED", "ADJUSTED DUE BALANCE", "TOTAL CLIENTS"]
                for col in money_cols:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}")
                col1, col2 = st.columns([1, 6])
                with col1:
                    st.badge(f"Total BROs: {len(display_df):,.0f}", color='green')
                with col2:
                    st.badge(f"Last Updated Due List: {latest_update.strftime('%Y-%m-%d %I:%M:%S %p') if pd.notna(latest_update) else 'N/A'}", color='blue')
                selected = st.dataframe(
                    display_df,
                    width="stretch",
                    hide_index=True,
                    key="category_dues",
                    on_select="rerun",
                    selection_mode="single-row",
                )

                selected_rows = selected.get("selection", {}).get("rows", [])

                if selected_rows:
                    selected_idx = selected_rows[0]
                    selected_rm = display_df.iloc[selected_idx]["BRO"]
                    show_rm_due_dialog(df_raw, selected_rm)

if __name__ == "__main__":
    Reports().render_page()