import random
from re import S
from time import sleep
import pandas as pd
import requests

from api.tms.shared_api_tms import get_cookie, get_headers, refresh_token
from utils.helper import show_message



def get_tms_server_id(client_code):
    while True:
        show_message(f"Fetching TMS server id for {client_code}")
        cookies = get_cookie()
        headers = get_headers()
        response = requests.get(
            f'https://tms48.nepsetms.com.np/tmsapi/orderbook/search-all-client/{client_code}',
            cookies=cookies,
            headers=headers,
        )
        if response.status_code == 200:
            return response.json()[0]['id']
        else:
            refresh_token()

def get_collateral_info(server_id:int):
    while True:
        show_message(f"Fetching Collateral Info.")
        cookies = get_cookie()
        headers = get_headers()

        response = requests.get(
            f'https://tms48.nepsetms.com.np/tmsapi/clientApi/rms-limit-setup/{server_id}',
            cookies=cookies,
            headers=headers,
        )
        if response.status_code == 200:
            response_data = response.json()
            return response_data['clientGroupId'], response_data['collateralUtilized'], response_data['creditForSale'], response_data['fundTransferAmount'], response_data['nonCashCollateralAmount'], response_data['topUpAmount']
        else:
            refresh_token()

def update_multiplication_factor(df, index, server_id, client_group_id, 
            collateral_utilized, credit_for_sale, 
            fund_transfer_amount, non_cash_collateral_amount, 
            topup_amount):
    while True:
        show_message(f"Updating TMS Multiplication Factor")
        cookies = get_cookie()
        headers = get_headers()


        json_data = {
            'cashCollateralAmount': 0,
            'chequeCollateralAmount': 0,
            'chequeDate': None,
            'chequeNo': None,
            'clientGroupId': client_group_id,
            'clientDealerMasterId': server_id,
            'collateralExpiryDate': None,
            'collateralMultiplicationFactor': 2,
            'collateralUtilized': collateral_utilized,
            'creditForSale': credit_for_sale,
            'fundTransferAmount': fund_transfer_amount,
            'nonCashCollateralAmount': non_cash_collateral_amount,
            'remarks': 'UMESH IT LOAD_COLLATERAL AS 0',
            'topUpAmount': topup_amount,
        }

        response = requests.post(
            'https://tms48.nepsetms.com.np/tmsapi/clientApi/rms-limit-setup/non-cash-collateral',
            cookies=cookies,
            headers=headers,
            json=json_data,
        )
        if response.status_code == 200:
            success_message = response.json()['message'].upper()
            df.loc[index, 'STATUS'] = success_message
            show_message(success_message,'green')
            print("*"*70)
            print("\n")
            return
        else:
            refresh_token()


def start_processing(filepath):
    df = pd.read_excel(filepath)
    total = len(df)
    for index, row in df.iterrows():
        client_code = str(row['clientcode']).strip()
        status = str(row['STATUS'])
        if status == "GIVE 2X":
            show_message(f"[{index+1}/{total}] Processing {client_code}")
            server_id = get_tms_server_id(client_code=client_code)
            client_group_id, collateral_utilized, credit_for_sale, fund_transfer_amount, non_cash_collateral_amount, topup_amount = get_collateral_info(server_id=server_id)

            update_multiplication_factor(df=df,index=index, server_id=server_id, client_group_id=client_group_id, collateral_utilized=collateral_utilized, credit_for_sale=credit_for_sale,
            fund_transfer_amount=fund_transfer_amount, non_cash_collateral_amount=non_cash_collateral_amount, topup_amount=topup_amount)
            sleep(random.randint(1,2))
    df.drop(columns=['debtoraccountnumber', 'creditoraccountnumber', 'batchid', 'referenceno', 'fundtransferdirection'], inplace=True)
    df.to_excel(filepath, index=False)
if __name__ == "__main__":
    start_processing()
            
