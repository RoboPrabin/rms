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
def get_today_due_list():
    # IMPORTANT: use date(), not strftime()
    target_date = datetime.now().date()
    return db.get_due_list_for_dpm3(target_date)


@st.cache_data(ttl=3600)
def get_client_rm_map():
    rows = db.get_table_rm_child_map()
    df = pd.DataFrame(rows, columns=["BRO", "CLIENT CODE"])
    return df

class DPM3(BasePage):
    def __init__(self):
        super().__init__()
        helper.eliminate_top_margin("-10rem")
        st.session_state.active_menu = "business"
        st.set_page_config("DPM3", page_icon="📦", layout='wide')
        # Dates
        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()
        activate_client_code_hotkey()
        navigation.render_sidebar()
        st.header("📦 DPM3", anchor=False)



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
        df["STATUS"] = "SUNDAY DATA"
        return df

    def append_thursday_buy_data(self, df: pd.DataFrame, selected_date: date) -> pd.DataFrame:
        rows = db.get_floorsheet_from_date(selected_date)
        print(f"Total Thursday buy rows: {len(rows)}")
        buy_df = pd.DataFrame(
            rows,
            columns=[
                "CLIENT CODE",
                "CLIENT NAME",
                "SCRIPT",
                "QUANTITY",
                "RATE",
                "AMOUNT",
                "TRANSACTION TYPE",
                "BRANCH",
                "TRADE DATE",
            ],
        )

        if buy_df.empty:
            return df

        buy_df["BRANCH"] = buy_df["BRANCH"].map(helper.get_branch_code_mapping()).fillna(
            buy_df["BRANCH"]
        )

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
                # If multiple BOIDs exist per client, keep the first non-empty one
                boid_by_client_code = temp.drop_duplicates("CLIENT CODE").set_index("CLIENT CODE")["BOID"]

        thursday_df = pd.DataFrame(
            {
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
            }
        )

        combined = pd.concat([df, thursday_df], ignore_index=True, sort=False)
        return combined

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
        bro_df = pd.DataFrame(rows, columns=["BRO", "CLIENT CODE"])
        merged = df.merge(bro_df, on="CLIENT CODE", how="left")
        merged["BRO"] = merged["BRO"].fillna("N/A")
        return merged




    def render_upload_mode(self):
        result, value = db.is_this_week_file_uploaded()
        if not result:
            uploaded_file = st.file_uploader("Import DPM3 file", type=".txt")
            if uploaded_file is None:
                return
            thursday_buy_floorsheet_date = st.date_input("Select thursday buy floorsheet date", value=helper.get_last_thursday())
            if st.button("Upload DPM3 file"):
                with st.status("📤 Uploading DPM3 file...", expanded=True) as status:
                    steps = [
                        ("Cleaning DPM3 file", self.extract_data_from_raw_txt_file, [uploaded_file]),
                        ("Matching ISIN number", self.enrich_with_isin, []),
                        ("Extracting client code & branch info", self.enrich_with_client_code_and_branch, []),
                        ("Adding Thursday buy data", self.append_thursday_buy_data, [thursday_buy_floorsheet_date]),
                        ("Extracting close price", self.enrich_with_close_price, []),
                        ("Extracting BROs", self.enrich_with_bro, []),
                        ("Dumping data to db", self.dump_data_to_db, [])
                    ]

                    df = None
                    for i, (label, func, args) in enumerate(steps, 1):
                        status.update(label=f"Step {i}/{len(steps)}: {label}", state="running")
                        sleep(0.3) 
                        if df is None:
                            df = func(*args)
                        else:
                            df = func(df, *args)
                    status.update(label="✅ Upload Completed", state="complete", expanded=False)
        else:
            formatted_date = value.strftime("%Y-%m-%d")
            weekday_name = value.strftime("%A")

            st.info(
                f"‎ ‎ ‎ DPM3 file uploaded on: {formatted_date} ({weekday_name})",
                icon="📢"
            )
            st.stop()



    # @st.cache_data(ttl=1600)
    def get_dpm3_data(_self):
        if 'dpm3' not in st.session_state:
            st.session_state['dpm3'] = db.get_dpm3()
        df:pd.DataFrame =  st.session_state['dpm3']
        df['CLIENT NAME'] = df['CLIENT NAME'].str.upper()
        df['BRANCH'] = df['BRANCH'].str.upper()
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
        col1, col2, col3 = st.columns(3)
        with col1:
            st.badge(f"Script Count: " + str(len(df)), color="green")
        with col2:
            st.badge(f"Total Free Balance: " + str(df["FREE BALANCE"].sum()), color="blue")
        with col3:
            st.badge(f"Total Valuation: " + f"{df['TOTAL VALUATION'].sum():,.2f}", color="yellow")
        st.data_editor(df, use_container_width=True, disabled=True)


    def render_latest_holdings_mode(self):
        with st.spinner("Loading latest holdings. Please wait...", show_time=True):
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
    
    def render_detailed_view_mode(self):
        with st.spinner("Loading detailed holdings. Please wait...", show_time=True):
            _, df_uploaded = self.get_dpm3_data()

            desired_cols = [
                "BRO",
                "SCRIPT",
                "CLIENT CODE",
                "CLIENT NAME",
                "BRANCH",
                "FREE BALANCE",
                "CLOSING PRICE",
                "FREE SHARE VALUATION",
                "PLEDGE SHARE VALUATION",
                "TOTAL VALUATION",
                "PLEDGE BALANCE",
                "CURRENT BALANCE",
                "STATUS",
                "uploaded_at",
                "BOID",
                "ISIN",
            ]

            df_all = df_uploaded.copy()
            for col in desired_cols:
                if col not in df_all.columns:
                    df_all[col] = ""

            df_all = df_all[desired_cols]
            # df_all.drop(columns=["uploaded_at", "BOID", "ISIN"], inplace=True)
            df_all.drop(columns=["uploaded_at", "ISIN", "STATUS", "BOID"], inplace=True)
            with st.expander("Filters", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    filter_field = st.selectbox(
                        "Filter by",
                        ["SCRIPT", "BRANCH", "BRO", "CLIENT CODE", "CLIENT NAME"],
                        index=0,
                    )

                options = (
                    df_all[filter_field]
                    .dropna()
                    .astype(str)
                    .map(lambda x: x.strip())
                    .loc[lambda s: s != ""]
                    .unique()
                    .tolist()
                )
                options = sorted(options)
                with col2:
                    selected_values = st.multiselect(
                        f"Select {filter_field}",
                        options=options,
                    )

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

            
            # Avoid Pandas Styler for very large tables (Streamlit will error if it exceeds max_elements).
            max_elements = int(pd.get_option("styler.render.max_elements"))
            if filtered.size <= max_elements:
                numeric_cols = filtered.select_dtypes(include="number").columns
                # st.data_editor doesn't support Pandas Styler; show formatted values via df copy.
                view_df = filtered.copy()
                for col in numeric_cols:
                    view_df[col] = view_df[col].map(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
                view_df.sort_values(by="CLIENT NAME", inplace=True)
                view_df.reset_index(drop=True, inplace=True)
                view_df.index = view_df.index + 1
                st.data_editor(view_df, width='stretch', disabled=True)
            else:
                filtered.sort_values(by="CLIENT NAME", inplace=True)
                filtered.reset_index(drop=True, inplace=True)
                filtered.index = filtered.index + 1
                st.data_editor(filtered, width='stretch', disabled=True)
        


    def get_thursday_buy_floorsheet(self, selected_date):    
        rows = db.get_floorsheet_from_date(selected_date)
        # rows = db.get_floorsheet_from_date(helper.get_last_thursday())
        df = pd.DataFrame(rows, columns=['CLIENT CODE', 'CLIENT NAME', 'SCRIPT', 'QUANTITY', 'RATE', 'AMOUNT', 'TRANSACTION TYPE', 'BRANCH', 'TRADE DATE'])
        
        # 1. Map Branch codes first
        df['BRANCH'] = df['BRANCH'].map(helper.get_branch_code_mapping()).fillna(df['BRANCH'])

        # 2. Aggregate data by Client and Script
        # We group by the unique identifiers for a holding
        agg_df = df.groupby(['CLIENT CODE', 'CLIENT NAME', 'SCRIPT', 'BRANCH'], as_index=False).agg({
            'QUANTITY': 'sum',
            'AMOUNT': 'sum'
        })

        # 3. Calculate Weighted Average Rate
        # Rate = Total Amount / Total Quantity
        agg_df['RATE'] = agg_df['AMOUNT'] / agg_df['QUANTITY']
        df['STATUS'] = 'THURSDAY BUY'
        # 4. Insert the aggregated data
        db.insert_to_dpm3_bulk(df=agg_df)
        

    def render_page(self):
        mode = st.radio("Select Mode", ["Latest Holdings (UAT)", "On Hold"], horizontal=True)
        if mode == "Latest Holdings (UAT)":
            with st.spinner("Loading latest holdings. Please wait...", show_time=True):
                df = get_latest_holdings()
                close_price_date = df['updated_at'].head(1).values[0]
                close_price_date = pd.to_datetime(close_price_date)
                formatted_date = close_price_date.strftime("%Y-%m-%d %I:%M %p")
                st.caption(f"Note: Close Price updated on: {formatted_date}")

                df.drop(columns=['STATUS', 'BOID'], inplace=True)
                df.rename(columns={'closePrice':'CLOSE PRICE', 'rmName':'BRO'}, inplace=True)

                df['FREE BALANCE'] = df['FREE BALANCE'].astype(float)
                df['PLEDGE BALANCE'] = df['PLEDGE BALANCE'].astype(float)
                df['CLOSE PRICE'] = df['CLOSE PRICE'].astype(float)

                df['FREE SHARE VALUATION'] = df['FREE BALANCE'] * df['CLOSE PRICE']
                df['PLEDGE SHARE VALUATION'] = df['PLEDGE BALANCE'] * df['CLOSE PRICE']
                df['TOTAL VALUATION'] = df['FREE SHARE VALUATION'] + df['PLEDGE SHARE VALUATION']

                col1, col2 = st.columns(2)
                with col1:
                    filter_by = st.selectbox(
                        "Filter by",
                        options=["ALL", "CLIENT CODE","CLIENT NAME" ,"SCRIPT", "BOID"]
                    )

                if filter_by != "ALL":
                    unique_values = sorted(df[filter_by].unique())
                    with col2:
                        selected_value = st.selectbox(
                            f"Select {filter_by}",
                            options=unique_values
                        )
                    df = df[df[filter_by] == selected_value].reset_index(drop=True)

                  

                # Display summary badges
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.badge(f"Total rows: {len(df):,}", color="green")
                with col2:
                    st.badge(f"Total Free Balance: {df['FREE BALANCE'].sum():,.2f}", color="blue")
                with col3:
                    st.badge(f"Total Valuation: {df['TOTAL VALUATION'].sum():,.2f}", color="orange")

                column_order = ['BRO','CLIENT CODE', 'CLIENT NAME', 'BRANCH', 'SCRIPT', 'CLOSE PRICE',
                                'TOTAL VALUATION', 'FREE BALANCE', 'PLEDGE BALANCE', 'LOCKIN BALANCE',
                                'FREE SHARE VALUATION', 'PLEDGE SHARE VALUATION']
                
                
                formatting_columns = ['CLOSE PRICE', 'FREE BALANCE', 'PLEDGE BALANCE', 'LOCKIN BALANCE',
                                    'FREE SHARE VALUATION', 'PLEDGE SHARE VALUATION', 'TOTAL VALUATION']

                df.sort_values(by="TOTAL VALUATION", inplace=True, ascending=False)
                for col in formatting_columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df[formatting_columns] = df[formatting_columns].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")

                df = df[column_order].reset_index(drop=True)
                df.index = df.index + 1
                st.dataframe(df, width='stretch')

                # 🔹 If filter is CLIENT CODE, also show On Hold data
                if filter_by in ["CLIENT CODE", "CLIENT NAME"]:
                    df_onhold = get_dpm3_onhold()
                    df_closing_price = get_latest_closing_price()
                    df_onhold = df_onhold.merge(
                        df_closing_price[['symbol', 'closePrice']], 
                        left_on="SCRIPT", 
                        right_on="symbol", 
                        how="left"
                    )

                    # Drop the duplicate 'symbol' column
                    df_onhold.drop(columns=['symbol'], inplace=True)

                    # If you want the column name to be consistent
                    df_onhold.rename(columns={'closePrice': 'CLOSE PRICE'}, inplace=True)
                    # Convert QUANTITY and CLOSE PRICE to numeric types first
                    df_onhold['QUANTITY'] = df_onhold['QUANTITY'].astype(float)
                    df_onhold['CLOSE PRICE'] = df_onhold['CLOSE PRICE'].astype(float)

                    # Compute TOTAL VALUATION
                    df_onhold['TOTAL VALUATION'] = df_onhold['QUANTITY'] * df_onhold['CLOSE PRICE']
                  
                    # Match dynamically based on filter_by
                    df_onhold = df_onhold[df_onhold[filter_by] == selected_value].reset_index(drop=True)

                    if not df_onhold.empty:
                        st.subheader("On Hold SCRIPTS", anchor=False)
                        df_onhold.index = df_onhold.index + 1
                        col_order = ['CLIENT CODE', 'CLIENT NAME', 'BRANCH', 'SCRIPT', 'QUANTITY', 'CLOSE PRICE', 'TOTAL VALUATION',
                                     'TRANSACTION TYPE', 'STATUS', 'SETTLEMENT DATE']
                        df_onhold = df_onhold[col_order]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.badge(f"Total rows: {len(df_onhold):,}", color="green")
                        with col2:
                            st.badge(f"Total Quantity: {df_onhold['QUANTITY'].sum():,.2f}", color="blue")
                        with col3:
                            st.badge(f"Total Valuation: {df_onhold['TOTAL VALUATION'].sum():,.2f}", color="orange")
                        df_onhold['QUANTITY'] = df_onhold['QUANTITY'].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
                        df_onhold['TOTAL VALUATION'] = df_onhold['TOTAL VALUATION'].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
                        st.dataframe(df_onhold, width='stretch')



        elif mode == "On Hold":
            with st.spinner("Loading on hold. Please wait...", show_time=True):
                df_onhold = get_dpm3_onhold()
                df_rm_map = get_client_rm_map()

                df_closing_price = get_latest_closing_price()
                df_onhold = df_onhold.merge(
                    df_closing_price[['symbol', 'closePrice']],
                    left_on="SCRIPT",
                    right_on="symbol",
                    how="left"
                )

                df_onhold = df_onhold.merge(
                    df_rm_map,
                    on="CLIENT CODE",
                    how="left"
                )

                # Replace missing BRO with "N/A"
                df_onhold['BRO'] = df_onhold['BRO'].fillna("N/A")


                # Drop duplicate symbol column
                df_onhold.drop(columns=['symbol'], inplace=True)

                # Rename for consistency
                df_onhold.rename(columns={'closePrice': 'CLOSE PRICE'}, inplace=True)

                # 🔹 Filtering UI
                col1, col2 = st.columns(2)
                with col1:
                    filter_by = st.selectbox(
                        "Filter by",
                        options=["ALL", "CLIENT CODE", "CLIENT NAME", "SCRIPT"]
                    )

                if filter_by != "ALL":
                    unique_values = sorted(df_onhold[filter_by].unique())
                    with col2:
                        selected_value = st.selectbox(
                            f"Select {filter_by}",
                            options=unique_values
                        )
                    df_onhold = df_onhold[df_onhold[filter_by] == selected_value].reset_index(drop=True)

                df_onhold['TOTAL VALUATION'] = df_onhold['QUANTITY'] * df_onhold['CLOSE PRICE']

                # Reset index for display
                df_onhold.sort_values(by="TOTAL VALUATION", inplace=True, ascending=False)
                df_onhold.reset_index(drop=True, inplace=True)
                df_onhold.index = df_onhold.index + 1
                col_order = ['BRO','CLIENT CODE', 'CLIENT NAME', 'BRANCH', 'SCRIPT', 'QUANTITY', 'CLOSE PRICE', 
                             'TOTAL VALUATION',
                                     'TRANSACTION TYPE', 'STATUS', 'SETTLEMENT DATE']
                df_onhold = df_onhold[col_order]
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.badge(f"Total rows: {len(df_onhold):,}", color="green")
                with col2:
                    st.badge(f"Total Quantity: {df_onhold['QUANTITY'].sum():,.2f}", color="blue")
                with col3:
                    st.badge(f"Total Valuation: {df_onhold['TOTAL VALUATION'].sum():,.2f}", color="orange")


                df_onhold['QUANTITY'] = df_onhold['QUANTITY'].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
                df_onhold['CLOSE PRICE'] = df_onhold['CLOSE PRICE'].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
                df_onhold['TOTAL VALUATION'] = df_onhold['TOTAL VALUATION'].map(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")
                st.dataframe(df_onhold, width='stretch')

if __name__ == "__main__":
    DPM3().render_page()
