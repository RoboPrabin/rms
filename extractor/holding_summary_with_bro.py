import pandas as pd
from sqlalchemy import create_engine,text
from utils import helper
from config import config

class BroExtractor:

    def extract_and_update_bro(self):
        # Engines
        intranet_engine = create_engine(helper.get_intranet_engine())
        holding_engine = create_engine(helper.get_holding_engine())

        # === STEP 1: Read Excel ===
        # df_excel = pd.read_excel(config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL)

        # Replace holdings table
        # df_excel.to_sql("holdings", holding_engine, if_exists="replace", index=False)

        # === STEP 2: Fetch RM data from intranet DB ===
        df_client_rm = pd.read_sql("SELECT client_code, rm_id FROM client_rm", intranet_engine)
        df_rm = pd.read_sql("SELECT u_id, rm_name, rm_fname FROM rm_tbl", intranet_engine)

        df_map = df_client_rm.merge(df_rm, left_on='rm_id', right_on='u_id', how='left')
        df_map['bro'] = df_map['rm_name']
        # df_map['bro'] = df_map['rm_name'] + ' ' + df_map['rm_fname']
        df_map = df_map[['client_code', 'bro']]

        # === STEP 3: Push mapping into holding DB ===
        df_map.to_sql("rm_map_temp", holding_engine, if_exists="replace", index=False)

        # === STEP 4: Update holdings table inside DB ===
        with holding_engine.begin() as conn:
            conn.execute(text("""
                ALTER TABLE holdings 
                ADD COLUMN IF NOT EXISTS bro TEXT;
            """))

            conn.execute(text("""
                UPDATE holdings h
                SET bro = COALESCE(r.bro, 'N/A')
                FROM rm_map_temp r
                WHERE h."clientCode" = r.client_code;
            """))

            conn.execute(text("""
                UPDATE holdings
                SET bro = 'N/A'
                WHERE bro IS NULL;
            """))
        

        # helper.show_message("[1] BRO column updated successfully.")

    # def extract_bro(self):
    #     # Step 1: Read Excel
    #     excel_path = config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL
    #     df_excel = pd.read_excel(excel_path)

    #     # Step 2: Connect to PostgreSQL
    #     engine = create_engine(helper.get_intranet_engine())
    #     df_client_rm = pd.read_sql("SELECT client_code, rm_id FROM client_rm", engine)
    #     df_rm = pd.read_sql("SELECT u_id, rm_name, rm_fname FROM rm_tbl", engine)

    #     # Step 3: Merge RM info into client_rm
    #     df_merged = df_client_rm.merge(df_rm, left_on='rm_id', right_on='u_id', how='left')

    #     # Step 4: Create 'Bro' column using RM name
    #     df_merged['bro'] = df_merged['rm_name'] + ' ' + df_merged['rm_fname']

    #     # Step 5: Ensure matching data types for merge
    #     df_excel['username'] = df_excel['username'].astype(str)
    #     df_merged['client_code'] = df_merged['client_code'].astype(str)

    #     # Step 6: Merge RM info into Excel data
    #     df_final = df_excel.merge(df_merged[['client_code', 'bro']], left_on='username', right_on='client_code', how='left')

    #     df_final.drop(columns=['client_code'], inplace=True)

    #     df_final['clientCode'] = df_final['clientCode'].fillna("N/A")
    #     helper.convert_columns_to_str(df=df_final)
    #     # Step 8: Save enriched Excel file
    #     # output_path = r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\holdings_with_bro.xlsx"
    #     df_final.to_excel(excel_path, index=False)

    #     print("[2] Excel file enriched with Bro column and saved successfully!")
    #     self.push_data_to_db()


    # def push_data_to_db(self):
    #     engine = create_engine(helper.get_holding_engine())
    #     df = pd.read_excel(config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL)
    #     df.to_sql("holdings", engine, if_exists="replace", index=False)
    #     print("[3] Holdings data successfully dumped into 'holdings' table.")