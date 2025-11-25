
from sqlalchemy import create_engine
from config import config
import pandas as pd
from datetime import datetime
from utils import helper

class DBUpdater:
    def __create_columns(self, df):
         # Initialize columns
        df['pendingWaccValuation'] = 0.0
        df['pendingWaccTotalQuantity'] = 0.0
        df['totalPurchaseCost'] = 0.0
        df['calculatedWacc'] = 0.0

        df['averageBrokerCommission'] = 0.0
        df['sebon'] = 0.0
        df['dpFee'] = 25.0  # default value
        df['capitalGain'] = 0.0
        df['estimatedCapitalGainTax'] = 0.0
        df['profitLoss'] = 0.0
        df['profitLossPercentage'] = 0.0
        df['ledgerBalance'] = 0.0
        return df
    
    def push_data_to_db(self):
        engine = create_engine(helper.get_holding_engine())
        df = pd.read_excel(config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL)
        # df: pd.DataFrame = self.__create_columns()
        # df['bro'] = df['bro'].fillna("N/A")
        for col in ['bro_x', 'bro_y']:
            if col in df.columns:
                df = df.drop(columns=[col])

        df.to_sql("holdings", engine, if_exists="replace", index=False)
        print("✅ Data successfully dumped into DB.")