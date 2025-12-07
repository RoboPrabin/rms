import shutil
import os
from time import sleep
from datetime import datetime
import requests
from api.tms.shared_api_tms import get_cookie, get_headers
from api.tms.api_refresh_token import refresh_token
from ui.login_tms import login_tms
from utils.helper import show_message, create_folder_with_datetime, get_date_from_folderpath
import json
import pandas as pd


def fetch_order_book_open():
    show_message("Fetching order book OPEN...")
    cookies_init=get_cookie(),
    while True:
        response = requests.get(
            'https://tms48.nepsetms.com.np/tmsapi/orderTradeApi/orderbook-v2?&activeStatus=OPEN&activeStatus=PARTIALLY_TRADED&activeStatus=PENDING&activeStatus=MODIFIED&',
            cookies=cookies_init,
            headers=get_headers(),
        )

        if response.status_code == 200:
                show_message("Order book OPEN fetched successfully.", 'green')
                # show_message(json.dumps(response.json(), indent=4), 'green')
                # folderpath = create_folder_with_datetime()
                # date_name = datetime.now().strftime('%d-%b-%Y %I-%M-%S %p')
                # filepath = folder_path + f"\\order_book_{date_name}.xlsx"
                # pd.DataFrame(response.json()).to_excel(filepath, index=False)
                return response.json()
        else:
            show_message("Failed to fetch data, retrying...", 'red')
            # sleep(3)
            cookies, headers = refresh_token()
            cookies_init = cookies
            # login_tms()
            
def copy_order_book_file(source_file: str, base_destination_folder: str = r"D:\Trishakti Local Server\Report-2025\OrderBook-Main"):
    # Format today's folder name like "2025-June-12"
    today_folder_name = datetime.now().strftime("%Y-%B-%d")

    # Full path to the destination subfolder
    today_folder_path = os.path.join(base_destination_folder, today_folder_name)

    # Ensure today's folder exists
    os.makedirs(today_folder_path, exist_ok=True)

    # Full destination file path
    destination_file = os.path.join(today_folder_path, os.path.basename(source_file))

    try:
        shutil.copy2(source_file, destination_file)
        show_message(f"File copied successfully to: {destination_file}")
    except Exception as e:
        show_message(f"Failed to copy file:\n{e}")


def fetch_order_book_completed(folder_path):
    show_message("Fetching order book COMPLETED...")
    cookies_init=get_cookie(),
    while True:
        response = requests.get(
            'https://tms48.nepsetms.com.np/tmsapi/orderTradeApi/orderbook-v2?&activeStatus=COMPLETED&activeStatus=CANCELLED&activeStatus=REJECTED&activeStatus=TMS_REJECTED&activeStatus=PARTIALLY_CANCELLED&activeStatus=MODIFIED_CANCELLED&',
            cookies=cookies_init,
            headers=get_headers(),
        )
        if response.status_code == 200:
            show_message("Order book fetched successfully.", 'green')
            # show_message(json.dumps(response.json(), indent=4), 'green')
            # folderpath = create_folder_with_datetime()
            date_name = datetime.now().strftime('%d-%b-%Y %I-%M-%S %p')
            filepath = folder_path + f"\\tms_order_book_{date_name}.xlsx"
            pd.DataFrame(response.json()).to_excel(filepath, index=False)
            print("\n")
            show_message(f"OG order book filepath: {filepath}", "yellow")
            copy_order_book_file(source_file=filepath)            
            return response.json()
        else:
            show_message("Failed to fetch data, retrying...", 'red')
            # login_tms()
            cookies, headers = refresh_token()
            cookies_init = cookies


def fetch_trade_order_book():
    cookies_init = get_cookie()
    while True:
        show_message("Fetching order book...")
        response = requests.get('https://tms48.nepsetms.com.np/tmsapi/orderTradeApi/tradebook-v2', cookies=cookies_init, headers=get_headers(referer='https://tms48.nepsetms.com.np/tms/me/trade-book'))
        if response.status_code ==200:
            show_message("Order book fetched successfully.", 'green')
            break
        else:
            show_message("Failed to fetch data, retrying...", 'red')
            # login_tms()
            cookies, headers = refresh_token()
            cookies_init = cookies

    df_trade_book = pd.DataFrame(response.json())
    df_trade_book['buyOrSell'] = df_trade_book['buyOrSell'].replace({1: 'BUY', 2: 'SELL'})
    df_trade_book['amount'] = df_trade_book['tradePrice'].astype(float) * df_trade_book['tradedQuantity'].astype(float)


    df = df_trade_book
    # df.to_excel("hello.xlsx", index=False)
    # Group by clientMemberCode and buyOrSell, summing the amount
    summary = df.groupby(['clientMemberCode', 'buyOrSell'])['amount'].sum().unstack().fillna(0)
    # Rename columns for clarity
    summary.columns = ['buyAmount', 'sellAmount']
    summary['buyAmount'] = summary['buyAmount'] * -1
    
    # Calculate netAmount
    summary['netAmount'] =  summary['sellAmount'] + summary['buyAmount']
    # Determine buy/sell status
    # summary['buy/sell'] = summary.apply(
    #     lambda x: 'BOTH' if x['buyAmount'] > 0 and x['sellAmount'] > 0 else ('BUY' if x['buyAmount'] > 0 else 'SELL'),
    #     axis=1
    # )
    summary['buy/sell'] = summary.apply(
        lambda x: 'BOTH' if x['buyAmount'] < 0 and x['sellAmount'] > 0 else (
            'BUY' if x['buyAmount'] < 0 else (
                'SELL' if x['sellAmount'] > 0 else 'NONE'
            )
        ),
        axis=1
    )

    
    # Reset index and rename clientMemberCode to clientName
    # summary = summary.reset_index().rename(columns={'clientMemberCode': 'clientName'})
    summary = summary.reset_index()
    # Reorder columns
    summary = summary[['clientMemberCode', 'buy/sell', 'buyAmount', 'sellAmount', 'netAmount']]
    # folderpath = create_folder_with_datetime()
    # date_name = datetime.now().strftime('%d-%b-%Y %I-%M-%S %p')
    # filepath = folder_path + f"\\trade_book_{date_name}.xlsx"
    # summary.to_excel(filepath, index=False)
    return summary

