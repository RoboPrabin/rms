from utils import helper
import pandas as pd
from sqlalchemy import create_engine
from config import config

class ClientSummaryExtractor:
    def extract_client_summary(self):
        # Step 1: Load holdings_FINAL.xlsx
        file_path = config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL
        # file_path = r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\holdings_FINAL.xlsx"
        df = pd.read_excel(file_path)

        # Step 2: Group by client name and username
        grouped = df.groupby(['name', 'username']).agg({
            'marketValue': 'sum',
            'profitLoss': 'sum',
            'profitLossPercentage': 'sum',
            'ledgerBalance': 'first'
        }).reset_index()

        # Step 3: Rename columns
        aggregated = grouped.rename(columns={
            'name': 'clientName',
            'username': 'clientCode',
            'marketValue': 'currentMarketValue',
            'profitLoss': 'profitLossAmount',
            'profitLossPercentage': 'profitLossPercentage',
            'ledgerBalance': 'ledgerValue'
        })

        # Step 4: Connect to DB and fetch RM info
        engine = create_engine(helper.get_intranet_engine())
        df_client_rm = pd.read_sql("SELECT client_code, rm_id FROM client_rm", engine)
        df_rm = pd.read_sql("SELECT u_id, rm_name, rm_fname FROM rm_tbl", engine)

        # Step 5: Merge RM info
        df_client_rm['client_code'] = df_client_rm['client_code'].astype(str)
        aggregated['clientCode'] = aggregated['clientCode'].astype(str)

        df_merged = aggregated.merge(df_client_rm, left_on='clientCode', right_on='client_code', how='left')
        df_merged = df_merged.merge(df_rm, left_on='rm_id', right_on='u_id', how='left')

        # Step 6: Create Bro column
        df_merged['bro'] = df_merged['rm_name'].fillna('N/A') + ' ' + df_merged['rm_fname'].fillna('')
        df_cleaned = df_merged[[
            'bro',
            'clientName',
            'clientCode',
            'currentMarketValue',
            'profitLossAmount',
            'profitLossPercentage',
            'ledgerValue'
        ]]

        # Step 7: Save to Excel
        df_cleaned = df_cleaned.copy()
        df_cleaned['assignedLimit'] = 0.00
        df_cleaned['category'] = "CRED"

        # output_path = r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\bro_summary.xlsx"
        # df_cleaned.to_excel(output_path, index=False)
        engine_holding_db = create_engine(helper.get_holding_engine())
        # Step 8: Push to bro_summary table
        df_cleaned.to_sql("client_summary", engine_holding_db, if_exists="replace", index=False)

        helper.show_message("[4] Summary file with Bro name created and pushed to DB!")




# import pandas as pd

# # Load the Excel file
# file_path = r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\holdings_FINAL.xlsx"
# df = pd.read_excel(file_path)

# # Group by client name and username
# grouped = df.groupby(['name', 'username'])

# # Aggregate required columns
# aggregated = grouped.agg({
#     'marketValue': 'mean',
#     'profitLoss': 'mean',
#     'profitLossPercentage': 'mean',
#     'ledgerBalance': 'first'  # assuming it's the same across rows
# }).reset_index()

# # Rename columns to match desired output
# aggregated.rename(columns={
#     'name': 'ClientName',
#     'username': 'ClientCode',
#     'marketValue': 'CurrentMarketValue',
#     'profitLoss': 'ProfitLossAmount',
#     'profitLossPercentage': 'ProfitLossPercentage',
#     'ledgerBalance': 'LedgerValue'
# }, inplace=True)

# # Save to new Excel file
# output_path = r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\client_summary.xlsx"
# aggregated.to_excel(output_path, index=False)

# print("✅ Summary file created successfully!")