from streamlit_searchbox import st_searchbox
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from time import sleep
from sqlalchemy import create_engine
from datetime import datetime
from utils.helper import get_holding_engine
from db import db
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from nepali_datetime import date as nepali_date
from utils.custom_hotkey import activate_client_code_hotkey
from utils import auth_utils, helper
from pages.BasePage import BasePage

pd.set_option("styler.render.max_elements", 1579383)



@st.cache_data(ttl=3600)
def get_latest_closing_price():
    row = db.get_table_average_price()
    df = pd.DataFrame(row, columns=['Symbol', 'Ltp'])
    return df

@st.cache_data(ttl=3600)
def get_today_due_list():
    # IMPORTANT: use date(), not strftime()
    target_date = datetime.now().date()
    return db.get_due_list_for_dpm3(target_date)

class DPM3(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin("-12rem")
        st.session_state.active_menu = "business"
        st.set_page_config("DPM3", page_icon="📦", layout='wide')

        # Dates
        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()
        activate_client_code_hotkey()

        # user = auth_utils.ensure_logged_in()
        # self.username= user['username']
        # self.role= user['role']
        # self.branch = user['branch']
        navigation.render_sidebar()

        # DB Connection
        self.holding_engine = get_holding_engine()
        st.header("📦 DPM3", anchor=False)

    def get_week_start(self,dt: date) -> date:
        # Sunday = 6 if Monday=0
        return dt - timedelta(days=(dt.weekday() + 1) % 7)


    def get_week_floorsheet(self):
        query = """
            SELECT
                clientcode,
                symbol,
                transaction_type,
                quantity
            FROM floorsheet
            WHERE uploaded_at::date >= %s
            AND uploaded_at::date <= CURRENT_DATE
        """
        week_start = self.get_week_start(date.today())
        return pd.read_sql(query, self.holding_engine, params=(week_start,))


    def dump_data_to_db(self, df):
        group_keys = ["BRO","CLIENT CODE","CLIENT NAME","BRANCH","BOID"]
        existing_keys = [col for col in group_keys if col in df.columns]
        other_cols = [col for col in df.columns if col not in existing_keys]
        df = df[existing_keys + other_cols]

        engine = create_engine(get_holding_engine())
        df.to_sql(
            name="dpm3",
            con=engine,
            if_exists="replace",
            index=False
        )

    def extract_data_from_raw_txt_file(self, file_obj):
        columns_to_extract = {
            0: "BOID",
            1: "ISIN",
            2: "FREE BALANCE",
            4: "PLEDGE BALANCE",
            10: "CURRENT BALANCE"
        }
        numeric_columns = ["FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE"]

        # Read all lines first
        lines = file_obj.readlines()

        # ✅ Skip last line if it does NOT contain "~"
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

        # Default extra columns
        df["SCRIPT"] = "NAN"
        df["CLOSING PRICE"] = 0.0
        df["FREE SHARE VALUATION"] = 0.0
        df["PLEDGE SHARE VALUATION"] = 0.0
        df["TOTAL VALUATION"] = 0.0

        return df

    def enrich_with_isin(self, df):
        isin_rows = db.get_isin_data()
        isin_df = pd.DataFrame(isin_rows, columns=["ISIN", "SCRIP"])
        merged = df.merge(isin_df, on="ISIN", how="left")
        merged["SCRIPT"] = merged["SCRIP"].fillna("N/F")
        merged = merged.drop(columns=["SCRIP"])
        return merged

    def enrich_with_client_code_and_branch(self, df):
        rows = db.get_kyc()
        kyc_df = pd.DataFrame(rows, columns=["CLIENT CODE","CLIENT NAME", "BRANCH", "BOID"])
        # kyc_df["BOID"] = kyc_df["BOID"].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "")
        def safe_boid(x):
            try:
                if pd.notnull(x):
                    return str(int(float(x)))
                else:
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
        df_avp = pd.DataFrame(rows, columns=["SYMBOL", "closePrice"]).rename(columns={"SYMBOL":"SCRIPT"})
        merged = df.merge(df_avp, on="SCRIPT", how="left")
        merged["CLOSING PRICE"] = merged["closePrice"].astype(float).fillna(0.0)
        merged.drop(columns=["closePrice"], inplace=True)
        merged["FREE SHARE VALUATION"] = merged["FREE BALANCE"] * merged["CLOSING PRICE"]
        merged["PLEDGE SHARE VALUATION"] = merged["PLEDGE BALANCE"] * merged["CLOSING PRICE"]
        merged["TOTAL VALUATION"] = merged["FREE SHARE VALUATION"] + merged["PLEDGE SHARE VALUATION"]
        return merged

    def enrich_with_bro(self, df):
        rows = db.get_table_rm_child_map()
        bro_df = pd.DataFrame(rows, columns=["BRO", "CLIENT NAME"])
        merged = df.merge(bro_df, on="CLIENT NAME", how="left")
        merged["BRO"] = merged["BRO"].fillna("N/A")
        return merged

    @st.cache_data(ttl=1600)
    def get_dpm3_data(_self):
        if 'dpm3' not in st.session_state:
            st.session_state['dpm3'] = db.get_dpm3()
        df =  st.session_state['dpm3']
        # print(df)
        group_keys = ["BRO","CLIENT CODE","CLIENT NAME","BRANCH","BOID"]
        
        sum_cols = ["FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE",
                    "FREE SHARE VALUATION",
                    "PLEDGE SHARE VALUATION", "TOTAL VALUATION"]
        
        df_grouped = df.groupby(group_keys, as_index=False)[sum_cols].sum()
        df_grouped["SCRIPT COUNT"] = df.groupby(group_keys)["SCRIPT"].count().values
        column_order = group_keys + ["SCRIPT COUNT"] + sum_cols
        df_grouped = df_grouped[column_order]
        return df_grouped, df


    @st.dialog("📑 Client Scripts Detail", width="large")
    def show_client_dialog(self,df:pd.DataFrame, label):
        st.subheader(label)
        st.badge(f"Script Count: " + str(len(df)), color="green")
        # st.dataframe(df, width='stretch')
        numeric_cols = df.select_dtypes(include="number").columns

        styled_df = df.style.format(
            {col: "{:,.0f}" for col in numeric_cols}
        )

        st.dataframe(
            styled_df,
            use_container_width=True
        )

    def show_import_file(self):
        uploaded_file = st.file_uploader("Import DPM3 file", type=".txt")
        if uploaded_file is None:
            return

        with st.status("📤 Uploading DPM3 file...", expanded=True) as status:
            steps = [
                ("Cleaning DPM3 file", self.extract_data_from_raw_txt_file, [uploaded_file]),
                ("Matching ISIN number", self.enrich_with_isin, []),
                ("Extracting client code & branch info", self.enrich_with_client_code_and_branch, []),
                ("Extracting close price", self.enrich_with_close_price, []),
                ("Extracting BROs", self.enrich_with_bro, []),
                ("Dumping data to db", self.dump_data_to_db, [])
            ]

            df = None
            for i, (label, func, args) in enumerate(steps, 1):
                status.update(label=f"Step {i}/{len(steps)}: {label}", state="running")
                sleep(0.3)  # optional to show effect
                if df is None:
                    df = func(*args)
                else:
                    df = func(df, *args)
            status.update(label="✅ Upload Completed", state="complete", expanded=False)

    def view_holdings(self):

        # ---------------------------
        # 1. Load DPM3 (RAW)
        # ---------------------------
        _, df_dpm3 = self.get_dpm3_data()

        # st.dataframe(_)

        df_dpm3 = df_dpm3.rename(columns={
            "CLIENT CODE": "clientcode",
            "CLIENT NAME": "clientname",
            "SCRIPT": "symbol",
            "CURRENT BALANCE": "quantity"
        })

        # ---------------------------
        # 2. Load Today's Floorsheet
        # ---------------------------
        df_fs = self.get_week_floorsheet()

        # ---------------------------
        # 3. Apply Floorsheet Delta
        # ---------------------------
        # ---------------------------
        # 3. Apply Floorsheet Delta
        # ---------------------------

        if df_fs.empty:
            st.info("ℹ️ No floorsheet uploaded today. Showing DPM3 holdings only.")
            df_live_stock = df_dpm3.copy()
            df_live_stock["final_quantity"] = df_live_stock["quantity"]

        else:
            df_fs["signed_qty"] = df_fs["quantity"].where(
                df_fs["transaction_type"].str.upper() == "BUY",
                -df_fs["quantity"]
            )

            df_fs_delta = (
                df_fs
                .groupby(["clientcode", "symbol"], as_index=False)["signed_qty"]
                .sum()
            )

            df_holdings = pd.merge(
                df_dpm3,
                df_fs_delta,
                how="outer",
                on=["clientcode", "symbol"]
            )

            df_holdings["quantity"] = df_holdings["quantity"].fillna(0)
            df_holdings["signed_qty"] = df_holdings["signed_qty"].fillna(0)

            df_holdings["final_quantity"] = (
                df_holdings["quantity"] + df_holdings["signed_qty"]
            )

            # ⚠️ Soft validation (DO NOT STOP)
            violations = df_holdings[df_holdings["final_quantity"] < 0]
            col1, col2 = st.columns([1.2,1])
            if not violations.empty:
                with col1:
                    st.warning("⚠️ Some sell transactions exceed Sunday holdings (intraday / unsettled trades).")
                violations.reset_index(inplace=True, drop=True)
                violations.index = violations.index + 1
                st.badge(f"Total unusal DP Holdings : " + str(len(violations)), color='red')
                st.dataframe(
                    violations[["clientcode", "symbol", "quantity", "signed_qty", "final_quantity"]],
                    width='stretch'
                )

            # Clip negatives for UI
            df_holdings["final_quantity"] = df_holdings["final_quantity"].clip(lower=0)

            # ✅ ALWAYS assign
            df_live_stock = df_holdings.copy()



        # ---------------------------
        # 4. Recalculate Balances & Valuation
        # ---------------------------
        df_live_stock = df_live_stock[df_live_stock["final_quantity"] > 0]

        df_live_stock["CURRENT BALANCE"] = df_live_stock["final_quantity"]
        df_live_stock["FREE BALANCE"] = df_live_stock["CURRENT BALANCE"]
        df_live_stock["PLEDGE BALANCE"] = 0

        df_live_stock["FREE SHARE VALUATION"] = (
            df_live_stock["FREE BALANCE"] * df_live_stock["CLOSING PRICE"]
        )

        df_live_stock["PLEDGE SHARE VALUATION"] = (
            df_live_stock["PLEDGE BALANCE"] * df_live_stock["CLOSING PRICE"]
        )

        df_live_stock["TOTAL VALUATION"] = (
            df_live_stock["FREE SHARE VALUATION"] +
            df_live_stock["PLEDGE SHARE VALUATION"]
        )

        # ---------------------------
        # 5. Client-Level Summary
        # ---------------------------
        group_keys = ["BRO", "clientcode", "clientname", "BRANCH", "BOID"]

        sum_cols = [
            "FREE BALANCE",
            "PLEDGE BALANCE",
            "CURRENT BALANCE",
            "FREE SHARE VALUATION",
            "PLEDGE SHARE VALUATION",
            "TOTAL VALUATION"
        ]

        df_client_summary = (
            df_live_stock
            .groupby(group_keys, as_index=False)[sum_cols]
            .sum()
        )

        df_client_summary["SCRIPT COUNT"] = (
            df_live_stock
            .groupby(group_keys)["symbol"]
            .count()
            .values
        )

        column_order = (
            group_keys +
            ["SCRIPT COUNT"] +
            sum_cols
        )

        df_client_summary = df_client_summary[column_order]

        # ---------------------------
        # 6. UI – Client Table
        # ---------------------------
        st.badge(f"Total Clients: {len(df_client_summary):,}", color="green")

        numeric_cols = df_client_summary.select_dtypes(include="number").columns

        styled_df = df_client_summary.style.format(
            {col: "{:,.2f}" for col in numeric_cols}
        )

        # st.dataframe(
        #     styled_df,
        #     use_container_width=True
        # )

        selection = st.dataframe(
            styled_df,
            selection_mode="single-row",
            key="client_table",
            on_select="rerun"
        )

        # ---------------------------
        # 7. Drill-down Dialog
        # ---------------------------
        if selection.selection.rows:
            idx = selection.selection.rows[0]
            selected = df_client_summary.iloc[idx]

            client_code = selected["clientcode"]
            client_name = selected["clientname"]

            client_scripts = (
                df_live_stock[df_live_stock["clientcode"] == client_code]
                .copy()
            )

            client_scripts.reset_index(drop=True, inplace=True)
            client_scripts.index += 1

            view_cols = [
                "symbol",
                "FREE BALANCE",
                "PLEDGE BALANCE",
                "CURRENT BALANCE",
                "CLOSING PRICE",
                "FREE SHARE VALUATION",
                "PLEDGE SHARE VALUATION",
                "TOTAL VALUATION"
            ]

            self.show_client_dialog(
                client_scripts[view_cols],
                f"👨🏻‍💻 {client_name} - {client_code}"
            )



    @st.cache_data(ttl=3600)
    def get_and_format_holdings(_self):
        raw_data = db.get_floorsheet_data()
        df = _self.calculate_holdings(raw_data)
        for col in ['rate', 'amount']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else x)
        return df

    
    def floorsheet_ui(self):
        st.subheader("Data from floorsheet", anchor=False)
        
        loading_placeholder = st.empty()
        with loading_placeholder.status("Fetching client holding data...", expanded=False) as status:
            new_df = self.get_and_format_holdings()
            status.update(label="Data fetched successfully.", state="complete", expanded=False)
            sleep(0.5)
        loading_placeholder.empty()

        with st.spinner("Loading data...", show_time=True):
            new_df = self.get_and_format_holdings()   # fast after first run due to cache

            filter_options = ['None', 'Client Code', 'Client Name', 'Symbol']

            col1, col2 = st.columns(2)
            with col1:
                selected_filter = st.selectbox("Filter by", filter_options, key="fs_filter")

            filtered_df = new_df.copy()

            with col2:
                if selected_filter == "Client Code":
                    search = st.text_input("Search by Client Code", "", key="fs_cc").strip().upper()
                    if search:
                        filtered_df = filtered_df[filtered_df['clientcode'].str.upper().str.contains(search, na=False)]

                elif selected_filter == "Client Name":
                    search = st.text_input("Search by Client Name", "", key="fs_cn").strip().upper()
                    if search:
                        filtered_df = filtered_df[filtered_df['clientname'].str.upper().str.contains(search, na=False)]

                elif selected_filter == "Symbol":
                    search = st.text_input("Search by Symbol", "", key="fs_sym").strip().upper()
                    if search:
                        filtered_df = filtered_df[filtered_df['symbol'].str.upper().str.contains(search, na=False)]


            st.badge(f"Total data: {len(filtered_df):,}")

            filtered_df = filtered_df.rename(columns={
                'clientcode': 'Client Code',
                'clientname': 'Client Name',
                'branch': 'Branch',
                'symbol': 'Symbol',
                'quantity': 'Quantity',
                'rate': 'Rate',
                'amount': 'Amount'
            })

            filtered_df = filtered_df.sort_values(by='Client Name').reset_index(drop=True)
            filtered_df.index = filtered_df.index + 1

            st.data_editor(data=filtered_df, disabled=True)




        # df_grouped,df_uploaded  = self.get_dpm3_data()
        # st.badge(f"Total rows: {len(df_grouped):,}", color="green")
        # selection = st.dataframe(
        #     df_grouped,
        #     # column_order=df_grouped.columns.tolist(),
        #     key="client_table",
        #     selection_mode="single-row",
        #     on_select="rerun"
        # )

        # if selection.selection.rows:
        #     row_idx = selection.selection.rows[0]
        #     selected_row = df_grouped.iloc[row_idx]

        #     selected_code = selected_row["CLIENT CODE"]
        #     client_label = selected_row["CLIENT NAME"]

        #     client_scripts:pd.DataFrame = df_uploaded[df_uploaded["CLIENT CODE"] == selected_code].copy()
        #     client_scripts.reset_index(drop=True, inplace=True)
        #     client_scripts.index += 1

        #     # Choose only the visible columns
        #     view_cols = [
        #         "SCRIPT","FREE BALANCE","PLEDGE BALANCE","CURRENT BALANCE",
        #         "CLOSING PRICE","FREE SHARE VALUATION",
        #         "PLEDGE SHARE VALUATION","TOTAL VALUATION"
        #     ]

        #     # Open the dialog
        #     self.show_client_dialog(client_scripts[view_cols], f"👨🏻‍💻 {client_label} - {selected_code}")
    


