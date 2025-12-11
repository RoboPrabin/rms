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


class Uarf:
    def __init__(self):
        st.set_page_config("DPM3", page_icon="📦", layout='wide')

        # Dates
        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")
        self.today_np_date = nepali_date.today()

        # Authentication & User Info
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()

        # DB Connection
        self.holding_engine = get_holding_engine()
        st.header("📦 DPM3", anchor=False)

    def dump_data_to_db(self, df):
        engine = create_engine(get_holding_engine())
        df.to_sql(
            name="dpm3",
            con=engine,
            if_exists="replace",
            index=False
        )

    def extract_data_from_raw_txt_file(self, file_obj):
        columns_to_extract = {0: "BOID", 1: "ISIN", 2: "FREE BALANCE",
                              4: "PLEDGE BALANCE", 10: "CURRENT BALANCE"}
        numeric_columns = ["FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE"]

        data = []
        for line in file_obj:
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
        kyc_df["BOID"] = kyc_df["BOID"].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "")
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

    def show_file_upload(self):
        if "df_grouped" not in st.session_state:
            uploaded_file = st.file_uploader("Import DPM3 file", type=".txt")
            if uploaded_file is None:
                return

            with st.status("📤 Uploading DPM3 file...", expanded=True) as status:
                steps = [
                    ("Cleaning DPM3 file", self.extract_data_from_raw_txt_file, [uploaded_file]),
                    ("Matching ISIN number", self.enrich_with_isin, []),
                    ("Extracting client code & branch info", self.enrich_with_client_code_and_branch, []),
                    ("Extracting close price", self.enrich_with_close_price, []),
                    ("Extracting BROs", self.enrich_with_bro, [])
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

            # Save to session_state for fast access
            st.session_state["df_uploaded"] = df

            # Group for display
            group_keys = ["BRO","CLIENT CODE","CLIENT NAME","BRANCH","BOID"]
            sum_cols = ["FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE",
                        "FREE SHARE VALUATION",
                        "PLEDGE SHARE VALUATION", "TOTAL VALUATION"]
            df_grouped = df.groupby(group_keys, as_index=False)[sum_cols].sum()
            df_grouped["SCRIPT COUNT"] = df.groupby(group_keys)["SCRIPT"].count().values
            # df_grouped["CLIENT_LABEL"] = df_grouped["CLIENT NAME"] + " - " + df_grouped["CLIENT CODE"]
            st.session_state["df_grouped"] = df_grouped

        # Use cached grouped data
        df_grouped = st.session_state["df_grouped"]
        df_uploaded = st.session_state["df_uploaded"]

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

            # Choose only the visible columns
            view_cols = [
                "SCRIPT","FREE BALANCE","PLEDGE BALANCE","CURRENT BALANCE",
                "CLOSING PRICE","FREE SHARE VALUATION",
                "PLEDGE SHARE VALUATION","TOTAL VALUATION"
            ]

            # Open the dialog
            self.show_client_dialog(client_scripts[view_cols], f"👨🏻‍💻 {client_label} - {selected_code}")


    def render_page(self):
        self.show_file_upload()

    @st.dialog("📑 Client Scripts Detail", width="large")
    def show_client_dialog(self,df, label):
        st.subheader(label)
        st.dataframe(df, use_container_width=True)



if __name__ == "__main__":
    Uarf().render_page()
