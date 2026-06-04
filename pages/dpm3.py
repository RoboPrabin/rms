from api.ledger_api import dg_ledger_api
from datetime import date, datetime
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine
from utils.helper import get_holding_engine
from db import db
import streamlit_bridge.navigation as navigation
from nepali_datetime import date as nepali_date
from utils.custom_hotkey import activate_client_code_hotkey
from utils import helper
from pages.BasePage import BasePage


# ---------------------------------------------------------------------------
# Cached resources (persist across reruns)
# ---------------------------------------------------------------------------
@st.cache_resource(ttl=3600)
def get_cached_ledger_token():
    return db.get_jwt_token()

@st.cache_resource
def get_db_engine():
    return create_engine(get_holding_engine())


# ---------------------------------------------------------------------------
# Cached data helpers (persist across reruns with TTL)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_latest_holdings():
    df = db.get_latest_holdings_dpm3()
    return df


@st.cache_data(ttl=3600)
def get_dpm3_onhold():
    df = db.get_dpm3_onhold()
    df.rename(columns={'client_code':'CLIENT CODE', 'client_name':'CLIENT NAME', 'branch':'BRANCH',
                       'symbol':'SCRIPT','transaction_type':'TRANSACTION TYPE',
                       'quantity':'QUANTITY','status':'STATUS','settlement_date':'SETTLEMENT DATE',
                       'uploaded_at':'UPLOADED AT'}, inplace=True)
    df.drop(columns=['UPLOADED AT'], inplace=True)
    df['CLIENT NAME'] = df['CLIENT NAME'].str.upper()
    df['BRANCH'] = df['BRANCH'].str.upper()
    return df


@st.cache_data(ttl=3600)
def get_latest_closing_price():
    row = db.get_table_average_price()
    df = pd.DataFrame(row, columns=['symbol', 'closePrice'])
    return df


@st.cache_data(ttl=3600)
def get_client_rm_map():
    rows = db.get_table_rm_child_map()
    df = pd.DataFrame(rows, columns=["BRO", "CLIENT CODE"])
    return df


@st.cache_data(ttl=3600)
def get_cached_isin_data():
    return db.get_isin_data()


@st.cache_data(ttl=3600)
def get_cached_kyc():
    return db.get_kyc()


@st.cache_data(ttl=1200)
def get_dpm3_grouped_data():
    df = db.get_dpm3()
    df['CLIENT NAME'] = df['CLIENT NAME'].str.upper()
    df['BRANCH'] = df['BRANCH'].str.upper()
    group_keys = ["BRO", "CLIENT CODE", "CLIENT NAME", "BRANCH", "BOID"]
    sum_cols = [
        "FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE",
        "FREE SHARE VALUATION", "PLEDGE SHARE VALUATION", "TOTAL VALUATION"
    ]
    df_grouped = df.groupby(group_keys, as_index=False)[sum_cols].sum()
    df_grouped["SCRIPT COUNT"] = df.groupby(group_keys)["SCRIPT"].count().values
    column_order = group_keys + ["SCRIPT COUNT"] + sum_cols
    df_grouped = df_grouped[column_order]
    return df_grouped, df


@st.cache_data(ttl=3600)
def get_processed_holdings():
    """Fully processed holdings DataFrame with valuations computed (cached)."""
    df = get_latest_holdings()
    if df is None or df.empty:
        return pd.DataFrame()
    cols_to_drop = [col for col in ['STATUS', 'BOID'] if col in df.columns]
    df = df.drop(columns=cols_to_drop)
    df = df.rename(columns={'closePrice': 'CLOSE PRICE', 'rmName': 'BRO'})
    if 'BRO' not in df.columns:
        df['BRO'] = 'N/A'
    if 'LOCKIN BALANCE' not in df.columns:
        df['LOCKIN BALANCE'] = 0
    for col in ['FREE BALANCE', 'PLEDGE BALANCE', 'LOCKIN BALANCE']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['CLOSE PRICE'] = df['CLOSE PRICE'].astype(float)
    compute_valuations(df)
    return df


