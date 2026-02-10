from time import sleep
import pandas as pd
from sqlalchemy import create_engine
from utils import helper
from config import config
from db import db
import re

class ClientSummaryExtractor:

    def extract_client_summary(self):
        # Step 1: Load holdings from DB
        df = db.get_table_holdings_in_df()
        # print("Holdings table preview:")
        # print(df.head())
        
        # Save a check Excel
        # df.to_excel(r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\check.xlsx", index=False)

        # Step 2: Normalize clientCode for consistency
        def clean_code(s):
            if pd.isna(s):
                return ''
            return re.sub(r'\s+', '', str(s)).upper()

        df['clientCode'] = df['clientCode'].apply(clean_code)

        # Step 3: Group by client name, username, and clientCode
        grouped = df.groupby(['name', 'username', 'clientCode']).agg({
            'marketValue': 'sum',
            'profitLoss': 'sum',
            'profitLossPercentage': 'sum',
            'ledgerBalance': 'first'
        }).reset_index()

        # Step 4: Rename columns
        aggregated = grouped.rename(columns={
            'name': 'clientName',
            # 'username': 'clientCode',  
            'marketValue': 'currentMarketValue',
            'profitLoss': 'profitLossAmount',
            'profitLossPercentage': 'profitLossPercentage',
            'ledgerBalance': 'ledgerValue'
        })

        # Step 5: Connect to intranet DB and fetch RM info
        engine_intranet = create_engine(helper.get_intranet_engine())
        df_client_rm = pd.read_sql("SELECT client_code, rm_id FROM client_rm", engine_intranet)
        df_rm = pd.read_sql("SELECT u_id, rm_name, rm_fname FROM rm_tbl", engine_intranet)

        # Normalize client codes in client_rm
        df_client_rm['client_code'] = df_client_rm['client_code'].apply(clean_code)

        # Step 6: Merge RM info
        df_merged = aggregated.merge(
            df_client_rm, left_on='clientCode', right_on='client_code', how='left'
        )
        df_merged = df_merged.merge(
            df_rm, left_on='rm_id', right_on='u_id', how='left'
        )

        # Step 7: Create Bro column
        df_merged['bro'] = df_merged['rm_name'].fillna('N/A')
        df_merged['bro'] = df_merged['bro'].str.strip()

        # Step 8: Select final columns
        df_cleaned = df_merged[[
            'bro',
            'clientName',
            'clientCode',
            'currentMarketValue',
            'profitLossAmount',
            'profitLossPercentage',
            'ledgerValue'
        ]].copy()

        # Step 9: Add additional columns
        df_cleaned['assignedLimit'] = 0.00
        df_cleaned['category'] = "CRED"

        # Step 10: Save to Excel
        # output_path = r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\client_summary.xlsx"
        # df_cleaned.to_excel(output_path, index=False)

        # Step 11: Push to holding DB
        engine_holding_db = create_engine(helper.get_holding_engine())
        df_cleaned.to_sql("client_summary", engine_holding_db, if_exists="replace", index=False)

        # helper.show_message("[4] Summary file with Bro name created and pushed to DB!")
        # sleep(6)


# Run the extractor
# ClientSummaryExtractor().extract_client_summary()