#     def view_holdings(self):

#         # ---------------------------
#         # 1. Load DPM3 (RAW)
#         # ---------------------------
#         _, df_dpm3 = self.get_dpm3_data()

#         # st.dataframe(_)

#         df_dpm3 = df_dpm3.rename(columns={
#             "CLIENT CODE": "clientcode",
#             "CLIENT NAME": "clientname",
#             "SCRIPT": "symbol",
#             "CURRENT BALANCE": "quantity"
#         })

#         # ---------------------------
#         # 2. Load Today's Floorsheet
#         # ---------------------------
#         df_fs = self.get_week_floorsheet()

#         if df_fs.empty:
#             st.info("ℹ️ No floorsheet uploaded today. Showing DPM3 holdings only.")
#             df_live_stock = df_dpm3.copy()
#             df_live_stock["final_quantity"] = df_live_stock["quantity"]

#         else:
#             df_fs["signed_qty"] = df_fs["quantity"].where(
#                 df_fs["transaction_type"].str.upper() == "BUY",
#                 -df_fs["quantity"]
#             )

#             df_fs_delta = (
#                 df_fs
#                 .groupby(["clientcode", "symbol"], as_index=False)["signed_qty"]
#                 .sum()
#             )

#             df_holdings = pd.merge(
#                 df_dpm3,
#                 df_fs_delta,
#                 how="outer",
#                 on=["clientcode", "symbol"]
#             )

