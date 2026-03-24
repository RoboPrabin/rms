import uuid

from utils.mailer import send_email
from datetime import datetime, timedelta
import pandas as pd
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
from utils.helper import show_message, show_message_box, get_holding_engine
from sqlalchemy import create_engine



def get_authorization(current_year:str):
    global driver
    options = Options()
    options.add_argument('--incognito')
    options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    driver.get("https://nepalstock.com.np/holiday-listing")
    # show_message_box(message="Plese change date and click ok?")
    time.sleep(3)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//th[text()='Holiday Date']"))
        )
        show_message("NepseStockExchange Holiday table loaded successfully.")
    except Exception as e:
        show_message(f"❌ Table not found: {e}", 'red')
        driver.quit()
        exit()

    auth_token = None
    for request in driver.requests:
        if request.response and f"list?year={current_year}" in request.url:
            headers = request.headers

            if "Authorization" in headers:
                auth_token = headers["Authorization"]
            break

    # driver.quit()
    return auth_token

def fetch_holidays(current_year:str, table_name:str = "holidays"):
    show_message("Fetching today's stock price from nepse stock exchange. Please wait . . .", 'yellow')
    authorization = get_authorization(current_year)
    if authorization:
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Authorization': authorization,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Referer': 'https://nepalstock.com.np/trading-average',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }


              
        params = {
            'year': current_year,
        }

        response = requests.get('https://nepalstock.com.np/api/nots/holiday/list', params=params, headers=headers, verify=False)


        if response.status_code == 200:
            json_response = response.json()
            df = pd.DataFrame(json_response)
            df['created_by'] = 'SYSTEM'
            df['created_at'] = datetime.now()
            df['id'] = [str(uuid.uuid4()) for _ in range(len(df))]
            df.rename(columns={'holidayDate':'holiday_date', 'holidayDescription':'holiday_description'}, inplace=True)
            df.drop(columns=['instrumentTypeId', 'modifiedBy', 'modifiedDate', 'activeStatus'], inplace=True)
            df.to_sql(name=table_name, con=get_holding_engine(),if_exists="replace", index=False)
            show_message(f"Holidays from NepalStockExchange dumped to table {table_name}.", color="green")
        else:
            show_message(f"NepalStoclExchange Request failed:" + response.text, 'red')
    else:
        show_message("NepalStockExchange Authorization token not found.", 'red')


if __name__ == "__main__":
    current_year = datetime.now().year
    show_message(message=f"Current Year: {current_year}", color="yellow")
    fetch_holidays(current_year=current_year)

  