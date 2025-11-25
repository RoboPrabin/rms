from datetime import datetime
import pandas as pd
from config import config

class WaccCalculator:

    def __init__(self):
        pass

    def calculate(self, live_market_data):
        ltp_dict = live_market_data

        # Load Excel
        df = pd.read_excel(config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL)
        
        # Initialize columns
        df['pendingWaccValuation'] = 0.0
        df['pendingWaccTotalQuantity'] = 0.0
        df['totalPurchaseCost'] = 0.0
        df['calculatedWacc'] = 0.0

        # --- Update LTP and Market Value ---
        df['ltp'] = df['script'].map(ltp_dict)  # or use correct column name
        df['ltp'] = df['ltp'].fillna(0.0)  # handle missing LTP

        # marketValue = currentBalance * ltp
        df['marketValue'] = df.apply(lambda row: float(row['currentBalance']) * float(row['ltp']),axis=1)

        df['averageBrokerCommission'] = 0.0
        df['sebon'] = 0.0
        df['dpFee'] = 25.0  # default value
        df['capitalGain'] = 0.0
        df['estimatedCapitalGainTax'] = 0.0
        df['profitLoss'] = 0.0
        df['profitLossPercentage'] = 0.0
        df['ledgerBalance'] = 0.0


        df["lastUpdated"] = datetime.now().strftime("%Y-%m-%d %I:%M:%S")
        # Iterate through rows
        for index, row in df.iterrows():
            pending_wacc_rate = str(row['pendingWaccRate']).replace(" ", "")
            pending_wacc_qty = str(row['pendingWaccQuantity']).replace(" ", "")

            # Convert lists safely
            if pending_wacc_qty == "0" or pending_wacc_rate == "0":
                qty_list, rate_list = [], []
            else:
                qty_list = [float(x) for x in pending_wacc_qty.split(",") if x]
                rate_list = [float(x) for x in pending_wacc_rate.split(",") if x]

            # Calculate total valuation and qty
            total_valuation = sum(q * r for q, r in zip(qty_list, rate_list))
            total_qty = sum(qty_list)

            # Save to dataframe
            df.at[index, 'pendingWaccValuation'] = total_valuation
            df.at[index, 'pendingWaccTotalQuantity'] = total_qty

            # Extract necessary base columns
            currentBalance = float(row['currentBalance'])
            wacc_rate = float(row['waccRate'])
            market_value = float(row['marketValue'])

            # --- COST LOGIC ---
            if total_qty == 0:
                cost = currentBalance * wacc_rate
            else:
                cost = total_valuation + (currentBalance - total_qty) * wacc_rate
            df.at[index, 'totalPurchaseCost'] = cost

            # --- BROKER COMMISSION / FEES ---
            avg_broker_commission = market_value * 0.003     # 0.3%
            sebon = market_value * 0.00015                   # 0.015%
            dp_fee = 25.0

            # --- CAPITAL GAIN ---
            capital_gain = (cost + avg_broker_commission + sebon + dp_fee) - market_value

            # --- ESTIMATED CAPITAL GAIN TAX ---
            estimated_tax = capital_gain * 0.075  # 7.5%

            # Store results
            calculated_wacc = (cost / currentBalance) if currentBalance != 0 else 0.0
            df.at[index, 'calculatedWacc'] = calculated_wacc
            df.at[index, 'averageBrokerCommission'] = avg_broker_commission
            df.at[index, 'sebon'] = sebon
            df.at[index, 'dpFee'] = dp_fee
            df.at[index, 'capitalGain'] = capital_gain
            df.at[index, 'estimatedCapitalGainTax'] = estimated_tax

            # --- PROFIT / LOSS ---
            profit_loss = market_value - cost - avg_broker_commission - sebon - dp_fee - estimated_tax
            df.at[index, 'profitLoss'] = round(profit_loss, 2)

            # --- PROFIT / LOSS % ---
            df.at[index, 'profitLossPercentage'] = round((profit_loss / cost * 100),2) if cost != 0 else 0.0


        # df = df.round(2)
        df['boid'] = df['boid'].astype(str)
        # df = df.applymap(lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else x)

        with pd.ExcelWriter(config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name='Result')
            workbook = writer.book
            worksheet = writer.sheets['Result']
            money_fmt = workbook.add_format({'num_format': '#,##0.00'})
            worksheet.set_column('A:AZ', 18, money_fmt)
        from db import db
        db.ensure_holdings_columns_exist()
        db.update_holdings_in_db(df)
        # print("[1] Wacc calculated successfully.")

    # def start_calulation(self, live_data:dict):
    #     self.calculate(live_market_data=live_data)

if __name__ == "__main__":
    wcc = WaccCalculator()
    from test_cases.niu_ltp_extractor import LtpExtractor
    wcc.calculate(live_market_data=LtpExtractor().fetch_live_market())