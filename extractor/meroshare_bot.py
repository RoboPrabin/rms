import warnings

from utils import helper
warnings.filterwarnings("ignore", category=UserWarning, module='streamlit')


from extractor.ledger_balance_extractor import LedgerBalanceExtractor
from test_cases.niu_ltp_extractor import LtpExtractor
from live_db_updater.db_updater import DBUpdater
import subprocess
import uuid
import pandas as pd
from time import sleep
from api.capital import CapitalId
from config import config
import pandas as pd
import requests
# from wacc_calculator import WaccCalculator
from db import db

class MeroshareBot:
    def __init__(self):
        self.authorization_token = None
        self.stock_holdings = []
        self.total_holdings_count = 0
        self.demat = None
        pass

    def get_headers(self, authorization_token="null"):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": authorization_token,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": "https://meroshare.cdsc.com.np",
            "Pragma": "no-cache",
            "Referer": "https://meroshare.cdsc.com.np/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
        return headers

    def get_json_data(self, client_id, username, password):
        json_data = {
            "clientId": client_id,
            "username": username,
            "password": password,
        }
        return json_data

    def get_stock_holding(self, client_dp_code: str, username: str):
        helper.show_message(f" > Fetching stock holdings.")
        while True:
            try:
                boid, name = self.get_boid_and_name()
                self.demat = boid
                json_data = {
                    "sortBy": "CCY_SHORT_NAME",
                    "demat": [boid],
                    "clientCode": client_dp_code,
                    "page": 1,
                    "size": 200,
                    "sortAsc": True,
                }

                response = requests.post(
                    "https://webbackend.cdsc.com.np/api/meroShareView/myShare/",
                    headers=self.get_headers(authorization_token=self.authorization_token),
                    json=json_data,
                )
                if response.status_code == 200:
                    try:
                        holdings = response.json()["meroShareDematShare"]
                        for h in holdings:
                            h["name"] = name
                            h["boid"] = boid
                            h["dp"] = client_dp_code
                            h["username"] = username
                        helper.show_message(f" > Total holdings: {len(holdings)}")
                        return holdings
                    except KeyError:
                        return []
            except Exception as e:
                helper.show_message(f" > Error, Retrying . . . .", color='red')
                sleep(3)

    def get_boid_and_name(self):
        sleep(1)
        response = requests.get(
            "https://webbackend.cdsc.com.np/api/meroShare/ownDetail/",
            headers=self.get_headers(authorization_token=self.authorization_token),
        )
        if response.status_code == 200:
            try:
                return response.json().get("demat", ""), response.json().get("name", "")
            except KeyError:
                return "", ""

    def get_all_scripts(self):
        json_data = {
            "isFilterByAllScript": True,
        }

        response = requests.post(
            "https://webbackend.cdsc.com.np/api/myPurchase/share/",
            headers=self.get_headers(authorization_token=self.authorization_token),
            json=json_data,
        )
        if response.status_code == 200:
            return response.json()

    def get_wacc(self, holdings):
        # print(json.dumps(holdings, indent=4))
        list_of_scripts = self.get_all_scripts()
        # print("\n\n")
        sleep(1)
        average_buy_rate = 0
        total_cost = 0
        total_qty = 0
        for index, script in enumerate(list_of_scripts):
            while True:
                try:
                    helper.show_message(f" > [{index+1}/{len(list_of_scripts)}] Processing {script}")
                    json_data = {"demat": self.demat, "scrip": script}

                    response = requests.post(
                        "https://webbackend.cdsc.com.np/api/myPurchase/search/wacc/",
                        headers=self.get_headers(self.authorization_token),
                        json=json_data,
                        timeout=10,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        # print(json.dumps(data, indent=4))
                        # print("\n")
                        try:
                            wacc = data["waccSummaryResponse"]
                            if len(wacc) > 0:
                                average_buy_rate = wacc['averageBuyRate']
                                total_cost = wacc['totalCost']
                                total_qty = wacc['totalQuantity']
                        except Exception:
                            pass

                        has_pending_wacc = False
                        if len(response.json()['waccUpdateResponse']) > 0:
                            wacc_update_response = response.json()['waccUpdateResponse']
                            pending_wacc_rate = ", ".join(str(item["rate"]) for item in data["waccUpdateResponse"])
                            pending_wacc_qty = ", ".join(str(item["transactionQuantity"]) for item in data["waccUpdateResponse"])
                            # pending_wacc_rate = max(item["rate"] for item in wacc_update_response)
                            sources = ", ".join(item["purchaseSource"] for item in data["waccUpdateResponse"])
                            has_pending_wacc = True

                        for h in holdings:
                            if h['script'] == script:
                                h['waccCalculatedQuantity'] = total_qty
                                h['waccRate'] = average_buy_rate
                                h['totalCostOfCapital'] = total_cost
                                if has_pending_wacc:
                                    h['pendingWaccQuantity'] = pending_wacc_qty
                                    h['pendingWaccRate'] = pending_wacc_rate
                                    h['pendingWaccCount'] = len(wacc_update_response)
                                    h['pendingWacc'] = True
                                    h['pendingWaccSource'] = sources
                                    has_pending_wacc = False
                                else:
                                    h['pendingWaccQuantity'] = 0
                                    h['pendingWaccRate'] = 0
                                    h['pendingWaccCount'] = 0
                                    h['pendingWacc'] = False
                                    h['pendingWaccSource'] = "N/A"

                        sleep(2)
                        break
                except Exception as e:
                    helper.show_message(f" > Error, Retrying . . . .", color='red')
                    sleep(3)

               
        return holdings

    def process_data(self):
        df_client_data = db.get_meroshare_accounts()
        if len(df_client_data) == 0:
            helper.show_message("No Meroshare accounts found to process.", color='red')
            return 0
        # print(df_client_data)
        client_bot = CapitalId()
        helper.show_message(f"Total Meroshare accounts to process: {len(df_client_data)}", color='green')
        print("\n\n")
        for index, row in df_client_data.iterrows():
            while True:
                try:
                    dp_id = str(row["dp"]) + "00"
                    username = str(row["username"])
                    password = str(row["password"])
                    client_name = str(row['clientName'])
                    client_id = client_bot.get_dp_id(dp_id)
                    if client_id == 0:
                        helper.show_message(f"Client ID not found for DP ID: {dp_id}", color='red')
                        continue

                    json_data = self.get_json_data(client_id, username, password)
                    helper.show_message(f"[{index+1}] Authenticating for: {client_name.upper()} | Username: {username}", color='cyan')

                    response = requests.post(
                        "https://webbackend.cdsc.com.np/api/meroShare/auth/",
                        headers=self.get_headers(),
                        json=json_data,
                    )
                    if response.status_code == 200:
                        helper.show_message(f" > Successfully authenticated.", color='green')
                        self.authorization_token = response.headers.get("Authorization", None)
                        df_client_data.at[index, "login_message"] = response.json().get(
                            "message", ""
                        )
                        df_client_data.at[index, "password_expired"] = response.json().get(
                            "passwordExpired", ""
                        )
                        df_client_data.at[index, "account_expired"] = response.json().get(
                            "accountExpired", ""
                        )
                        df_client_data.at[index, "demat_expired"] = response.json().get(
                            "dematExpired", ""
                        )
                        sleep(1)
                        holdings = self.get_stock_holding(
                            client_dp_code=dp_id, username=username
                        )
                        holdings = self.get_wacc(holdings=holdings)
                        self.stock_holdings.extend(holdings)
                        print("\n")
                        sleep(3)
                    else:
                        df_client_data.at[index, "login_message"] = f"Failed: {response.json().get('message', '')}"
                        helper.show_message(f" > Authentication failed for {client_name}. Status Code: {response.status_code} | {dict(response.json()).get('message', '')}", color='red')
                        print("\n")
                        sleep(2)
                    break
                except Exception as e:
                    helper.show_message(f"❌ Error occurred for {client_name}: {e}", color='red')
                    helper.show_message(f"Retrying after 3 seconds.", color='yellow')
                    print("\n")
                    sleep(3)

        df_client_data.to_excel(config.CLIENT_DATA_FILEPATH, index=False)

        df_holdings = pd.DataFrame(self.stock_holdings)

        df_holdings["id"] = [str(uuid.uuid4()) for _ in range(len(df_holdings))]
        desired_order = ["id", "name", "username", "dp", "boid"] + [
            col
            for col in df_holdings.columns
            if col not in ["id", "name", "username", "dp", "boid"]
        ]
        df_holdings = df_holdings[desired_order]
        while True:
            try:
                df_holdings.to_excel(config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL, index=False)
                # helper.show_message(f"Holdings data written at {config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL}")
                db.update_meroshare_accounts_status(df_client_data=df_client_data)
                break
            except PermissionError:
                helper.show_message(f"[Alert] Please close the file ASAP. Thank you ! !", color='red')
                sleep(3)
        
        # WaccCalculator().calculate()


    
# if __name__ == "__main__":
#     # MeroshareBot().process_data()
#     LedgerBalanceExtractor().extract_balance()
#     from live_db_updater.niu_nepal_stock_exchange import NepalStockExchange

#     live_data = NepalStockExchange().start_live_bot()
#     print(live_data)
#     print("\n\n\n\n")

    # live_data = LtpExtractor().fetch_live_market()
    # from wacc_calculator import WaccCalculator

    # WaccCalculator().start_calulation(live_data=live_data)

    # from holding_summary_with_bro import BroExtractor
    # BroExtractor().extract_bro()
    # DBUpdater().push_data_to_db()

    # from client_summary_calc import ClientSummaryExtractor
    # ClientSummaryExtractor().extract_client_summary()

    # from manager_summary_calc import ManagerSummaryExtractor
    # ManagerSummaryExtractor().extract_manager_summary()
    


    # subprocess.Popen(["streamlit", "run", "streamlit\\login.py"], cwd=config.PROJECT_PATH)

































    # live_updater = LiveUpdater()
    # # wacc_calc = WaccCalculator()
    # has_url_opened = False
    # while True:
    #     live_updater.update_prices()
    #     if not has_url_opened:
    #         subprocess.Popen(["streamlit", "run", "app.py"], cwd=config.PROJECT_PATH)
    #         has_url_opened = True
    #     print(f"Sleeping for 30 seconds . . . | has_url_opened={has_url_opened}")
    #     sleep(config._REFRESH_TIME_IN_SECONDS)
