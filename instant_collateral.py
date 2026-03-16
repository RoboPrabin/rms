import pandas as pd
from db import db
from utils import helper
from api.tms.api_collateral import get_tms_server_id, get_collateral_info, update_multiplication_factor
class InstantCollateral:
    def __init__(self):
        pass

    def get_client_category(self):
        rows = db.fetch_clients_category()
        df = pd.DataFrame(rows, columns=['Client Name', 'Client Code', 'Category', 'Credit Limit'])
        return df
    
    def get_trade_book(self):
        rows = db.fetch_trade_book_test()
        df = pd.DataFrame(rows, columns=['Client Name', 'Client Code', 'Transaction Type', 'Sell Amount'])
        return df
    
    def match_client_category_with_trade_book(self, client_category_df, trade_book_df):
        # We perform an inner join on 'Client Code'
        # This will drop any trades where the client code isn't in the category list
        matched_df = pd.merge(
            trade_book_df, 
            client_category_df[['Client Code', 'Category', 'Credit Limit']], 
            on='Client Code', 
            how='inner'
        )
        return matched_df
    
    def get_list_of_instant_collateral_receiver(self):
        matched_df = self.match_client_category_with_trade_book(self.get_client_category(), self.get_trade_book())
        matched_df.sort_values(by='Category', inplace=True)
        print(matched_df)
        return matched_df
    
    def process_instant_collateral(self):
        # DF from trade_book db, updated every 1 minute.
        df = self.get_list_of_instant_collateral_receiver()
        df.to_excel("instant_collateral.xlsx", index=False)

        total = len(df)
        for index, row in df.iterrows():
            client_code = str(row['Client Code']).upper()
            category = str(row['Category']).upper()
            sell_amount = int(row['Sell Amount'])
            helper.show_message(f"[{index+1}/{total}] Processing {client_code} with category {category}")
            server_id = get_tms_server_id(client_code=client_code)
            client_group_id, collateral_utilized, credit_for_sale, fund_transfer_amount, non_cash_collateral_amount, topup_amount = get_collateral_info(server_id=server_id)
            
            if category == "NONE":
                update_multiplication_factor(df=df,index=index, server_id=server_id, client_group_id=client_group_id, 
                                            collateral_utilized=collateral_utilized, credit_for_sale=sell_amount,
                                            fund_transfer_amount=fund_transfer_amount, 
                                            non_cash_collateral_amount=0, 
                                            topup_amount=0)
            elif category == "CASH" or category == "CREDIT":
                update_multiplication_factor(df=df,index=index, server_id=server_id, client_group_id=client_group_id, 
                                            collateral_utilized=collateral_utilized, credit_for_sale=sell_amount,
                                            fund_transfer_amount=fund_transfer_amount, 
                                            non_cash_collateral_amount=non_cash_collateral_amount, 
                                            topup_amount=topup_amount)
            elif category == "DUE":
                update_multiplication_factor(df=df,index=index, server_id=server_id, client_group_id=client_group_id, 
                                            collateral_utilized=collateral_utilized, credit_for_sale=sell_amount,
                                            fund_transfer_amount=fund_transfer_amount, 
                                            non_cash_collateral_amount=0, 
                                            topup_amount=0)


            # update_multiplication_factor(df=df,index=index, server_id=server_id, client_group_id=client_group_id, 
            #                             collateral_utilized=collateral_utilized, credit_for_sale=credit_for_sale,
            #                             fund_transfer_amount=fund_transfer_amount, 
            #                             non_cash_collateral_amount=non_cash_collateral_amount, 
            #                             topup_amount=topup_amount)





if __name__ == "__main__":
    instant_collateral = InstantCollateral()
    instant_collateral.process_instant_collateral()