@st.cache_data(ttl=3600)
def get_close_price_date_str():
    df = get_latest_holdings()
    if df is None or df.empty:
        return ""
    dt = pd.to_datetime(df['UPDATED AT'].head(1).values[0])
    return dt.strftime("%Y-%m-%d %I:%M %p")


@st.cache_data(ttl=3600)
def get_merged_onhold():
    df = get_dpm3_onhold()
    if df is None or df.empty:
        return pd.DataFrame()
    return merge_onhold_with_closing_price(df)


@st.cache_data(ttl=3600)
def get_detailed_view_data():
    _, df_uploaded = get_dpm3_grouped_data()
    desired_cols = [
        "BRO", "SCRIPT", "CLIENT CODE", "CLIENT NAME", "BRANCH",
        "FREE BALANCE", "CLOSING PRICE", "FREE SHARE VALUATION",
        "PLEDGE SHARE VALUATION", "TOTAL VALUATION", "PLEDGE BALANCE",
        "CURRENT BALANCE",
    ]
    return df_uploaded[[c for c in desired_cols if c in df_uploaded.columns]].copy()


# ---------------------------------------------------------------------------
# Reusable helpers
# ---------------------------------------------------------------------------
def compute_valuations(df):
    df['FREE SHARE VALUATION'] = df['FREE BALANCE'] * df['CLOSE PRICE']
    df['PLEDGE SHARE VALUATION'] = df['PLEDGE BALANCE'] * df['CLOSE PRICE']
    df['TOTAL VALUATION'] = df['FREE SHARE VALUATION'] + df['PLEDGE SHARE VALUATION']
    return df


