from sqlalchemy import create_engine
from utils.formatting import *
from time import sleep
from db import db

import pandas as pd
import io
from nepali_datetime import date as nepali_date
from datetime import date


import numpy as np
import streamlit as st
import pandas as pd
from utils import helper
from datetime import datetime, timedelta
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
from config import config


from utils.helper import  show_message, get_holding_engine
import pandas as pd
import chardet
pd.set_option("styler.render.max_elements", 1677849)

class Uarf:
    def __init__(self):
        st.set_page_config("DPM3", page_icon="📦", layout='wide')

        self.today_eng_date = datetime.now().strftime("%Y-%m-%d (%A)")

        self.today_np_date = nepali_date.today()
        today_np = nepali_date.today()
        # Authentication & User Info
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()
        self.username, self.role = app_state.get_current_user_info()
        navigation.render_sidebar()

        # DB Connection
        self.holding_engine = helper.get_holding_engine()

        st.header("📦 DPM3", anchor=False)
    def dump_data_to_db(self, df):
        engine = create_engine(get_holding_engine())
        df.to_sql(
            name="dpm3",
            con=engine,
            if_exists="replace",   # options: 'fail', 'replace', 'append'
            index=False            # don’t write DataFrame index as a column
        )
    def detect_encoding(self, filepath):
        with open(filepath, 'rb') as f:
            raw = f.read(10000)  # first 10KB
            return chardet.detect(raw)['encoding']
        
    def enrich_with_isin(self, df: pd.DataFrame) -> pd.DataFrame:
        rows = db.get_isin_data()
        isin_df = pd.DataFrame(rows, columns=["ISIN", "SCRIP"])

        merged = df.merge(isin_df, on="ISIN", how="left")
        merged["SCRIPT"] = merged["SCRIP"]
        merged = merged.drop(columns=["SCRIP"])
        merged['SCRIPT'] = merged['SCRIPT'].fillna("N/F") 
        return merged
    
    def enrich_with_close_price(self, df: pd.DataFrame) -> pd.DataFrame:
        # Fetch average price rows from DB
        rows = db.get_table_average_price()
        # Use the actual column names returned by DB
        df_avp = pd.DataFrame(rows, columns=["SYMBOL", "closePrice"])

        # Rename SYMBOL -> SCRIPT so it matches your DPM3 df
        df_avp = df_avp.rename(columns={"SYMBOL": "SCRIPT"})

        # Merge on SCRIPT
        merged = df.merge(df_avp, on="SCRIPT", how="left")

        # ✅ Now create/overwrite CLOSING PRICE column from closePrice
        merged["CLOSING PRICE"] = merged["closePrice"].astype(float).fillna(0.0)

        # Drop helper column if you don’t want it
        merged = merged.drop(columns=["closePrice"])

        # Compute valuations
        merged["FREE SHARE VALUATION"] = merged["FREE BALANCE"] * merged["CLOSING PRICE"]
        merged["PLEDGE SHARE VALUATION"] = merged["PLEDGE BALANCE"] * merged["CLOSING PRICE"]
        merged["TOTAL VALUATION"] = merged["FREE SHARE VALUATION"] + merged["PLEDGE SHARE VALUATION"]

        return merged
    
    def enrich_with_bro(self, df:pd.DataFrame) -> pd.DataFrame:
        rows = db.get_table_rm_child_map()
        client_rm_map_df = pd.DataFrame(rows, columns=["BRO", "CLIENT NAME"])
        merged = df.merge(client_rm_map_df, on="CLIENT NAME", how="left")
        merged['BRO'] = merged['BRO'].fillna("N/A")
        return merged


    def enrich_with_client_code_and_branch(self, df: pd.DataFrame) -> pd.DataFrame:
        # Fetch KYC rows from DB
        rows = db.get_kyc()
        kyc_info = pd.DataFrame(rows, columns=["CLIENT CODE","CLIENT NAME", "BRANCH", "BOID"])

        # Convert Boid to string and strip trailing ".0"
        kyc_info["BOID"] = kyc_info["BOID"].apply(
            lambda x: str(int(float(x))) if pd.notnull(x) else ""
        )

        # Align column names for merge: uploaded df has "BOID"
        # kyc_info = kyc_info.rename(columns={"Boid": "BOID"})

        # Merge on BOID
        merged = df.merge(kyc_info, on="BOID", how="left")

        # Fill missing values with defaults
        merged["CLIENT CODE"] = merged["CLIENT CODE"].fillna("N/F")
        merged["CLIENT NAME"] = merged["CLIENT NAME"].fillna("N/F")
        merged["BRANCH"] = merged["BRANCH"].fillna("N/F")
        merged['uploaded_at'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        return merged

    def extract_data_from_raw_txt_file(self, file_obj):
        columns_to_extract = {
            0: "BOID",
            1: "ISIN",
            2: "FREE BALANCE",
            4: "PLEDGE BALANCE",
            10: "CURRENT BALANCE"
        }
        numeric_columns = ["FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE"]

        data = []
        # Read uploaded file line by line
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

        # Add extra columns with defaults
        df["SCRIPT"] = "NAN"
        df["CLOSING PRICE"] = 0.0
        df["FREE SHARE VALUATION"] = 0.0
        df["PLEDGE SHARE VALUATION"] = 0.0
        df["TOTAL VALUATION"] = 0.0
        # Preview in Streamlit
        # st.dataframe(df)
        return df

    def show_file_upload(self):
        uploaded_file = st.file_uploader(label="Import DPM3 file", type=".txt")
        if uploaded_file is not None:
            # with st.spinner("Please wait  . . . .", show_time=True):
            empty_space = st.empty()
            with empty_space.container():
                with st.status("📤 Uploading DPM3 file. Please wait ...", expanded=True) as status:
                    st.write("✔ Cleaning dpm3 file")
                    sleep(1)
                    df = self.extract_data_from_raw_txt_file(uploaded_file)
                    st.write("✔ Matching ISIN number")
                    sleep(1)
                    df = self.enrich_with_isin(df)
                    st.write("✔ Extracting client code, branch info from kyc")
                    sleep(1)
                    df = self.enrich_with_client_code_and_branch(df)
                    st.write("✔ Extracting close price")
                    sleep(1)
                    df = self.enrich_with_close_price(df=df)
                    st.write("✔ Extracting BROs")
                    sleep(1)
                    df = self.enrich_with_bro(df=df)
                    # Show in Streamlit
                    status.update(label="Upload Completed", state="complete", expanded=False)
                    sleep(0.6)
                empty_space.empty()
            # First, coerce numeric columns
            numeric_cols = ["FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE",
                            "CLOSING PRICE", "FREE SHARE VALUATION",
                            "PLEDGE SHARE VALUATION", "TOTAL VALUATION"]

            # df = coerce_numeric_columns(df, numeric_cols)

            # # Apply accounting format + highlight negative using Pandas Styler
            # styled_df = (
            #     df.style
            #     .format(accounting_format, subset=numeric_cols)   # format numbers
            #     .map(highlight_negative, subset=numeric_cols) # highlight negatives
            # )

            # # Show styled DataFrame in Streamlit
            # st.dataframe(styled_df)
            
            
            
            # Define the preferred order
            column_order = ["BRO", "CLIENT CODE", "CLIENT NAME", "BRANCH", "BOID"]

            # Build the final order: first your preferred columns, then all the rest
            final_order = column_order + [col for col in df.columns if col not in column_order]

            # Reorder DataFrame
            df = df[final_order]
            df.sort_values(by="BRO", inplace=True)
            df.reset_index(inplace=True, drop=True)
            df.index = df.index + 1
            self.dump_data_to_db(df=df)
            df.drop(columns=['uploaded_at'], inplace=True)
            # st.dataframe(df)

            # nf_client_code_count = (df["CLIENT CODE"] == "N/F").sum()
            # # Count rows where BRANCH == "N/F"
            # nf_branch_count = (df["BRANCH"] == "N/F").sum()
            # nf_bro_count = (df["BRO"] == "N/A").sum()

            # st.badge(f"Total N/A BRO: {nf_bro_count:,}", color="red")
            # st.badge(f"Total N/F Clients: {nf_client_code_count:,}", color="red")
            # st.badge(f"Total N/F Branch: {nf_branch_count:,}", color="red")




            # Define the grouping keys (client identity)
            group_keys = ["BRO","CLIENT CODE", "CLIENT NAME", "BRANCH", "BOID"]

            # Define which numeric columns you want to sum
            sum_cols = ["FREE BALANCE", "PLEDGE BALANCE", "CURRENT BALANCE",
                        "CLOSING PRICE", "FREE SHARE VALUATION",
                        "PLEDGE SHARE VALUATION", "TOTAL VALUATION"]

            # Group by client and sum numeric columns
            df_grouped = df.groupby(group_keys, as_index=False)[sum_cols].sum()

            # Optional: add row count per client (number of scripts)
            df_grouped["SCRIPT COUNT"] = df.groupby(group_keys)["SCRIPT"].count().values

            st.badge(f"Total rows: {len(df_grouped):,}", color="green")
            # Show in Streamlit
            df_grouped.sort_values(by="BRO", inplace=True)
            df_grouped.reset_index(inplace=True, drop=True)
            df_grouped.index = df_grouped.index + 1
            # st.dataframe(df_grouped)
            


            df_grouped["CLIENT_LABEL"] = df_grouped["CLIENT NAME"] + " - " + df_grouped["CLIENT CODE"]

            selection = st.dataframe(
                df_grouped,
                key="client_table",
                selection_mode="single-row",
                on_select="rerun"
            )

            if selection.selection.rows:
                row_idx = selection.selection.rows[0]
                selected_code = df_grouped.iloc[row_idx]["CLIENT CODE"]

                client_scripts = df[df["CLIENT CODE"] == selected_code].copy()
                client_scripts.reset_index(drop=True, inplace=True)
                client_scripts.index += 1

                st.subheader(f"Scripts for {df_grouped.iloc[row_idx]['CLIENT_LABEL']}")
                st.dataframe(client_scripts[[
                    "SCRIPT","FREE BALANCE","PLEDGE BALANCE","CURRENT BALANCE",
                    "CLOSING PRICE","FREE SHARE VALUATION",
                    "PLEDGE SHARE VALUATION","TOTAL VALUATION"
                ]])   
                        

            # Select a client to drill down
            # Build a combined label column
            # df_grouped["CLIENT_LABEL"] = df_grouped["CLIENT NAME"] + " - " + df_grouped["CLIENT CODE"]

            # # Use that in the selectbox
            # selected_label = st.selectbox("Select client to view scripts", df_grouped["CLIENT_LABEL"].unique())

            # # Extract the client code back from the label if needed
            # selected_code = selected_label.split(" - ")[1]


            # # Show scripts for that client
            # client_scripts = df[df["CLIENT CODE"] == selected_code]
            # client_scripts.reset_index(drop=True, inplace=True)
            # client_scripts.index = client_scripts.index + 1
            # st.dataframe(client_scripts[["SCRIPT","FREE BALANCE","PLEDGE BALANCE","CURRENT BALANCE",
            #                             "CLOSING PRICE","FREE SHARE VALUATION",
            #                             "PLEDGE SHARE VALUATION","TOTAL VALUATION"]])






    def render_page(self):
        self.show_file_upload()
        # rows = db.get_table_rm_child_map()
        # client_rm_map_df = pd.DataFrame(rows, columns=["BRO", "CLIENT NAME"])
        # print(client_rm_map_df)


if __name__ == "__main__":
    Uarf().render_page()