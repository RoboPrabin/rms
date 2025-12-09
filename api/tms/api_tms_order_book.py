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
from utils.helper import show_message, show_message_box, get_holding_engine
from sqlalchemy import create_engine


def push_to_order_book_db(df:pd.DataFrame, table_name:str="order_book"):
    engine = create_engine(get_holding_engine())
    df.to_sql(
    table_name,        
    engine,              
    if_exists="replace",  
    index=False          
    )
    show_message(f"'ORDER BOOK' data dumbed to order_book Table.", color="cyan")


def extract_rm_in_order_book(order_book_df:pd.DataFrame):
    # Create DB engine
    engine = create_engine(get_holding_engine())
    # Query DB
    with engine.connect() as conn:
        df = pd.read_sql_query("SELECT * FROM client_rm_map", con=conn)

    # Merge: match clientMemberCode (Excel) with clientCode (DB)
    merge_df = order_book_df.merge(
        df[['clientCode', 'rmName']], 
        left_on='clientMemberCode', 
        right_on='clientCode', 
        how='left'   # keep all rows from Excel
    )

    # Optional: drop clientCode if you don’t need duplicate
    merge_df = merge_df.drop(columns=['clientCode'])
    merge_df['rmName'] = merge_df['rmName'].fillna("N/A")

    preferred_order = [
        'rmName',
        'clientMemberCode',
        'symbol',
        # 'securityName',
        'buyOrSell',
        'orderQuantity',
        'orderPrice',
        'amount'
    ]

    # Add any other columns that exist but aren’t in preferred_order
    cols = preferred_order + [col for col in merge_df.columns if col not in preferred_order]
    # Reorder DataFrame
    merge_df = merge_df[cols]
    return merge_df


def fetch_order_book_completed():
    cookies_init=get_cookie()
    while True:
        response = requests.get(
            "https://tms48.nepsetms.com.np/tmsapi/orderTradeApi/tradebook-v2",
            cookies=cookies_init,
            headers=get_headers(),
        )
        if response.status_code == 200:
            df_trade_book = pd.DataFrame(response.json())
            df_trade_book['buyOrSell'] = df_trade_book['buyOrSell'].replace({1: 'BUY', 2: 'SELL'})
            df_trade_book['activeStatus'] = "COMPLETED"
            show_message(f"Fetched order book 'COMPLETED'.", color='green')
            return df_trade_book

        else:
            # login_tms()
            cookies, headers = refresh_token()
            cookies_init = cookies



def fetch_order_book_open():
    cookies_init=get_cookie()
    while True:
        response = requests.get(
            'https://tms48.nepsetms.com.np/tmsapi/orderTradeApi/orderbook-v2?&activeStatus=CANCELLED&activeStatus=REJECTED&activeStatus=TMS_REJECTED&activeStatus=PARTIALLY_CANCELLED&activeStatus=MODIFIED_CANCELLED&activeStatus=OPEN&activeStatus=PARTIALLY_TRADED&activeStatus=PENDING&activeStatus=MODIFIED&',
            cookies=cookies_init,
            headers=get_headers(),
        )

        if response.status_code == 200:
                df_trade_book = pd.DataFrame(response.json())
                df_trade_book['buyOrSell'] = df_trade_book['buyOrSell'].replace({1: 'BUY', 2: 'SELL'})
                show_message(f"Fetched order book 'OPEN'.", color='green')
                return df_trade_book
        else:
            # login_tms()
            cookies, headers = refresh_token()
            cookies_init = cookies



def merge_and_clean_order_book(open_df:pd.DataFrame, completed_df:pd.DataFrame):
    # Step 1: Compute average tradePrice per clientMemberCode + symbol in completed file
    avg_prices = (
        completed_df.groupby(["clientMemberCode", "symbol"])["tradePrice"]
        .mean()
        .reset_index()
        .rename(columns={"tradePrice": "avgOrderPrice"})
    )

    # Step 2: Merge avg prices into open_df
    merged = open_df.merge(avg_prices, on=["clientMemberCode", "symbol"], how="left")

    # Step 3: Replace orderPrice = 0.00 with avgOrderPrice (if available)
    merged["orderPrice"] = merged.apply(
        lambda row: row["avgOrderPrice"] if row["orderPrice"] == 0 and pd.notnull(row["avgOrderPrice"]) else row["orderPrice"],
        axis=1
    )

    # Step 4: Round the entire column to 2 decimals
    merged["orderPrice"] = merged["orderPrice"].round(2)

    # Step 5: Drop helper column
    merged = merged.drop(columns=["avgOrderPrice"])

    open_df = merged

    # Mapping dictionary: completed_df column → open_df column
    column_mapping = {
        "id": "id",
        "clientMemberCode": "clientMemberCode",
        "symbol": "symbol",
        "securityName": "securityName",
        "tradeTime": "orderTime",
        "exchangeOrderId": "exchangeOrderId",
        "buyOrSell": "buyOrSell",
        "tradePrice": "orderPrice",
        "tradedQuantity": "orderQuantity",
        "displayName": "displayName",
        "activeStatus": "activeStatus",
    }

    # Rename completed_df columns
    completed_df = completed_df.rename(columns=column_mapping)

    # Keep only the mapped columns that exist in completed_df
    available_cols = [col for col in column_mapping.values() if col in completed_df.columns]
    completed_df = completed_df[available_cols]

    # Step 3: Concatenate row-wise (append)
    combined_df = pd.concat([open_df, completed_df], ignore_index=True)
    combined_df.drop(columns=['id', 'exchangeOrderId', 'displayActiveStatus', 'orderPlacedBy', 'displayName', 'securityName'], inplace=True)
    combined_df['amount'] = combined_df['orderQuantity'].astype(float) * combined_df['orderPrice'].astype(float)  
    combined_df.loc[combined_df['activeStatus'] == "COMPLETED", 'totalTradedQuantity'] = combined_df['orderQuantity']

    # combined_df.to_excel(r"D:\Trishakti\Projects\RPA\track_stock_price\open_and_completed.xlsx", index=False)
    combined_df = extract_rm_in_order_book(combined_df)
    combined_df['updatedTime'] = datetime.now().strftime("%Y-%m-%d %I:%H:%S %p")
    combined_df = combined_df.rename(columns={'clientMemberCode':'clientCode', 'rmName':'bro'})
    return combined_df


def fetch_order_book():
    open_df = fetch_order_book_open()
    completed_df = fetch_order_book_completed()
    df = merge_and_clean_order_book(open_df=open_df, completed_df=completed_df)
    push_to_order_book_db(df=df)
    

def fetch_trade_book():
    cookies_init = get_cookie()
    while True:
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
    return summary