#             df_holdings["quantity"] = df_holdings["quantity"].fillna(0)
#             df_holdings["signed_qty"] = df_holdings["signed_qty"].fillna(0)

#             df_holdings["final_quantity"] = (
#                 df_holdings["quantity"] + df_holdings["signed_qty"]
#             )

#             # ⚠️ Soft validation (DO NOT STOP)
#             violations = df_holdings[df_holdings["final_quantity"] < 0]
#             col1, col2 = st.columns([1.2,1])
#             if not violations.empty:
#                 with col1:
#                     st.warning("⚠️ Some sell transactions exceed Sunday holdings (intraday / unsettled trades).")
#                 violations.reset_index(inplace=True, drop=True)
#                 violations.index = violations.index + 1
#                 st.badge(f"Total unusal DP Holdings : " + str(len(violations)), color='red')
#                 st.dataframe(
#                     violations[["clientcode", "symbol", "quantity", "signed_qty", "final_quantity"]],
#                     width='stretch'
#                 )

#             # Clip negatives for UI
#             df_holdings["final_quantity"] = df_holdings["final_quantity"].clip(lower=0)

#             # ✅ ALWAYS assign
#             df_live_stock = df_holdings.copy()



#         # ---------------------------
#         # 4. Recalculate Balances & Valuation
#         # ---------------------------
#         df_live_stock = df_live_stock[df_live_stock["final_quantity"] > 0]

