import re
from time import sleep
import pandas as pd
import requests
from api.dg.shared_api_dg import get_headers
from config import config
from ui.login_dg import login_dg

class LedgerBalanceExtractor:
    def __init__(self):
        pass
        
    def __get_ledger_balance(self, ac_code: str):
        params = {
            "acCode": ac_code,
            "dateFrom": "2025-07-17",
            "dateTo": "2026-07-16",
            "branch": "1",
            "fy": "8283",
            "rv": "true",
            "opening": "true",
        }

        response = requests.get(
            "https://dgtrade.trishakti.com.np:8080/bom/api/account/report/ledger",
            params=params,
            headers=get_headers(),
        )

        if response.status_code == 200:
            return response.json().get("balance")
        return None


    def extract_balance(self):
        # --- MAIN LOOP ---
        df = pd.read_excel(config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL)

        # Ensure columns exist
        if 'ledgerFetched' not in df.columns:
            df['ledgerFetched'] = "NO"
        if 'ledgerBalance' not in df.columns:
            df['ledgerBalance'] = None
        if 'clientCode' not in df.columns:
            df['clientCode'] = None
        df['ledgerFetched'] = df['ledgerFetched'].astype(str)
        df['clientCode'] = df['clientCode'].astype(str)
        # Convert types once
        df['boid'] = df['boid'].astype(str)

        unique_boids = df.loc[df['ledgerFetched'] != 'YES', 'boid'].unique()

        for boid in unique_boids:
            print(f"Processing BOID -> {boid}")

            response = requests.get(
                "https://dgtrade.trishakti.com.np:8080/bom/api/customer/customer-registration/find-client-info",
                params={"name": boid},
                headers=get_headers(),
            )

            if response.status_code == 200:
                data = response.json()
                if len(data) > 0:
                    ac_code = str(data[0]["acCode"])
                    # Extract TMS code safely
                    client_name = str(data[0].get("clientName", ""))
                    match = re.search(r"\[([^\[\]]+)\]", client_name)
                    tms_code_value = match.group(1) if match else ""

                    ledger_balance = self.__get_ledger_balance(ac_code)
                    try:
                        ledger_balance = float(ledger_balance)
                    except (ValueError, TypeError):
                        ledger_balance = 0.0  

                    print(f"Fetched -> {boid} | acCode: {ac_code} | balance: {ledger_balance} | TMS: {tms_code_value}")

                    df.loc[df['boid'] == boid, ['ledgerBalance', 'ledgerFetched', 'clientCode']] = [
                        ledger_balance,
                        'YES',
                        tms_code_value
                    ]

                    df['boid'] = df['boid'].astype(str)
                    df['ledgerBalance'] = pd.to_numeric(df['ledgerBalance'], errors='coerce').fillna(0.0)
                    df['ledgerBalance'] = df['ledgerBalance'].apply(lambda x: f"{x:.2f}")
                    df['ledgerBalance'] = df['ledgerBalance'].astype(float)
                    
                    df.to_excel(config.OUTPUT_CLIENT_DATA_FILEPATH_FINAL, index=False)

                else:
                    print(f"⚠️ No data found for BOID: {boid}")
                sleep(3)
            else:
                print(f"❌ Status Code: {response.status_code}, re-logging...")
                login_dg()
        print("✅ All BOIDs processed successfully!")
