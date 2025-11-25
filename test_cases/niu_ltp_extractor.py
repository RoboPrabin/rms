import requests
from bs4 import BeautifulSoup

class LtpExtractor:
    def __init__(self):
        print("[+] Initilizing Ltp Extractor . . .")
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
            if len(tds) >= 3:
                symbol = tds[0]           # e.g. 'NABIL', 'NTC', etc.
                ltp = tds[1].replace(',', '')
                try:
                    data[symbol] = float(ltp)
                except:
                    pass
        return data