#         df_live_stock["CURRENT BALANCE"] = df_live_stock["final_quantity"]
#         df_live_stock["FREE BALANCE"] = df_live_stock["CURRENT BALANCE"]
#         df_live_stock["PLEDGE BALANCE"] = 0

#         df_live_stock["FREE SHARE VALUATION"] = (
#             df_live_stock["FREE BALANCE"] * df_live_stock["CLOSING PRICE"]
#         )

#         df_live_stock["PLEDGE SHARE VALUATION"] = (
#             df_live_stock["PLEDGE BALANCE"] * df_live_stock["CLOSING PRICE"]
#         )

#         df_live_stock["TOTAL VALUATION"] = (
#             df_live_stock["FREE SHARE VALUATION"] +
#             df_live_stock["PLEDGE SHARE VALUATION"]
#         )

#         # ---------------------------
#         # 5. Client-Level Summary
#         # ---------------------------
#         group_keys = ["BRO", "clientcode", "clientname", "BRANCH", "BOID"]

#         sum_cols = [
#             "FREE BALANCE",
#             "PLEDGE BALANCE",
#             "CURRENT BALANCE",
#             "FREE SHARE VALUATION",
#             "PLEDGE SHARE VALUATION",
#             "TOTAL VALUATION"
#         ]

#         df_client_summary = (
#             df_live_stock
#             .groupby(group_keys, as_index=False)[sum_cols]
#             .sum()
#         )

