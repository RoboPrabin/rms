import pandas as pd
from sqlalchemy import create_engine, text
from config import config
from utils import helper

class ManagerSummaryExtractor:
    def extract_manager_summary(self):
        # Step 1: Load holdings_FINAL.xlsx
        holdings_path = config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL
        df_holdings = pd.read_excel(holdings_path)

        # Step 2: Connect to PostgreSQL
        engine = create_engine(helper.get_intranet_engine())
        df_client_rm = pd.read_sql("SELECT client_code, rm_id FROM client_rm", engine)
        df_rm = pd.read_sql("SELECT u_id, rm_name, rm_fname FROM rm_tbl", engine)

        # Step 3: Aggregate client-level data
        df_holdings['username'] = df_holdings['username'].astype(str)
        grouped = df_holdings.groupby(['name', 'username']).agg({
            'marketValue': 'sum',
            'profitLoss': 'sum',
            'profitLossPercentage': 'sum',
            'ledgerBalance': 'first',
            'totalPurchaseCost': 'sum'
        }).reset_index()

        grouped.rename(columns={
            'name': 'clientName',
            'username': 'clientCode',
            'marketValue': 'currentMarketValue',
            'profitLoss': 'unrealisedProfitLoss',
            'profitLossPercentage': 'profitLossPercentage',
            'ledgerBalance': 'totalLedgerBalance',
            'totalPurchaseCost': 'assetsUnderCustody'
        }, inplace=True)

        # Step 4: Merge RM info
        df_client_rm['client_code'] = df_client_rm['client_code'].astype(str)
        grouped['clientCode'] = grouped['clientCode'].astype(str)

        df_merged = grouped.merge(df_client_rm, left_on='clientCode', right_on='client_code', how='left')
        df_merged = df_merged.merge(df_rm, left_on='rm_id', right_on='u_id', how='left')

        # Step 5: Create broName
        df_merged['bro'] = df_merged['rm_name'].fillna('N/A') + ' ' + df_merged['rm_fname'].fillna('')

        # Step 6: Aggregate by BRO
        manager_summary = df_merged.groupby('bro').agg({
            'clientCode': 'nunique',
            'assetsUnderCustody': 'sum',
            'currentMarketValue': 'sum',
            'unrealisedProfitLoss': 'sum',
            'totalLedgerBalance': 'sum',
        }).reset_index()

        manager_summary.rename(columns={
            'clientCode': 'totalClients'
        }, inplace=True)

        # Step 7: Save to Excel
        output_path = r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\manager_summary.xlsx"
        # manager_summary['usedLimit'] = 0
        # manager_summary['totalLimit'] = 0
        # manager_summary['availableLimit'] = 0
        manager_summary.to_excel(output_path, index=False)
        print("✅ Manager summary with BRO-level aggregation created successfully!")

        # Step 8: Push to DB
        engine = create_engine(helper.get_holding_engine())

        manager_summary.to_sql("manager_summary", engine, if_exists="replace", index=False)
        print("✅ Summary file pushed to manager_summary table in client_holdings DB!")

        engine = create_engine(helper.get_holding_engine())
        with engine.begin() as conn:
            conn.execute(text("""
                ALTER TABLE manager_summary
                ADD COLUMN "usedLimit" NUMERIC DEFAULT 0,
                ADD COLUMN "totalLimit" NUMERIC DEFAULT 0;
            """))

            conn.execute(text("""
                ALTER TABLE manager_summary
                ADD COLUMN "availableLimit" NUMERIC GENERATED ALWAYS AS ("totalLimit" - "usedLimit") STORED;
            """))


        print("✅ Columns dropped and 'availableLimit' added as a generated column.")



if __name__ == "__main__":
    ManagerSummaryExtractor().extract_manager_summary()