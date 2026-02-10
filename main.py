
import os
os.system("")
import warnings
warnings.filterwarnings("ignore", message="Thread 'MainThread': missing ScriptRunContext")
import logging
logging.getLogger("streamlit.runtime.scriptrunner_utils").setLevel(logging.ERROR)

from calculation.wacc_calculator import WaccCalculator
from extractor.holding_summary_with_bro import BroExtractor
from calculation.client_summary_calc import ClientSummaryExtractor
from calculation.manager_summary_calc import ManagerSummaryExtractor

from extractor.ledger_balance_extractor import LedgerBalanceExtractor
from extractor.meroshare_bot import MeroshareBot
from utils import helper
import json
from datetime import datetime
import requests
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
from config import config
from db import db

class NepalStockExchange:
    def __init__(self):
        self.url = "https://nepalstock.com.np/live-market"
        self.driver = None

    def setup_chrome(self):
        chrome_options = Options()
        chrome_options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--start-maximized")
        return chrome_options

    def execute_browser(self):
         # Launch Chrome
        self.driver = webdriver.Chrome(options=self.setup_chrome())
        self.driver.get(self.url)
        time.sleep(3)  # wait for table to load

    def start_live_tracking(self):
        """
        interval: seconds to wait before fetching the table again
        """
        try:
            # while True:
            # Get table HTML snapshot
            table_html = self.driver.find_element(By.XPATH, "//table").get_attribute("outerHTML")

            # Parse with BeautifulSoup
            soup = BeautifulSoup(table_html, "html.parser")
            header_row = soup.select("tr")[0]
            headers = [th.text.strip() for th in header_row.find_all("th")]

            # Dynamically map Symbol and LTP columns
            col_map = {name: idx for idx, name in enumerate(headers) if name in ["Symbol", "LTP"]}

            # Extract rows
            rows = soup.select("tr")[1:]  # skip header
            data_dict = {}
            for row in rows:
                cols = row.find_all("td")
                symbol = cols[col_map["Symbol"]].text.strip().replace('"', "'").replace("\n", "").replace("\t", "")
                ltp_text = cols[col_map["LTP"]].text.strip().replace(",", "").replace("\n", "").replace("\t", "")

                try:
                    ltp = float(ltp_text)
                except ValueError:
                    ltp = 0.0  # fallback if parsing fails
                data_dict[symbol] = ltp

            # print(data_dict)
            # print("\n")
            print("[+++++++++++] JUST FETCHED")
            # print(json.dumps(data_dict, indent=4))
            return data_dict

        except KeyboardInterrupt:
            helper.show_message("[INFO] Live tracking stopped by user.", "red")
 
    def quit_driver(self):
        self.driver.quit()

    
    # 🧾 Update live_price and valuation in DB
    # def update_prices(self, live_data:dict):
    #     if not live_data:
    #         helper.show_message("No live data fetched.", color='red')
    #         return

    #     conn = db.get_connection()
    #     cur = conn.cursor()

    #     cur.execute("SELECT DISTINCT script FROM holdings;")
    #     scripts = [row[0] for row in cur.fetchall()]
        
    #     updated_count = 0
    #     for script in scripts:
    #         if script in live_data:
    #             ltp = live_data[script]
    #             cur.execute("""
    #                     UPDATE holdings
    #                     SET ltp = %s,
    #                         "marketValue" = "currentBalance" * %s,
    #                         "lastUpdated" = %s
    #                     WHERE UPPER(TRIM(script)) = %s;
    #                 """, (ltp, ltp, datetime.now(), script.strip().upper()))

    #             updated_count += 1

    #     conn.commit()
    #     cur.close()
    #     conn.close()
    #     helper.show_message(f"Updated {updated_count} scripts at {datetime.now()}", color='green')





    def update_prices(self, live_data: dict):
        if not live_data:
            helper.show_message("No live data fetched.", color='red')
            return

        conn = db.get_connection()
        cur = conn.cursor()

        updated_count = 0

        for symbol, ltp in live_data.items():
            normalized_symbol = symbol.strip().upper()

            # Debug: check old vs new
            cur.execute("SELECT ltp FROM holdings WHERE UPPER(TRIM(script)) = %s;", (normalized_symbol,))
            old_val = cur.fetchone()
            if old_val is not None and old_val[0] is not None:
                print(f"{normalized_symbol}: old={old_val[0]}, new={ltp}")
                if old_val[0] != ltp:
                    helper.show_message(f"{normalized_symbol}: old={old_val[0]}, new={ltp}", color="red")
            
            cur.execute("""
                UPDATE holdings
                SET ltp = %s,
                    "marketValue" = "currentBalance" * %s,
                    "lastUpdated" = %s
                WHERE UPPER(TRIM(script)) = %s;
            """, (ltp, ltp, datetime.now(), normalized_symbol))

            updated_count += cur.rowcount
            # print(f"Updated script : {normalized_symbol}, rowcount={cur.rowcount}")

        conn.commit()
        cur.close()
        conn.close()

        helper.show_message(
            f"Updated {updated_count} rows at {datetime.now()}",
            color='green'
        )


  

    


    def dummy_market_data(self):
        live_data:dict = None
        with open("market_data.txt" , 'r') as file:
            live_data = file.read()
            live_data = json.loads(str(live_data).replace("'", '"'))
            helper.show_message("[+] Live data fetched successfully. [www.nepalstock.com.np]")
            return live_data

    def start_live_bot(self):
        # flag = MeroshareBot().process_data()
        # if flag == 0:
        #     helper.show_message("Exiting live bot due to no Meroshare accounts.", color='red')
        #     return
        # LedgerBalanceExtractor().extract_balance()  
        # Target Time
        # target_time = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        self.execute_browser()
        helper.show_message("[INFO] Starting live tracking of Symbol + LTP...", "green")
        print("\n")
        first_run = 0
        while True:
            now = datetime.now()
            # if now >= target_time:
                # print("\n\n[-] It's 3 PM! Exiting LIVE DP HOLDING PROGRAM.")
                # break


            live_data = self.start_live_tracking()
            # live_data = self.dummy_market_data()
            helper.show_message("Live data fetched successfully. [www.nepalstock.com.np]", "green")
            
            self.update_prices(live_data=live_data)

            time.sleep(0.5)
            BroExtractor().extract_and_update_bro()
            WaccCalculator().calculate(live_market_data=live_data, run_flag=first_run)
            ClientSummaryExtractor().extract_client_summary()
            ManagerSummaryExtractor().extract_manager_summary()
            helper.show_message(f"[INFO] Waiting for {config.REFRESH_TIME_IN_SECONDS} seconds . . . . .", color='yellow')
            time.sleep(config.REFRESH_TIME_IN_SECONDS)
            # first_run = 1


if __name__ == "__main__":
    NepalStockExchange().start_live_bot()