#         df_client_summary["SCRIPT COUNT"] = (
#             df_live_stock
#             .groupby(group_keys)["symbol"]
#             .count()
#             .values
#         )

#         column_order = (
#             group_keys +
#             ["SCRIPT COUNT"] +
#             sum_cols
#         )

#         df_client_summary = df_client_summary[column_order]


#         search_box = st.text_input(
#     "Search by Script",
#     placeholder="e.g. NABIL, NTC, API"
# ).strip().upper()

#         # ---------------------------
#         # 6. UI – Client Table
#         # ---------------------------
#         st.badge(f"Total Clients: {len(df_client_summary):,}", color="green")

#         numeric_cols = df_client_summary.select_dtypes(include="number").columns

#         styled_df = df_client_summary.style.format(
#             {col: "{:,.2f}" for col in numeric_cols}
#         )

       
#         selection = st.dataframe(
#             styled_df,
#             selection_mode="single-row",
#             key="client_table",
#             on_select="rerun"
#         )

#         # ---------------------------
#         # 7. Drill-down Dialog
#         # ---------------------------
#         if selection.selection.rows:
#             idx = selection.selection.rows[0]
#             selected = df_client_summary.iloc[idx]

#             client_code = selected["clientcode"]
#             client_name = selected["clientname"]

#             client_scripts = (
#                 df_live_stock[df_live_stock["clientcode"] == client_code]
#                 .copy()
#             )

#             client_scripts.reset_index(drop=True, inplace=True)
#             client_scripts.index += 1

#             view_cols = [
#                 "symbol",
#                 "FREE BALANCE",
#                 "PLEDGE BALANCE",
#                 "CURRENT BALANCE",
#                 "CLOSING PRICE",
#                 "FREE SHARE VALUATION",
#                 "PLEDGE SHARE VALUATION",
#                 "TOTAL VALUATION"
#             ]

