import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils.custom_hotkey import activate_client_code_hotkey
from utils import helper
from db import db
import streamlit_bridge.navigation as navigation
from pages.BasePage import BasePage

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_top_brokers_cached(start_date, end_date):
    return db.fetch_top_brokers_by_date(start_date, end_date)

@st.cache_data(ttl=3600)
def fetch_and_process_data(start_date: date, end_date: date) -> pd.DataFrame:
    df = db.fetch_top_brokers_by_date(start_date, end_date)
    cols_to_convert = ["totalAmount", "buyerAmount", "sellerAmount", "matchingAmount"]
    for col in cols_to_convert:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors='coerce')
    return df

@st.cache_data(ttl=600, show_spinner=False)
def fetch_floorsheet_cached(start_date, end_date):
    return db.fetch_floorsheet_by_date_range(start_date, end_date)

@st.cache_data(ttl=600, show_spinner=False)
def fetch_broker_totals_cached(start_date, end_date, trishakti_code):
    return db.fetch_floorsheet_branch_totals(start_date, end_date, trishakti_code)

class BusinessTurnover(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_padding()
        st.session_state.active_menu = "business"
        activate_client_code_hotkey()
        st.set_page_config("Broker Business Trunover", page_icon="🅱️", layout='wide')
        navigation.render_sidebar()
        st.header("🅱️ Broker Business Trunover", anchor=False)

    # -------------------------------
    # Helper: Rename columns
    # -------------------------------
    def rename_columns(self, df: pd.DataFrame):
        return df.rename(columns={
            'name': 'Broker Name', 'number': 'Broker Number',
            'buyerAmount': 'Buyer Amount', 'sellerAmount': 'Seller Amount',
            'differ': 'Difference', 'matchingAmount': "Matching Amount",
            'totalAmount': 'Total Amount', 'date': 'Date', 'DT_Row_Index': 'Rank'
        })

    # -------------------------------
    # Normal View: Date Selection
    # -------------------------------
    def show_date_selection_ui(self):
        col1, col2, col3 = st.columns(3)
        with col1:
            fiscal_year_date = st.selectbox("Fiscal year", ['-select-', '81/82', '82/83', '83/84'], index=3)
            start_d, end_d = helper.get_fiscal_year_dates(fiscal_year=fiscal_year_date)
        with col2:
            start_date = st.date_input("Start date", start_d)
            self.start_date = start_date
        with col3:
            end_date = st.date_input("End date", end_d)
            self.end_date = end_date

        if start_date > end_date:
            st.error("Start date cannot be greater than end date", icon="📢")
            st.stop()
        self.calculate_and_show_data(start_date=start_date, end_date=end_date)

    def calculate_and_show_data(self, start_date, end_date):
        df = fetch_top_brokers_cached(start_date, end_date)
        if df.empty:
            st.info("No data found for selected fiscal period")
            st.stop()

        df = df.sort_values(by=['date', 'DT_Row_Index'], ascending=[True, True])

        cols_to_convert = ["totalAmount", "buyerAmount", "sellerAmount", "matchingAmount"]
        for col in cols_to_convert:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors='coerce')

        broker_options = df[["number", "name"]].drop_duplicates().copy()
        broker_options["number"] = broker_options["number"].astype(int)
        broker_options = broker_options.sort_values("number", ascending=True)
        broker_options_list = broker_options.apply(lambda row: f"{row['number']} - {row['name']}", axis=1).tolist()

        filter_value = st.selectbox("Select Broker", ["None"] + broker_options_list)

        if 'checked' not in st.session_state or filter_value == "None":
            st.session_state.checked = False

        agg_checkbox = st.checkbox("Aggregate Data", value=st.session_state.checked)
        st.divider()

        if agg_checkbox:
            st.session_state.checked = True
            broker_summary_df = (
                df.groupby("name", as_index=False)
                .agg(total_turnover=("totalAmount", "sum"), trade_days=("totalAmount", "count"))
                .sort_values("total_turnover", ascending=False)
            )
            broker_summary_df = broker_summary_df.rename(columns={
                'name': 'Broker Name', 'total_turnover': 'Total Turnover', 'trade_days': 'Trade Days'
            }).reset_index(drop=True)
            broker_summary_df.index += 1

            trishakti_row = broker_summary_df[broker_summary_df["Broker Name"].str.strip().str.lower() == "trishakti securities public limited"]
            if not trishakti_row.empty:
                turnover = trishakti_row["Total Turnover"].iloc[0]
                rank = trishakti_row.index[0]
                st.badge(f"Trishakti Turnover: {turnover:,.2f}", color="green")
                st.badge(f"Trishakti's Rank: {rank}", color='blue')

            broker_summary_df["Total Turnover"] = broker_summary_df["Total Turnover"].map("{:,.2f}".format)
            st.dataframe(broker_summary_df, use_container_width=True)
            st.stop()

        df = df.reset_index(drop=True)
        df.index += 1

        total_market_turnover = (df["totalAmount"].sum()/2)
        trishakti_turnover = df.loc[df["name"].str.strip().str.lower() == "trishakti securities public limited","totalAmount"].sum()

        if filter_value != 'None':
            selected_number = int(filter_value.split(" - ")[0].strip())
            selected_name = filter_value.split(" - ")[1].strip()
            filtered_df = df[df["number"].astype(int) == selected_number]
            other_turnover_total = filtered_df['totalAmount'].sum()

        st.metric("🟡 NEPSE Total Turnover", f"NPR {total_market_turnover:,.2f}", border=True)
        kpi_col1, kpi_col2 = st.columns(2)
        with kpi_col1:
            st.metric("🔵 Trishakti Total Turnover", f"NPR {trishakti_turnover:,.2f}", border=True)
        with kpi_col2:
            total_contribution = (trishakti_turnover / total_market_turnover) * 100
            st.metric(f"🔵 Trishakti Market Contribution", f"{total_contribution:.4f} %", border=True)
        
        col1, col2 = st.columns(2)
        if filter_value != 'None':
            with col1:
                st.metric(f"⚪ {selected_name} Total Turnover", f"NPR {other_turnover_total:,.2f}", border=True)
            with col2:
                total_contribution = (other_turnover_total / total_market_turnover) * 100
                st.metric(f"⚪ {selected_name} Market Contribution", f"{total_contribution:.4f} %", border=True)

        show_reference = st.toggle("Show Reference")
        if show_reference:
            st.badge(f"Total rows: {len(df)}")
            df = self.rename_columns(df)
            first_cols = ["Broker Name", "Broker Number", "Rank"]
            new_order = first_cols + [c for c in df.columns if c not in first_cols]
            df = df[new_order]
            numeric_cols = df.select_dtypes(include=['float64']).columns
            for col in numeric_cols:
                df[col] = df[col].map("{:,.2f}".format)
            st.dataframe(df, use_container_width=True)


    def show_top_brokers_view(self):
        selected_date = st.date_input("Select Date", width=400)
        if selected_date:
            date_str = selected_date.strftime('%Y-%m-%d')
            df = db.fetch_top_brokers(date=date_str)

            df.drop(columns=['date', 'DT_Row_Index'], inplace=True)
            df.rename(columns={
                "name": "Broker Name", "number": "Broker No.",
                "buyerAmount": "Buyer Amount (Rs.)", "sellerAmount": "Seller Amount (Rs.)",
                "totalAmount": "Total Amount (Rs.)", "differ": "Difference (Rs.)",
                "matchingAmount": "Matching Amount (Rs.)"
            }, inplace=True)
            df.index = df.index + 1
            numeric_cols = df.columns.difference(['Broker Name', 'Broker No.'])
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

            if not df.empty:
                idx = df.index[df['Broker Name'] == 'Trishakti Securities Public Limited'].tolist()
                st.badge(f"Trishakti's Rank: {idx[0]}", color='green')
                st.dataframe(df.style.format({col: "{:,.0f}" for col in numeric_cols}))
            else:
                st.info("No data available for selected date.", icon="📢")

    # -------------------------------
    # Our Brokers View
    # -------------------------------
    def show_our_brokers_view(self):
        col1, col2, col3 = st.columns(3)
        with col1:
            fiscal_year_date = st.selectbox("Fiscal year", ['-select-', '82/83', '83/84'], index=2)
            start_d, end_d = helper.get_fiscal_year_dates(fiscal_year=fiscal_year_date)
        with col2:
            start_date = st.date_input("Start date", start_d)
        with col3:
            end_date = st.date_input("End date", end_d)

        if start_date > end_date:
            st.error("Start date cannot be greater than end date", icon="📢")
            st.stop()

        try:
            with st.spinner("Loading floorsheet data..."):
                trishakti_code = None
                top_df = fetch_top_brokers_cached(start_date, end_date)
                if not top_df.empty:
                    tri_row = top_df[top_df["name"].str.strip().str.lower() == "trishakti securities public limited"]
                    if not tri_row.empty:
                        trishakti_code = str(int(tri_row["number"].iloc[0]))

                if not trishakti_code:
                    st.info("Trishakti broker code not found")
                    st.stop()

                table = fetch_broker_totals_cached(start_date, end_date, trishakti_code)

            if table.empty:
                st.info("No floorsheet data found for selected period")
                st.stop()

            table["total_turnover"] = table["purchase_turnover"] + table["sell_turnover"]
            total_all = table.loc[table["branch"] != "TOTAL", "total_turnover"].sum()
            table["Branch Contribution"] = (table["total_turnover"] / total_all * 100).round(2) if total_all != 0 else 0

            table.index += 1
            for col in ["purchase_turnover", "sell_turnover", "total_turnover"]:
                table[col] = table[col].map("{:,.2f}".format)
            table["Branch Contribution"] = table["Branch Contribution"].map("{:.2f}%".format)

            st.dataframe(table, use_container_width=True)
        except Exception:
            st.error("Failed to load floorsheet data. Please try again.")

    # -------------------------------
    # Render Page
    # -------------------------------
    def render_page(self):
        view = st.radio("View", ['Normal', 'Compare', 'Top Brokers'], horizontal=True)
        # view = st.radio("View", ['Normal', 'Compare', 'Top Brokers', 'Our Brokers'], horizontal=True)
        st.divider()
        if view == "Normal":
            self.show_date_selection_ui()
        elif view == "Top Brokers":
            self.show_top_brokers_view()
        # elif view == "Our Brokers":
        #     self.show_our_brokers_view()
        elif view == "Compare":
            col1, col2 = st.columns([1,1])
            with col1:
                first_fiscal_year_date = st.selectbox("1st Fiscal year", ['-select-', '81/82', '82/83', '83/84'], index=3)
                first_fy_start_date, fist_fy_end_date = helper.get_fiscal_year_dates(fiscal_year=first_fiscal_year_date)
            with col2:
                second_fiscal_year_date = st.selectbox("2nd Fiscal year", ['-select-', '81/82', '82/83', '83/84'], index=2)
                second_fy_start_date, second_fy_end_date = helper.get_fiscal_year_dates(fiscal_year=second_fiscal_year_date)
            if first_fiscal_year_date == second_fiscal_year_date:
                st.info(f"You cannot compare with same fiscal year. Choose different fiscal year.", icon="📢")
                st.stop()

            compare_period = st.radio("Period", ['1M', '2M', '3M', '4M', '5M', '6M', '7M', '8M', '9M', '10M', '11M', '12M'], horizontal=True)

            days_map = {
                '1M': 30, '2M': 60, '3M': 90, '4M': 120,
                '5M': 151, '6M': 181, '7M': 212, '8M': 243,
                '9M': 273, '10M': 304, '11M': 334, '12M': 365
            }

            days = days_map[compare_period]

            first_start = first_fy_start_date
            first_end = first_fy_start_date + timedelta(days=days - 1)

            second_start = second_fy_start_date
            second_end = second_fy_start_date + timedelta(days=days - 1)

            first_fy_df = fetch_and_process_data(first_start, first_end)
            second_fy_df = fetch_and_process_data(second_start, second_end)

            nepse_turnover_1 = first_fy_df['totalAmount'].sum()
            nepse_turnover_2 = second_fy_df['totalAmount'].sum()
            turnover1 = first_fy_df[first_fy_df['name'].str.lower() == "trishakti securities public limited"]['totalAmount'].sum()
            turnover2 = second_fy_df[second_fy_df['name'].str.lower() == "trishakti securities public limited"]['totalAmount'].sum()

            diff = turnover2 - turnover1
            pct = (diff / turnover1 * 100) if turnover1 != 0 else 0
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🟡Nepse Turnover FY 81/82", f"{nepse_turnover_1:,.2f}", border=True)
            with col2:
                st.metric("🟡 Nepse Turnover FY 82/83", f"{nepse_turnover_2:,.2f}", border=True)
            col1, col2 = st.columns(2)
            with col1:
                label = "🔴 Trishakti Turnover in FY" if diff < 0 else "🟢 Trishakti Turnover in FY"
                st.metric(f"{label} {first_fiscal_year_date}:", f"Rs. {turnover1:,.2f}", border=True)
            with col2:
                label = "🔴 Trishakti Turnover in FY" if diff < 0 else "🟢 Trishakti Turnover in FY"
                st.metric(f"{label} {second_fiscal_year_date}:", f"Rs.{turnover2:,.2f}", border=True)

            col1, col2 = st.columns(2)
            with col1:
                label = "🔴 Shortage by" if diff < 0 else "🟢 Exceed by"
                if diff < 0:
                    st.metric(label, f"Rs. -{abs(diff):,.2f}", border=True)
                else:
                    st.metric(label, f"Rs. {abs(diff):,.2f}", border=True)

            with col2:
                delta_color = "off" if diff == 0 else ("normal" if diff > 0 else "inverse")
                label = "🔴 Percentage" if diff < 0 else "🟢 Percentage"
                st.metric(label, f"{pct:+.2f}%", delta_color=delta_color, border=True)

        else:
            st.info("View not selected", icon="📢")
            st.stop()


if __name__ == "__main__":
    BusinessTurnover().render_page()
