import json
from wacc_calculator import WaccCalculator
import subprocess
from test_cases.niu_live_updater import LiveUpdater
import uuid
import pandas as pd
from time import sleep
from api.capital import CapitalId
from config import config
import pandas as pd
import requests
from sqlalchemy import create_engine


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
            'clientId': client_id,
            'username': username,
            'password': password,
        }
        return json_data
    

    def get_stock_holding(self, client_dp_code:str, username:str):
        print(f" > Fetching stock holdings for DP Code: {client_dp_code}")
        boid, name = self.get_boid_and_name()
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Authorization': self.authorization_token,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Origin': 'https://meroshare.cdsc.com.np',
            'Pragma': 'no-cache',
            'Referer': 'https://meroshare.cdsc.com.np/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        json_data = {
            'sortBy': 'CCY_SHORT_NAME',
            'demat': [
                boid
            ],
            'clientCode': client_dp_code,
            'page': 1,
            'size': 200,
            'sortAsc': True,
        }

        response = requests.post('https://webbackend.cdsc.com.np/api/meroShareView/myShare/', headers=headers, json=json_data)
        if response.status_code == 200:
            try:
                holdings = response.json()['meroShareDematShare']
                for h in holdings:
                    h['name'] = name
                    h['boid'] = boid
                    h['dp'] = client_dp_code
                    h['username'] = username
                print(f" > Total holdings fetched: {len(holdings)}")
                return holdings
            except KeyError:
                return []


    def get_boid_and_name(self):
        sleep(1)
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Authorization': self.authorization_token,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Origin': 'https://meroshare.cdsc.com.np',
            'Pragma': 'no-cache',
            'Referer': 'https://meroshare.cdsc.com.np/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }

        response = requests.get('https://webbackend.cdsc.com.np/api/meroShare/ownDetail/', headers=headers)
        if response.status_code == 200:
            try:
                return response.json().get('demat', ''), response.json().get('name', '')
            except KeyError:
                return '', ''
            

    def push_data_to_db(self, df:pd.DataFrame):
        engine = create_engine(f"postgresql+psycopg2://{config.postgresql_config['db_user']}:{config.postgresql_config['db_password']}@{config.postgresql_config['db_host']}:{config.postgresql_config['db_port']}/{config.postgresql_config['db_name']}")
        df.to_sql("holdings", engine, if_exists="replace", index=False)
        print("✅ Data successfully dumped into DB.")

    
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
            print(" -> Total Scripts = " +str(len(response.json())))
            return response.json()

    def get_wacc(self, holdings):
        # print(json.dumps(holdings, indent=4))
        list_of_scripts = self.get_all_scripts()
        print("\n\n")
        sleep(1)
        average_buy_rate = 0
        total_cost = 0
        total_qty = 0
        for index, script in enumerate(list_of_scripts):
            print(f"[{index+1}/{len(list_of_scripts)}] Processing {script}")
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
                print(data)
                print("\n")
                try:
                    wacc = data["waccSummaryResponse"]
                    if len(wacc) > 0:
                        average_buy_rate = wacc['averageBuyRate']
                        total_cost = wacc['totalCost']
                        total_qty = wacc['totalQuantity']
                except Exception:
                    print(response.text)
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
                        h['wacc_calculated__qty'] = total_qty
                        h['wacc_rate'] = average_buy_rate
                        h['total_cost_of_capital'] = total_cost
                        if has_pending_wacc:
                            h['pending_wacc_qty'] = pending_wacc_qty
                            h['pending_wacc_rate'] = pending_wacc_rate
                            h['pending_wacc_count'] = len(wacc_update_response)
                            h['pending_wacc'] = True
                            h['pending_wacc_source'] = sources
                            has_pending_wacc = False
                        else:
                            h['pending_wacc_qty'] = 0
                            h['pending_wacc_rate'] = 0
                            h['pending_wacc'] = False
                            h['pending_wacc_count'] = 0
                            h['pending_wacc_source'] = "N/A"

                sleep(2)
               
        return holdings

    def process_data(self):
        df_client_data = pd.read_excel(config.CLIENT_DATA_FILEPATH)
        df_client_data['PASSWORD_EXPIRED'] = None
        df_client_data['ACCOUNT_EXPIRED'] = None
        df_client_data['DEMAT_EXPIRED'] = None
        df_client_data['LOGIN_MESSAGE'] = None

        client_bot = CapitalId()

        for index, row in df_client_data.iterrows():
            dp_id = str(row['DP']) + "00"
            username = str(row['USERNAME'])
            password = str(row['PASSWORD'])
            client_id = client_bot.get_dp_id(dp_id)
            if client_id == 0:
                print(f"Client ID not found for DP ID: {dp_id}")
                continue
            
            json_data = self.get_json_data(client_id, username, password)
            print(f"[{index+1}] Authenticating for DP ID: {dp_id}, Username: {username}")
            response = requests.post('https://webbackend.cdsc.com.np/api/meroShare/auth/', headers=self.get_headers(), json=json_data)
            if response.status_code == 200:
                print(f" > Successfully authenticated for DP ID: {dp_id}")
                self.authorization_token = response.headers.get('Authorization', None)
                df_client_data.at[index, 'LOGIN_MESSAGE'] = response.json().get('message', '')
                df_client_data.at[index, 'PASSWORD_EXPIRED'] = response.json().get('passwordExpired', '')
                df_client_data.at[index, 'ACCOUNT_EXPIRED'] = response.json().get('accountExpired', '')
                df_client_data.at[index, 'DEMAT_EXPIRED'] = response.json().get('dematExpired', '')
                sleep(1)
                holdings = self.get_stock_holding(client_dp_code=dp_id, username=username)
                holdings = self.get_wacc(holdings=holdings)
                self.stock_holdings.extend(holdings)
                print("\n")
                sleep(3)

        df_client_data.to_excel(config.CLIENT_DATA_FILEPATH, index=False)


        df_holdings = pd.DataFrame(self.stock_holdings)
        
        df_holdings['live_price'] = None
        df_holdings['market_value'] = None
        df_holdings['last_updated'] = None


        df_holdings['id'] = [str(uuid.uuid4()) for _ in range(len(df_holdings))]
        desired_order = ['id', 'name', 'username', 'dp', 'boid'] + [col for col in df_holdings.columns if col not in ['id', 'name', 'username', 'dp', 'boid']]
        df_holdings = df_holdings[desired_order]
        df_holdings.to_excel(config.OUTPUT_CLIENT_DATA_FILEPATH, index=False)
        WaccCalculator().calculate()

        self.push_data_to_db(df=df_holdings)


if __name__ == "__main__":
    MeroshareBot().process_data()
    live_updater = LiveUpdater()
    has_url_opened = False
    while True:
        live_updater.update_prices()
        if not has_url_opened:
            subprocess.Popen(["streamlit", "run", "app.py"], cwd=config.PROJECT_PATH)
            has_url_opened = True
        print(f"Sleeping for 30 seconds . . . | has_url_opened={has_url_opened}")
        sleep(config._REFRESH_TIME_IN_SECONDS)
