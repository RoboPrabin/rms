import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
import psycopg2
from datetime import datetime
from db import db
class LiveUpdater:
    def __init__(self):
        pass
        
    # 🧠 Database connection
    # def get_connection(self):
    #     return psycopg2.connect(
    #         host="localhost",
    #         database="client_holdings",
    #         user="postgres",
    #         password="admin"
    #     )

    # 🔍 Fetch all client scripts from DB
    def get_all_scripts(self):
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT script FROM client_holdings;")
        scripts = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return scripts

    # 🌐 Scrape live prices from merolagani
    def fetch_live_market(self):
        url = "https://merolagani.com/LatestMarket.aspx"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table', class_='table table-hover live-trading sortable')
        if not table:
            print("⚠️ Live trading table not found.")
            return {}

        data = {}
        for tr in table.find('tbody').find_all('tr'):
            tds = [td.text.strip() for td in tr.find_all('td')]
            # print(tds[1])
            # print(tds[0])
            # print(tds)
            if len(tds) >= 3:
                symbol = tds[0]           # e.g. 'NABIL', 'NTC', etc.
                ltp = tds[1].replace(',', '')
                try:
                    data[symbol] = float(ltp)
                except:
                    pass
        return data

    # 🧾 Update live_price and valuation in DB
    def update_prices(self):
        live_data = self.fetch_live_market()
        print(live_data)
        import time
        time.sleep(1000000)
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
                """, (ltp, ltp, datetime.now().strftime("%Y-%m-%d %I:%M:%S"), script))
                updated_count += 1

        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ Updated {updated_count} scripts at {datetime.now()}")

    def scheduler(self):
        while True:
            self.update_prices()
            print("Sleeping for 1 minute...\n")
            time.sleep(60) 

if __name__ == "__main__":
    LiveUpdater().scheduler()
