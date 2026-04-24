# from utils.mailer import send_email
# from datetime import datetime, timedelta
# import pandas as pd
# import requests
# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# from seleniumwire import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import time
# import json
# from utils.helper import show_message, show_message_box, get_holding_engine
# from sqlalchemy import create_engine



# def get_authorization():
#     global driver
#     options = Options()
#     options.add_argument('--incognito')
#     options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
#     options.add_argument('--disable-gpu')
#     driver = webdriver.Chrome(options=options)
#     driver.maximize_window()
#     driver.get("https://nepalstock.com.np/trading-average")
#     # show_message_box(message="Plese change date and click ok?")
#     time.sleep(3)
#     try:
#         WebDriverWait(driver, 10).until(
#             EC.presence_of_element_located((By.XPATH, "//th[normalize-space()='Symbol']"))
#         )
#         show_message("NepseStockExchange Table loaded successfully.")
#     except Exception as e:
#         show_message(f"❌ Table not found: {e}", 'red')
#         driver.quit()
#         exit()

#     auth_token = None
#     for request in driver.requests:
#         if request.response and "trading-average?nDays=120" in request.url:
#             headers = request.headers

#             if "Authorization" in headers:
#                 auth_token = headers["Authorization"]
#             break

#     # driver.quit()
#     return auth_token

# def fetch_trading_average_price(table_name:str = "average_price"):
#     show_message("Fetching today's stock price from nepse stock exchange. Please wait . . .", 'yellow')
#     authorization = get_authorization()
        
#     if authorization:
#         headers = {
#             'Accept': 'application/json, text/plain, */*',
#             'Accept-Language': 'en-US,en;q=0.9',
#             'Authorization': authorization,
#             'Cache-Control': 'no-cache',
#             'Connection': 'keep-alive',
#             'Pragma': 'no-cache',
#             'Referer': 'https://nepalstock.com.np/trading-average',
#             'Sec-Fetch-Dest': 'empty',
#             'Sec-Fetch-Mode': 'cors',
#             'Sec-Fetch-Site': 'same-origin',
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
#             'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
#             'sec-ch-ua-mobile': '?0',
#             'sec-ch-ua-platform': '"Windows"',
#         }

#         # today = datetime.today()
#         today = datetime.today().strftime("%Y-%m-%d")
#         # weekday(): Monday=0, Tuesday=1, ..., Sunday=6
#         # days_back = (today.weekday() - 3) % 7  # Thursday = 3
#         # last_thursday = today - timedelta(days=days_back if days_back != 0 else 7)
#         # last_thursday_date = last_thursday.strftime("%Y-%m-%d")

              
#         params = {
#             'nDays': '120',
#             'businessDate': today,
            
#         }

#         response = requests.get(
#             'https://nepalstock.com.np/api/nots/nepse-data/trading-average',
#             params=params,
#             headers=headers,
#             verify=False  # ← disables SSL cert check
#         )


#         if response.status_code == 200:
#             json_response = response.json()
#             df = pd.DataFrame(json_response)
#             df['updated_at'] = pd.Timestamp.now()
#             engine = create_engine(get_holding_engine())
#             # Dump DataFrame to SQL table
#             df.to_sql(name=table_name,con=engine,if_exists="replace", index=False)
#             show_message(f"Average Price from NepalStockExchange dumped to table {table_name}.", color="green")
#         else:
#             show_message(f"NepalStoclExchange Request failed:" + response.text, 'red')
#     else:
#         show_message("NepalStockExchange Authorization token not found.", 'red')


# if __name__ == "__main__":
#     fetch_trading_average_price()
#     # send_email("prabin.trishakti@gmail.com")
    
#     # from db import db
#     # rows = db.get_table_average_price() 
#     # df_avp = pd.DataFrame(rows, columns=["SYMBOL", "AVERAGE_PRICE"])
#     # print(df_avp)











from playwright.sync_api import sync_playwright
import requests
from sqlalchemy import create_engine
import urllib3
import pandas as pd
from datetime import datetime
import json

from utils.helper import get_holding_engine

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def fetch_today_price():
    """
    1. Open browser → page fires POST to today-price
    2. Sniff auth token + dynamic id from that POST payload
    3. Replay POST with size=500 & today's date → all stocks in ONE request
    4. Save CSV
    5. ONLY THEN close the browser
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--incognito", "--disable-gpu"],
        )
        context = browser.new_context()
        page    = context.new_page()

        auth_token = None
        dynamic_id = None

        # ── Sniff auth token + dynamic id from the page's own POST ──────────
        def handle_request(request):
            nonlocal auth_token, dynamic_id

            if "today-price" not in request.url:
                return

            if not auth_token:
                auth = (
                    request.headers.get("authorization")
                    or request.headers.get("Authorization")
                )
                if auth:
                    auth_token = auth
                    print(f"✅  Auth token  : {auth_token[:50]}…")

            if request.method == "POST" and not dynamic_id:
                try:
                    body = request.post_data
                    if body:
                        payload = json.loads(body)
                        if "id" in payload:
                            dynamic_id = payload["id"]
                            print(f"✅  Dynamic ID  : {dynamic_id}")
                except Exception as e:
                    print(f"⚠️  Could not parse POST body: {e}")

        page.on("request", handle_request)
        # ────────────────────────────────────────────────────────────────────

        print("🌐  Loading https://nepalstock.com.np/today-price …")
        page.goto(
            "https://nepalstock.com.np/today-price",
            wait_until="networkidle",
            timeout=60_000,
        )

        if not auth_token:
            print("❌  Authorization token not found. Closing browser.")
            browser.close()
            return

        if not dynamic_id:
            print("❌  Dynamic ID not found. Closing browser.")
            browser.close()
            return

        # ── Dynamic today's date ─────────────────────────────────────────────
        # today = "2026-04-22"
        today = datetime.today().strftime("%Y-%m-%d")

        # ── Browser still OPEN → token still valid ───────────────────────────
        print(f"\n🔑  Fetching all stocks for {today} with id={dynamic_id} …")

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": auth_token,
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": "https://nepalstock.com.np",
            "Referer": "https://nepalstock.com.np/today-price",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/146.0.0.0 Safari/537.36"
            ),
            "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }

        response = requests.post(
            f"https://nepalstock.com.np/api/nots/nepse-data/today-price?&size=500&businessDate={today}",
            headers=headers,
            json={"id": dynamic_id},   # ← dynamic id captured from browser
            verify=False,
        )
        
        print(response.status_code)

        if response.status_code != 200:
            print(f"❌  Request failed [{response.status_code}]: {response.text}")
            browser.close()
            return

        json_response = response.json()

        # ── Parse response["content"] ─────────────────────────────────────────
        items = json_response.get("content", [])

        if not items:
            print("⚠️  No content found. Raw response:")
            print(json_response)
            browser.close()
            return

        records = [
            {
                "symbol":     stock["symbol"],
                "closePrice": stock["closePrice"],
            }
            for stock in items
        ]

        df = pd.DataFrame(records)
        df["updated_at"]   = datetime.now().strftime("%Y-%m-%d %I:%M:%S")
        engine = create_engine(get_holding_engine())
        # Dump DataFrame to SQL table
        df.to_sql(
            name="average_price",
            con=engine,
            if_exists="replace",   # options: 'fail', 'replace', 'append'
            index=False            # don’t write DataFrame index as a column
        )
        # ── CSV saved → NOW close the browser ────────────────────────────────
        print("\n🔒  Dumped to db saved successfully. Closing browser now.")
        browser.close()


if __name__ == "__main__":
    fetch_today_price()