def format_numeric_columns(df, columns):
    present = [c for c in columns if c in df.columns]
    if not present:
        return df
    for col in present:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df[present] = df[present].applymap(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
    return df


def merge_onhold_with_closing_price(df_onhold):
    df_cp = get_latest_closing_price()
    df_onhold = df_onhold.merge(
        df_cp[['symbol', 'closePrice']],
        left_on="SCRIPT",
        right_on="symbol",
        how="left"
    ).drop(columns=['symbol']).rename(columns={'closePrice': 'CLOSE PRICE'})
    df_onhold['QUANTITY'] = pd.to_numeric(df_onhold['QUANTITY'], errors="coerce")
    df_onhold['CLOSE PRICE'] = pd.to_numeric(df_onhold['CLOSE PRICE'], errors="coerce")
    df_onhold['TOTAL VALUATION'] = df_onhold['QUANTITY'] * df_onhold['CLOSE PRICE']
    return df_onhold


# ---------------------------------------------------------------------------
# DPM3 Page
# ---------------------------------------------------------------------------
class DPM3(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin("-10rem")
        st.session_state.active_menu = "business"
        st.set_page_config("DPM3", page_icon="📦", layout='wide')
        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()
        activate_client_code_hotkey()
        navigation.render_sidebar()
        col1, col2, _ = st.columns([1, 2, 3])
        with col1:
            st.header("📦 DPM3", anchor=False)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("‎", icon="🧹", type='tertiary', help="Clear Cache. This operation shows latest updated data."):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("Cache cleared successfully.", icon="✅")
                st.rerun()

    # ------------------------------------------------------------------ #
    # Upload pipeline
    # ------------------------------------------------------------------ #
    def dump_data_to_db(self, df):
        group_keys = ["BRO", "CLIENT CODE", "CLIENT NAME", "BRANCH", "BOID"]
        existing_keys = [col for col in group_keys if col in df.columns]
        other_cols = [col for col in df.columns if col not in existing_keys]
        df = df[existing_keys + other_cols]
        engine = get_db_engine()
        df.to_sql(name="dpm3", con=engine, if_exists="replace", index=False)
        st.session_state.pop('dpm3', None)

    def extract_data_from_raw_txt_file(self, file_obj):
        columns_to_extract = {
            0: "BOID", 1: "ISIN", 2: "FREE BALANCE",
            4: "PLEDGE BALANCE", 10: "CURRENT BALANCE"
        }
        numeric_columns = ["FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE"]
        lines = file_obj.readlines()
        if lines and "~" not in lines[-1].decode("latin1"):
            lines = lines[:-1]
        data = []
        for line in lines:
            parts = line.decode("latin1").strip().split("~")
            row = {}
            for idx, col_name in columns_to_extract.items():
                value = parts[idx] if idx < len(parts) else ''
                if col_name == "BOID":
                    row[col_name] = str(value).strip()
                elif col_name in numeric_columns:
                    try:
                        row[col_name] = float(value)
                    except ValueError:
                        row[col_name] = 0.0
                else:
                    row[col_name] = value
            data.append(row)
        df = pd.DataFrame(data)
        df["SCRIPT"] = "NAN"
        df["CLOSING PRICE"] = 0.0
        df["FREE SHARE VALUATION"] = 0.0
        df["PLEDGE SHARE VALUATION"] = 0.0
        df["TOTAL VALUATION"] = 0.0
        df["STATUS"] = "SUNDAY DATA"
        return df

    def append_thursday_buy_data(self, df: pd.DataFrame, selected_date: date) -> pd.DataFrame:
        rows = db.get_floorsheet_from_date(selected_date)
        buy_df = pd.DataFrame(
            rows,
            columns=[
                "CLIENT CODE", "CLIENT NAME", "SCRIPT", "QUANTITY",
                "RATE", "AMOUNT", "TRANSACTION TYPE", "BRANCH", "TRADE DATE"
            ],
        )
        if buy_df.empty:
            return df
        buy_df["BRANCH"] = buy_df["BRANCH"].map(helper.get_branch_code_mapping()).fillna(buy_df["BRANCH"])
        agg_df = buy_df.groupby(
            ["CLIENT CODE", "CLIENT NAME", "SCRIPT", "BRANCH"], as_index=False
        ).agg({"QUANTITY": "sum"})
        boid_by_client_code = pd.Series(dtype="object")
        if "CLIENT CODE" in df.columns and "BOID" in df.columns:
            temp = df[["CLIENT CODE", "BOID"]].copy()
            temp["CLIENT CODE"] = temp["CLIENT CODE"].astype(str).str.strip()
            temp["BOID"] = temp["BOID"].astype(str).str.strip()
            temp = temp[(temp["CLIENT CODE"] != "") & (temp["BOID"] != "") & (temp["BOID"].str.upper() != "NAN")]
            if not temp.empty:
                boid_by_client_code = temp.drop_duplicates("CLIENT CODE").set_index("CLIENT CODE")["BOID"]
        thursday_df = pd.DataFrame({
            "BOID": agg_df["CLIENT CODE"].astype(str).str.strip().map(boid_by_client_code).fillna(""),
            "ISIN": "",
            "FREE BALANCE": agg_df["QUANTITY"].astype(float),
            "PLEDGE BALANCE": 0.0,
            "CURRENT BALANCE": agg_df["QUANTITY"].astype(float),
            "SCRIPT": agg_df["SCRIPT"],
            "CLIENT CODE": agg_df["CLIENT CODE"],
            "CLIENT NAME": agg_df["CLIENT NAME"],
            "BRANCH": agg_df["BRANCH"],
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "STATUS": "THURSDAY BUY",
        })
        combined = pd.concat([df, thursday_df], ignore_index=True, sort=False)
        return combined

    def enrich_with_isin(self, df):
        isin_rows = get_cached_isin_data()
        isin_df = pd.DataFrame(isin_rows, columns=["ISIN", "SCRIP"])
        merged = df.merge(isin_df, on="ISIN", how="left")
        merged["SCRIPT"] = merged["SCRIP"].fillna(merged["SCRIPT"])
        merged.drop(columns=["SCRIP"], inplace=True)
        return merged

    def enrich_with_client_code_and_branch(self, df):
        rows = get_cached_kyc()
        kyc_df = pd.DataFrame(rows, columns=["CLIENT CODE", "CLIENT NAME", "BRANCH", "BOID"])

        def safe_boid(x):
            try:
                if pd.notnull(x):
                    return str(int(float(x)))
                return ""
            except (ValueError, TypeError):
                return ""

        kyc_df["BOID"] = kyc_df["BOID"].apply(safe_boid)
        merged = df.merge(kyc_df, on="BOID", how="left")
        merged["CLIENT CODE"] = merged["CLIENT CODE"].fillna("N/F")
        merged["CLIENT NAME"] = merged["CLIENT NAME"].fillna("N/F")
        merged["BRANCH"] = merged["BRANCH"].fillna("N/F")
        merged['uploaded_at'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        return merged

    def enrich_with_close_price(self, df):
        rows = db.get_table_average_price()
        df_avp = pd.DataFrame(rows, columns=["SYMBOL", "closePrice"]).rename(columns={"SYMBOL": "SCRIPT"})
        merged = df.merge(df_avp, on="SCRIPT", how="left")
        merged["CLOSING PRICE"] = merged["closePrice"].astype(float).fillna(0.0)
        merged.drop(columns=["closePrice"], inplace=True)
        return compute_valuations(merged)

    def enrich_with_bro(self, df):
        rows = db.get_table_rm_child_map()
        bro_df = pd.DataFrame(rows, columns=["BRO", "CLIENT CODE"])
        merged = df.merge(bro_df, on="CLIENT CODE", how="left")
        merged["BRO"] = merged["BRO"].fillna("N/A")
        return merged

    # ------------------------------------------------------------------ #
    # Upload render (file-upload pipeline)
    # ------------------------------------------------------------------ #
    def render_upload_mode(self):
        result, value = db.is_this_week_file_uploaded()
        if not result:
            uploaded_file = st.file_uploader("Import DPM3 file", type=".txt")
            if uploaded_file is None:
                return
            thursday_buy_floorsheet_date = st.date_input(
                "Select thursday buy floorsheet date", value=helper.get_last_thursday()
            )
            if st.button("Upload DPM3 file"):
                with st.status("📤 Uploading DPM3 file...", expanded=True) as status:
                    steps = [
                        ("Cleaning DPM3 file", self.extract_data_from_raw_txt_file, [uploaded_file]),
                        ("Matching ISIN number", self.enrich_with_isin, []),
                        ("Extracting client code & branch info", self.enrich_with_client_code_and_branch, []),
                        ("Adding Thursday buy data", self.append_thursday_buy_data, [thursday_buy_floorsheet_date]),
                        ("Extracting close price", self.enrich_with_close_price, []),
                        ("Extracting BROs", self.enrich_with_bro, []),
                        ("Dumping data to db", self.dump_data_to_db, []),
                    ]
                    df = None
                    for i, (label, func, args) in enumerate(steps, 1):
                        status.update(label=f"Step {i}/{len(steps)}: {label}", state="running")
                        if df is None:
                            df = func(*args)
                        else:
                            df = func(df, *args)
                    status.update(label="✅ Upload Completed", state="complete", expanded=False)
        else:
            formatted_date = value.strftime("%Y-%m-%d")
            weekday_name = value.strftime("%A")
            st.info(f"‎ ‎ ‎ DPM3 file uploaded on: {formatted_date} ({weekday_name})", icon="📢")
            st.stop()

    @st.dialog("📑 Client Scripts Detail", width="large")
    def show_client_dialog(self, df: pd.DataFrame, label):
        st.subheader(label)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.badge(f"Script Count: {len(df)}", color="green")
        with col2:
            st.badge(f"Total Free Balance: {df['FREE BALANCE'].sum()}", color="blue")
        with col3:
            st.badge(f"Total Valuation: {df['TOTAL VALUATION'].sum():,.2f}", color="yellow")
        st.dataframe(df, use_container_width=True)

    # ------------------------------------------------------------------ #
    # Latest holdings view (table + client dialog)
    # ------------------------------------------------------------------ #
    def render_latest_holdings_mode(self):
        with st.spinner("Loading latest holdings. Please wait...", show_time=True):
            df_grouped, df_uploaded = get_dpm3_grouped_data()
        st.badge(f"Total rows: {len(df_grouped):,}", color="green")
        selection = st.dataframe(
            df_grouped,
            key="client_table",
            selection_mode="single-row",
            on_select="rerun"
        )
        if selection.selection.rows:
            row_idx = selection.selection.rows[0]
            selected_row = df_grouped.iloc[row_idx]
            selected_code = selected_row["CLIENT CODE"]
            client_label = selected_row["CLIENT NAME"]
            client_scripts = df_uploaded[df_uploaded["CLIENT CODE"] == selected_code].copy()
            client_scripts.reset_index(drop=True, inplace=True)
            client_scripts.index += 1
            view_cols = [
                "SCRIPT", "FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE",
                "CLOSING PRICE", "FREE SHARE VALUATION",
                "PLEDGE SHARE VALUATION", "TOTAL VALUATION"
            ]
            self.show_client_dialog(client_scripts[view_cols], f"👨🏻‍💻 {client_label} - {selected_code}")

    # ------------------------------------------------------------------ #
    # Detailed view
    # ------------------------------------------------------------------ #
    def render_detailed_view_mode(self):
        with st.spinner("Loading detailed holdings. Please wait...", show_time=True):
            df_all = get_detailed_view_data()
        with st.expander("Filters", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                filter_field = st.selectbox(
                    "Filter by",
                    ["SCRIPT", "BRANCH", "BRO", "CLIENT CODE", "CLIENT NAME"],
                    index=0,
                )
            options = sorted(
                df_all[filter_field]
                .dropna().astype(str).map(lambda x: x.strip())
                .loc[lambda s: s != ""]
                .unique().tolist()
            )
            with col2:
                selected_values = st.multiselect(f"Select {filter_field}", options=options)
        filtered = df_all
        if selected_values:
            filtered = filtered[filtered[filter_field].astype(str).str.strip().isin(selected_values)]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.badge(f"Total rows: {len(filtered):,}", color="green")
        with col2:
            st.badge(f"Total Free Balance: {filtered['FREE BALANCE'].sum():,.2f}", color="blue")
        with col3:
            st.badge(f"Total Valuation: {filtered['TOTAL VALUATION'].sum():,.2f}", color="yellow")
        max_elements = int(pd.get_option("styler.render.max_elements"))
        view_df = filtered.sort_values(by="CLIENT NAME")
        if view_df.size <= max_elements:
            numeric_cols = view_df.select_dtypes(include="number").columns.tolist()
            if numeric_cols:
                view_df[numeric_cols] = view_df[numeric_cols].applymap(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
        view_df.reset_index(drop=True, inplace=True)
        view_df.index = view_df.index + 1
        st.dataframe(view_df, width='stretch')

    # ------------------------------------------------------------------ #
    # Insert Thursday floorsheet into DB
    # ------------------------------------------------------------------ #
    def get_thursday_buy_floorsheet(self, selected_date):
        rows = db.get_floorsheet_from_date(selected_date)
        df = pd.DataFrame(rows, columns=[
            'CLIENT CODE', 'CLIENT NAME', 'SCRIPT', 'QUANTITY',
            'RATE', 'AMOUNT', 'TRANSACTION TYPE', 'BRANCH', 'TRADE DATE'
        ])
        df['BRANCH'] = df['BRANCH'].map(helper.get_branch_code_mapping()).fillna(df['BRANCH'])
        agg_df = df.groupby(
            ['CLIENT CODE', 'CLIENT NAME', 'SCRIPT', 'BRANCH'], as_index=False
        ).agg({'QUANTITY': 'sum', 'AMOUNT': 'sum'})
        agg_df['RATE'] = agg_df['AMOUNT'] / agg_df['QUANTITY']
        df['STATUS'] = 'THURSDAY BUY'
        db.insert_to_dpm3_bulk(df=agg_df)

    # ------------------------------------------------------------------ #
    # Main page
    # ------------------------------------------------------------------ #
    def _render_ledger_section(self, df):
        nepse_code = df['CLIENT CODE'].iloc[0]
        cache_key = f"ledger_{nepse_code}"
        if cache_key not in st.session_state:
            token = get_cached_ledger_token()
            from_date_default = "2025-07-17"
            to_date_str = datetime.now().strftime("%Y-%m-%d")
            ledger_data = dg_ledger_api.get_ledger(
                token=token, nepse_code=nepse_code,
                date_from=from_date_default, date_to=to_date_str
            )
            st.session_state[cache_key] = ledger_data
        else:
            ledger_data = st.session_state[cache_key]
        balance = float(ledger_data['balance'])
        balance_type = ledger_data['balanceType']
        unbilled_balance = sum(
            txn.get("credit", 0) for txn in ledger_data["ubilledTransactions"]
        )
        adjusted_balance = float(balance) - float(unbilled_balance)
        st.caption("💡 Ledger Information")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.badge(f"Unbilled Amount:{unbilled_balance:,.2f}", color="grey")
        with col2:
            st.badge(f"Adjusted Balance:{adjusted_balance:,.2f}", color="grey")
        with col3:
            st.badge(f"Balance:{balance:,.2f} {balance_type}", color="green")
        free_valuation_sum = df['FREE SHARE VALUATION'].sum()
        total_valuation_sum = df['TOTAL VALUATION'].sum()

    def _render_onhold_metrics(self, df_onhold):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.badge(f"Total Hold Scripts: {len(df_onhold):,}", color="green")
        with col2:
            st.badge(f"Total Hold Quantity: {df_onhold['QUANTITY'].sum():,.2f}", color="blue")
        with col3:
            st.badge(f"Total Hold Valuation: {df_onhold['TOTAL VALUATION'].sum():,.2f}", color="orange")

    def _render_onhold_table(self, df_onhold):
        df_onhold.index = df_onhold.index + 1
        col_order = [
            'CLIENT CODE', 'CLIENT NAME', 'BRANCH', 'SCRIPT', 'QUANTITY',
            'CLOSE PRICE', 'TOTAL VALUATION', 'TRANSACTION TYPE', 'STATUS', 'SETTLEMENT DATE'
        ]
        df_onhold = df_onhold[col_order]
        self._render_onhold_metrics(df_onhold)
        format_cols = ['QUANTITY', 'CLOSE PRICE', 'TOTAL VALUATION']
        present_fmt = [c for c in format_cols if c in df_onhold.columns]
        if present_fmt:
            df_onhold[present_fmt] = df_onhold[present_fmt].applymap(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
        st.dataframe(df_onhold, width='stretch')

    def _render_latest_holdings(self):
        with st.spinner("Loading latest holdings. Please wait...", show_time=True):
            df = get_processed_holdings()
            if df.empty:
                st.warning("No holdings data available.")
                return
            formatted_date = get_close_price_date_str()
            if formatted_date:
                st.caption(f"Note: Close Price updated on: {formatted_date}")
        col1, col2 = st.columns(2)
        with col1:
            filter_by = st.selectbox(
                "Filter by",
                options=["ALL", "CLIENT CODE", "SCRIPT", "BRANCH"]
            )
        if filter_by != "ALL":
            unique_values = sorted(df[filter_by].unique())
            with col2:
                selected_value = st.selectbox(f"Select {filter_by}", options=unique_values)
            df = df[df[filter_by] == selected_value].reset_index(drop=True)
        filter_point = False
        df_onhold = pd.DataFrame()
        with st.container(border=True):
            if filter_by in ["CLIENT CODE", "CLIENT NAME"]:
                filter_point = True
                df_onhold = get_merged_onhold()
                if not df_onhold.empty and filter_by in df_onhold.columns:
                    df_onhold = df_onhold[df_onhold[filter_by] == selected_value].reset_index(drop=True)
                if not df_onhold.empty:
                    self.total_valuation_all = df_onhold['TOTAL VALUATION'].sum() + df['FREE SHARE VALUATION'].sum()
                    self.total_scripts_all = len(df_onhold) + len(df)
                    col_a, col_b, col_c = st.columns([3, 1, 1])
                    with col_a:
                        st.metric("ℹ️ Overall Valuation", value=f"Rs. {self.total_valuation_all:,.2f}", border=True, width='content')
                    with col_b:
                        st.metric("🔖 Overall Scripts", value=f"{self.total_scripts_all:,.2f}", border=True, width='content')
                    with col_c:
                        st.metric("📊 Pledge Script", value=f"{len(df[df['PLEDGE BALANCE'] > 0]):,.2f}", border=True, width='content')
                    st.divider()
            if filter_by == "CLIENT CODE":
                self._render_ledger_section(df)
                st.divider()
            st.subheader("🟢 Current Holdings", anchor=False)
            with st.spinner("Loading current holdings data...", show_time=True):
                col3, col4, col5, col6 = st.columns(4)
                with col3:
                    label = "Total Scripts" if filter_point else "Total Rows"
                    st.badge(f"{label}: {len(df):,}", color="green")
                with col4:
                    st.badge(f"Total Valuation: {df['TOTAL VALUATION'].sum():,.2f}", color="blue")
                with col5:
                    st.badge(f"Total Free Valuation: {df['FREE SHARE VALUATION'].sum():,.2f}", color="green")
                with col6:
                    st.badge(f"Total Pledge Valuation: {df['PLEDGE SHARE VALUATION'].sum():,.2f}", color="red")
                column_order = [
                    'BRO', 'CLIENT CODE', 'CLIENT NAME', 'BRANCH', 'SCRIPT', 'CLOSE PRICE',
                    'TOTAL VALUATION', 'FREE BALANCE', 'PLEDGE BALANCE', 'LOCKIN BALANCE',
                    'FREE SHARE VALUATION', 'PLEDGE SHARE VALUATION'
                ]
                formatting_cols = [
                    'CLOSE PRICE', 'FREE BALANCE', 'PLEDGE BALANCE', 'LOCKIN BALANCE',
                    'FREE SHARE VALUATION', 'PLEDGE SHARE VALUATION', 'TOTAL VALUATION'
                ]
                df.sort_values(by="TOTAL VALUATION", ascending=False, inplace=True)
                df = format_numeric_columns(df, formatting_cols)
                df = df[column_order]
                df.reset_index(drop=True, inplace=True)
                df.index = df.index + 1
                st.dataframe(df, width='stretch')
            if filter_by in ["CLIENT CODE", "CLIENT NAME"] and not df_onhold.empty:
                st.divider()
                st.subheader("🟡 On Hold SCRIPTS", anchor=False)
                self._render_onhold_table(df_onhold)

    def _render_onhold_mode(self):
        with st.spinner("Loading on hold. Please wait...", show_time=True):
            df_onhold = get_merged_onhold()
            if df_onhold.empty:
                st.warning("No on-hold data available.")
                return
            df_rm_map = get_client_rm_map()
            df_onhold = df_onhold.merge(df_rm_map, on="CLIENT CODE", how="left")
            df_onhold['BRO'] = df_onhold['BRO'].fillna("N/A")
        col1, col2 = st.columns(2)
        with col1:
            filter_by = st.selectbox(
                "Filter by",
                options=["ALL", "CLIENT CODE", "CLIENT NAME", "SCRIPT"]
            )
        if filter_by != "ALL":
            unique_values = sorted(df_onhold[filter_by].unique())
            with col2:
                selected_value = st.selectbox(f"Select {filter_by}", options=unique_values)
            df_onhold = df_onhold[df_onhold[filter_by] == selected_value].reset_index(drop=True)
        df_onhold = df_onhold.sort_values(
            by=["SETTLEMENT DATE", "TOTAL VALUATION"],
            ascending=[False, False]
        ).reset_index(drop=True)
        col_order = [
            'BRO', 'CLIENT CODE', 'CLIENT NAME', 'BRANCH', 'SCRIPT', 'QUANTITY',
            'CLOSE PRICE', 'TOTAL VALUATION', 'TRANSACTION TYPE', 'STATUS', 'SETTLEMENT DATE'
        ]
        df_onhold = df_onhold[col_order]
        self._render_onhold_metrics(df_onhold)
        format_cols = ['QUANTITY', 'CLOSE PRICE', 'TOTAL VALUATION']
        present_fmt = [c for c in format_cols if c in df_onhold.columns]
        if present_fmt:
            df_onhold[present_fmt] = df_onhold[present_fmt].applymap(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
        st.dataframe(df_onhold, width='stretch')

    def render_page(self):
        self.total_valuation_all = None
        self.total_scripts_all = None
        mode = st.radio("Select Mode", ["Latest Holdings (UAT)", "On Hold"], horizontal=True)
        if mode == "Latest Holdings (UAT)":
            self._render_latest_holdings()
        elif mode == "On Hold":
            self._render_onhold_mode()


if __name__ == "__main__":
    DPM3().render_page()