#             self.show_client_dialog(
#                 client_scripts[view_cols],
#                 f"👨🏻‍💻 {client_name} - {client_code}"
#             )


    

    def render_page(self):
        if self.role in ["USER", "VIEWER"]:
            selected_radio_bt = st.radio("Select option", [ 'View Holdings'], horizontal=True)
        else:
            selected_radio_bt = st.radio("Select option", ['Import DPM3', 'Latest Holdings', 'Weekly DPM3 only', 
                                                           'Test', 'Holding Summary of Due Clients'], index=1, horizontal=True)
        
        if selected_radio_bt == "Import DPM3":
            if not db.is_sunday_file_uploaded():
                self.show_import_file()
            else:
                st.info(f"‎ ‎ ‎ DPM3 file has been uploaded on : " + str(db.get_last_sunday()), icon="📢")
        
        elif selected_radio_bt == "Weekly DPM3 only":
            df_grouped,df_uploaded  = self.get_dpm3_data()
            st.badge(f"Total rows: {len(df_grouped):,}", color="green")
            selection = st.dataframe(
                df_grouped,
                # column_order=df_grouped.columns.tolist(),
                key="client_table",
                selection_mode="single-row",
                on_select="rerun"
            )

            if selection.selection.rows:
                row_idx = selection.selection.rows[0]
                selected_row = df_grouped.iloc[row_idx]

                selected_code = selected_row["CLIENT CODE"]
                client_label = selected_row["CLIENT NAME"]

                client_scripts:pd.DataFrame = df_uploaded[df_uploaded["CLIENT CODE"] == selected_code].copy()
                client_scripts.reset_index(drop=True, inplace=True)
                client_scripts.index += 1

                # Choose only the visible columns
                view_cols = [
                    "SCRIPT","FREE BALANCE","PLEDGE BALANCE","CURRENT BALANCE",
                    "CLOSING PRICE","FREE SHARE VALUATION",
                    "PLEDGE SHARE VALUATION","TOTAL VALUATION"
                ]

                # Open the dialog
                self.show_client_dialog(client_scripts[view_cols], f"👨🏻‍💻 {client_label} - {selected_code}")
        
        elif selected_radio_bt == 'Latest Holdings':
            self.view_holdings()
        elif selected_radio_bt == "Test":
            self.floorsheet_ui()
        elif selected_radio_bt == "Holding Summary of Due Clients":
            self.holding_summary()

    def holding_summary(self):
        status , due_list_df = get_today_due_list()
        today_date = datetime.now().strftime("%Y-%m-%d")
        weekday_name = datetime.now().strftime("%A")

        if 'AM' in status:
            st.subheader(f"Holdings Summary of Due Clients: {today_date} ({weekday_name}) - Morning Session", anchor=False)
        else:
            st.subheader(f"Holdings Summary of Due Clients: {today_date} ({weekday_name}) - Evening Session", anchor=False)

        loading_placeholder = st.empty()
        with loading_placeholder.status("Fetching due clients holding data. Please wait !", expanded=False) as status:
            if 'floorsheet_data' not in st.session_state:
                st.session_state.floorsheet_data = db.get_floorsheet_data()
            new_df = self.calculate_holdings(st.session_state.floorsheet_data)
            status.update(label="Data fetched successfully.", state="complete", expanded=False)
            sleep(0.5)

        loading_placeholder.empty()
        with st.spinner("Loading data. Please wait...", show_time=True):
            filter_options = ['None', 'Client Code', 'Client Name', 'Symbol']

            col1, col2 = st.columns(2)
            with col1:
                selected_filter = st.selectbox("Filter by", filter_options)

            with col2:
                search_value = ""
                if selected_filter == "Client Code":
                    search_value = st.text_input("Search by Client Code", "").strip().upper()
                    if search_value:
                        filtered_df = new_df[new_df['clientcode'].str.upper().str.contains(search_value)]
                    else:
                        filtered_df = new_df

                elif selected_filter == "Client Name":
                    search_value = st.text_input("Search by Client Name", "").strip().upper()
                    if search_value:
                        filtered_df = new_df[new_df['clientname'].str.upper().str.contains(search_value)]
                    else:
                        filtered_df = new_df

                elif selected_filter == "Symbol":
                    search_value = st.text_input("Search by Symbol", "").strip().upper()
                    if search_value:
                        filtered_df = new_df[new_df['symbol'].str.upper().str.contains(search_value)]
                    else:
                        filtered_df = new_df

                else:
                    filtered_df = new_df

            # Merge with latest closing price
            df = get_latest_closing_price()
            merge_df = filtered_df.merge(df, left_on="symbol", right_on="Symbol", how="left")
            merge_df.drop(columns=['Symbol'], inplace=True)

            # Merge with due list
            merge_df_with_due = merge_df.merge(
                due_list_df[['clientCode', 'adjustedBalance']],
                left_on="clientcode",
                right_on="clientCode",
                how="left"
            )

            # Compute amount
            merge_df_with_due['amount'] = merge_df_with_due['Ltp'] * merge_df_with_due['quantity']

            # Aggregate summary (keep clientcode!)
            summary_df = (
                merge_df_with_due
                .groupby(['clientcode', 'clientname', 'branch'], as_index=False)
                .agg({
                    'amount': 'sum',
                    'adjustedBalance': 'first'
                })
            )

            # Keep only rows where adjustedBalance is not null/empty
            summary_df = summary_df[
                summary_df['adjustedBalance'].notna() & (summary_df['adjustedBalance'] != '')
            ].copy()

            # Restrict to required columns
            summary_df = summary_df[['clientcode', 'clientname', 'branch', 'amount', 'adjustedBalance']].copy()

            # Restrict to required columns
            summary_df = summary_df[['clientcode', 'clientname', 'branch', 'amount', 'adjustedBalance']]
            summary_df.sort_values(by="adjustedBalance", inplace=True)
            summary_df.reset_index(drop=True, inplace=True)
            summary_df.index = summary_df.index + 1

            # Ensure numeric
            summary_df['amount'] = pd.to_numeric(summary_df['amount'], errors='coerce')
            summary_df['adjustedBalance'] = pd.to_numeric(summary_df['adjustedBalance'], errors='coerce')

            # Rename for display
            summary_df.rename(columns={
                'clientcode': 'Client Code',
                'clientname': 'Client Name',
                'branch': 'Branch',
                'amount':'Amount',
                'adjustedBalance':'Adjusted Due Balance'
            }, inplace=True)

            # Formatter: positives normal, negatives in brackets
            def accounting_format(val):
                if pd.isnull(val):
                    return ""
                if val < 0:
                    return f"({abs(val):,.2f})"   # brackets for negatives
                return f"{val:,.2f}"              # normal for positives

            # Apply formatting
            styled_summary = summary_df.style.format({
                'Adjusted Due Balance': accounting_format,
                'Amount': accounting_format
            })

            # Apply red color for negatives
            def red_if_negative(val):
                try:
                    num = float(str(val).replace(",","").replace("(","").replace(")",""))
                    if num < 0:
                        return "color: red;"
                except:
                    return ""
                return ""

            styled_summary = styled_summary.map(red_if_negative, subset=['Adjusted Due Balance','Amount'])

            # Show in Streamlit
            st.badge(f"Total data: {len(summary_df):,.0f}")
            st.data_editor(styled_summary, disabled=True)
            if st.toggle("Show Reference"):
                merge_df_with_due.drop(columns="clientCode", inplace=True)
                merge_df_with_due.rename(columns={
                    'clientcode':'Client Code',
                    'clientname':'Client Name',
                    'branch':'Branch',
                    'symbol':'Symbol',
                    'quantity':'Quantity',
                    'rate':'Purchase Rate',
                    'amount':'Amount',
                    'adjustedBalance':'Adjusted Balance'
                }, inplace=True)

                column_order = [
                    'Client Code', 'Client Name', 'Branch',
                    'Symbol', 'Quantity', 'Purchase Rate',
                    'Ltp', 'Amount', 'Adjusted Balance'
                ]
                merge_df_with_due = merge_df_with_due[column_order]

                merge_df_with_due.reset_index(drop=True, inplace=True)
                merge_df_with_due.index = merge_df_with_due.index + 1

                # Ensure numeric for Amount and Adjusted Balance only
                merge_df_with_due['Amount'] = pd.to_numeric(merge_df_with_due['Amount'], errors='coerce')
                merge_df_with_due['Adjusted Balance'] = pd.to_numeric(merge_df_with_due['Adjusted Balance'], errors='coerce')

                # Formatter: positives normal, negatives in brackets
                def accounting_format(val):
                    if pd.isnull(val):
                        return ""
                    if val < 0:
                        return f"({abs(val):,.2f})"   # brackets for negatives
                    return f"{val:,.2f}"              # normal for positives

                # Format only Amount and Adjusted Balance
                styled_df = merge_df_with_due.style.format({
                    'Amount': accounting_format,
                    'Adjusted Balance': accounting_format,
                    'Quantity': '{:,.0f}'.format,          # integer, no decimals
                    'Purchase Rate': '{:,.2f}'.format,     # 2 decimals
                    'Ltp': '{:,.2f}'.format                # 2 decimals
                })

                # Apply red color for negatives in Amount and Adjusted Balance
                def red_if_negative(val):
                    try:
                        num = float(str(val).replace(",","").replace("(","").replace(")",""))
                        if num < 0:
                            return "color: red;"
                    except:
                        return ""
                    return ""

                styled_df = styled_df.map(red_if_negative, subset=['Amount','Adjusted Balance'])

                st.data_editor(styled_df, disabled=True)

    def calculate_holdings(self, df):
        # Ensure transaction_type is consistent
        df['transaction_type'] = df['transaction_type'].str.strip().str.title()

        # Separate Buys and Sells
        df_buy = df[df['transaction_type'] == 'Buy'].copy()
        df_sell = df[df['transaction_type'] == 'Sell'].copy()

        # Aggregate buys per client, symbol, branch
        buy_agg = df_buy.sort_values('tradetime').groupby(
            ['clientcode', 'clientname', 'branch', 'symbol'], as_index=False
        ).agg({
            'quantity': 'sum',
            'rate': 'last',
            'amount': 'last'
        })

        # Aggregate sells per client, symbol, branch
        sell_agg = df_sell.groupby(
            ['clientcode', 'clientname', 'branch', 'symbol'], as_index=False
        ).agg({
            'quantity': 'sum'
        })
        sell_agg.rename(columns={'quantity': 'sell_quantity'}, inplace=True)

        # Merge buys and sells
        holdings = pd.merge(
            buy_agg,
            sell_agg,
            on=['clientcode', 'clientname', 'branch', 'symbol'],
            how='left'
        )
        holdings['sell_quantity'] = holdings['sell_quantity'].fillna(0)

        # Calculate net quantity
        holdings['quantity'] = holdings['quantity'] - holdings['sell_quantity']

        # Remove rows where net quantity <= 0
        holdings = holdings[holdings['quantity'] > 0].copy()

        # Drop temporary column
        holdings.drop(columns=['sell_quantity'], inplace=True)
        holdings['amount'] = holdings['quantity'] * holdings['rate']
        return holdings.sort_values(['symbol', 'quantity'], ascending=[True, False])
        # return holdings.sort_values(['clientcode', 'symbol', 'branch'])

    def floorsheet_ui(self):
        st.subheader("Data from floorsheet", anchor=False)
        loading_placeholder = st.empty()
        with loading_placeholder.status("Fetching client holding data. Please wait !", expanded=False) as status:
            if 'floorsheet_data' not in st.session_state:
                st.session_state.floorsheet_data = db.get_floorsheet_data()
            new_df = self.calculate_holdings(st.session_state.floorsheet_data)
            status.update(label="Data fetched successfully.", state="complete", expanded=False)
            sleep(0.5)
        loading_placeholder.empty()
        with st.spinner("Loading data. Please wait...", show_time=True):
            filter_options = ['None', 'Client Code', 'Client Name', 'Symbol']

            col1, col2 = st.columns(2)
            with col1:
                selected_filter = st.selectbox("Filter by", filter_options)

            with col2:
                # dynamic search input based on filter choice
                search_value = ""
                if selected_filter == "Client Code":
                    search_value = st.text_input("Search by Client Code", "").strip().upper()
                    if search_value:
                        filtered_df = new_df[new_df['clientcode'].str.upper().str.contains(search_value)]
                    else:
                        filtered_df = new_df

                elif selected_filter == "Client Name":
                    search_value = st.text_input("Search by Client Name", "").strip().upper()
                    if search_value:
                        filtered_df = new_df[new_df['clientname'].str.upper().str.contains(search_value)]
                    else:
                        filtered_df = new_df

                elif selected_filter == "Symbol":
                    search_value = st.text_input("Search by Symbol", "").strip().upper()
                    if search_value:
                        filtered_df = new_df[new_df['symbol'].str.upper().str.contains(search_value)]
                    else:
                        filtered_df = new_df

                else:
                    filtered_df = new_df



            st.badge(f"Total data: {len(filtered_df):,.2f}")
            # format numeric columns with commas
            for col in ['rate', 'amount']:
                if col in filtered_df.columns:
                    filtered_df[col] = filtered_df[col].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else x)

            filtered_df.rename(columns={'clientcode':'Client Code', 'clientname':'Client Name', 'branch':'Branch', 'symbol':'Symbol', 'quantity':'Quantity',
                                        'rate':'Rate', 'amount':'Amount'}, inplace=True)
            filtered_df.sort_values(by='Client Name', inplace=True)
            
            
            filtered_df.reset_index(inplace=True, drop=True)
            filtered_df.index = filtered_df.index + 1
            st.data_editor(data=filtered_df, disabled=True)







if __name__ == "__main__":
    DPM3().render_page()
