import warnings
warnings.filterwarnings("ignore", message="Thread 'MainThread': missing ScriptRunContext")

from extractor.ledger_balance_extractor import LedgerBalanceExtractor
from extractor.meroshare_bot import MeroshareBot
from utils import helper
import json
from datetime import datetime
import requests
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

class NepalStockExchange:
    def __init__(self):
        self.refresh_time_in_seconds = 10
        self.url = "https://nepalstock.com.np/live-market"
        self.auth_token = None
        self.driver = None
        

    def headers(self, authorization:str):
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Authorization': authorization,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Referer': 'https://nepalstock.com.np/live-market',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        return headers

    def setup_chrome(self):
        # --- Chrome Options ---
        chrome_options = Options()
        # chrome_options.add_argument('--incognito')
        # chrome_options.add_argument('--headless')
        chrome_options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
        return chrome_options
    
    def execute_browser(self):
        driver = webdriver.Chrome(options=self.setup_chrome())
        self.driver = driver
        target_url = self.url
        print("Opening page…")
        driver.get(target_url)

    def extract_auth_token(self):
        time.sleep(1)
        for req in self.driver.requests:
            if req.response:
                if "api/nots" in req.url:
                    if 'Authorization' in req.headers:
                        self.auth_token = req.headers['Authorization']
                        if self.auth_token:
                            print(f"Token found: " + self.auth_token)
                            break
    

    def fetch_live_market_data(self):
        self.execute_browser()
        self.extract_auth_token()
        response = requests.get('https://nepalstock.com.np/api/nots/lives-market', headers=self.headers(authorization=self.auth_token), verify=False)
        if response.status_code != 200:
            print("Failed:", response.status_code)
            return None

        data = response.json()

        symbol_ltp_dict = {item["symbol"]: item["lastTradedPrice"] for item in data}
        return symbol_ltp_dict

    def quit_driver(self):
        self.driver.quit()

     # 🧾 Update live_price and valuation in DB
    
    
    def update_prices(self, live_data:dict):
        if not live_data:
            print("No live data fetched.")
            return

        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT DISTINCT script FROM holdings;")
        scripts = [row[0] for row in cur.fetchall()]

        updated_count = 0
        for script in scripts:
            if script in live_data:
                ltp = live_data[script]
                cur.execute("""
                    UPDATE holdings
                    SET ltp = %s,
                        marketValue = "currentBalance" * %s,
                        lastUpdated = %s
                    WHERE script = %s;
                """, (ltp, ltp, datetime.now(), script))
                updated_count += 1

        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Updated {updated_count} scripts at {datetime.now()}")

    def start_bot(self):
        self.execute_browser()
        print("\n\n[+] Ready to fetch latest data.")
        self.extract_auth_token()
        data = self.fetch_live_market_data()
        return data
    

    def start_live_bot(self):
        from calculation.wacc_calculator import WaccCalculator
        from extractor.holding_summary_with_bro import BroExtractor
        from calculation.client_summary_calc import ClientSummaryExtractor
        from calculation.manager_summary_calc import ManagerSummaryExtractor



        # MeroshareBot().process_data()
        # LedgerBalanceExtractor().extract_balance()  
        # Target Time
        # target_time = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)

        while True:
            now = datetime.now()
            # if now >= target_time:
                # print("\n\n[-] It's 3 PM! Exiting LIVE DP HOLDING PROGRAM.")
                # break




            BroExtractor().extract_and_update_bro()
            helper.show_message("[2] Ready to fetch latest data.")
            # live_data = self.fetch_live_market_data()
            live_data:dict = None
            with open("market_data.txt" , 'r') as file:
                live_data = file.read()
                live_data = json.loads(str(live_data).replace("'", '"'))
                helper.show_message("[3] Live data fetched successfully. [www.nepalstock.com.np]")

            
            # print(live_data)

            # time.sleep(100000)
            WaccCalculator().calculate(live_market_data=live_data)
            # time.sleep(1000000)

            ClientSummaryExtractor().extract_client_summary()
            ManagerSummaryExtractor().extract_manager_summary()
            helper.show_message("[INFO] Waiting for 15 seconds . . . . .", color='yellow')
            time.sleep(self.refresh_time_in_seconds)

            # self.driver.refresh()


if __name__ == "__main__":
    NepalStockExchange().start_live_bot()





