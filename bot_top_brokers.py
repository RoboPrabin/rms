import requests
import pandas as pd
from sqlalchemy import create_engine
import requests
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import DictCursor

# ---------------------------
# PostgreSQL connection setup
# ---------------------------
def get_connection():
    return psycopg2.connect(
        host="172.17.26.6",
        dbname="client_holdings",
        user="postgres",
        password="admin",
        cursor_factory=DictCursor
    )

# SQLAlchemy engine for easy append
engine = create_engine(
    'postgresql+psycopg2://postgres:admin@172.17.26.6/client_holdings'
)

def get_today_data():
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.sharesansar.com/top-brokers',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    params = {
        'draw': '1',
        'columns[0][data]': 'DT_Row_Index',
        'columns[0][name]': '',
        'columns[0][searchable]': 'false',
        'columns[0][orderable]': 'false',
        'columns[0][search][value]': '',
        'columns[0][search][regex]': 'false',
        'columns[1][data]': 'number',
        'columns[1][name]': '',
        'columns[1][searchable]': 'false',
        'columns[1][orderable]': 'true',
        'columns[1][search][value]': '',
        'columns[1][search][regex]': 'false',
        'columns[2][data]': 'name',
        'columns[2][name]': '',
        'columns[2][searchable]': 'false',
        'columns[2][orderable]': 'true',
        'columns[2][search][value]': '',
        'columns[2][search][regex]': 'false',
        'columns[3][data]': 'buyerAmount',
        'columns[3][name]': '',
        'columns[3][searchable]': 'false',
        'columns[3][orderable]': 'true',
        'columns[3][search][value]': '',
        'columns[3][search][regex]': 'false',
        'columns[4][data]': 'sellerAmount',
        'columns[4][name]': '',
        'columns[4][searchable]': 'false',
        'columns[4][orderable]': 'true',
        'columns[4][search][value]': '',
        'columns[4][search][regex]': 'false',
        'columns[5][data]': 'totalAmount',
        'columns[5][name]': '',
        'columns[5][searchable]': 'false',
        'columns[5][orderable]': 'true',
        'columns[5][search][value]': '',
        'columns[5][search][regex]': 'false',
        'columns[6][data]': 'differ',
        'columns[6][name]': '',
        'columns[6][searchable]': 'false',
        'columns[6][orderable]': 'true',
        'columns[6][search][value]': '',
        'columns[6][search][regex]': 'false',
        'columns[7][data]': 'matchingAmount',
        'columns[7][name]': '',
        'columns[7][searchable]': 'false',
        'columns[7][orderable]': 'true',
        'columns[7][search][value]': '',
        'columns[7][search][regex]': 'false',
        'order[0][column]': '5',
        'order[0][dir]': 'desc',
        'start': '0',
        'length': '-1',
        'search[value]': '',
        'search[regex]': 'false',
        'date': datetime.now().strftime("%Y-%m-%d"),
        # '_': '1767606538692',
    }

    response = requests.get('https://www.sharesansar.com/top-brokers', params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()['data']
        df = pd.DataFrame(data)
        df.to_sql("top-brokers", engine, if_exists='append',index=False)
    else:
        print("Failed to fetch data.")

def get_all_data():
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://www.sharesansar.com/top-brokers',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
        # 'cookie': '_gid=GA1.2.1732434292.1767592779; _ga_FPXFBP3MT9=GS2.1.s1767606529$o42$g1$t1767606539$j50$l0$h0; _ga=GA1.2.1751698080.1746529281; XSRF-TOKEN=eyJpdiI6InJSNUZIMkI0K0xjaFFQd3R3RTZ1dlE9PSIsInZhbHVlIjoicVlGQlcyUTFGU0FZb2xMN0tGTjFjL2JVT2s3dGpTR3RUeUFBMVdsamd3OEhDUjJUdkV0Z05Gc1dLMzBmbW9LSisva2JrUk1McTBrZ1cwUHdJY0wzRmVPanBBWDd3dlFqL0RXTThiOGh4TGJlQU93U0xEQWMrSXNMODNHK1dheloiLCJtYWMiOiJmNTU0MTFjM2JhMzBjOWIyMjgyYWMwZmQ3NWJhOWZkZThmYWE2ZjA4YjJjMjkyZDJlYTA3NmUyZTAwYjJkY2IzIn0%3D; sharesansar_session=eyJpdiI6IkJXcnB0dlZVb2VXT20wcCtrT0FmN1E9PSIsInZhbHVlIjoiSlEzQ2pmcS9JcDY1M2ZCZGdwZFhEamd3OUNTczQ5SVhqUVJLTU45b0Y3YklYUmhFczYxTS8wakorMis5cWdaTTFJcmhPTnVoZ3hWZ0NrTTJiRWlWakQyN0xPa2pHNGlvL1pqYVc5SUZBTWVoQUZDczJWaGF4REhMd2toY3NiYzYiLCJtYWMiOiJhNGQ0ZDI3MzFmN2IyMjc1OTM0Mjc0MGQ5Mjk3OTkxNDE3ZmJiZDI4ZDBhNGE5NGQ3NmViZTllMjJlODljNGE1In0%3D',
    }

    def get_top_brokers(date_str:str):
        params = {
            'draw': '1',
            'columns[0][data]': 'DT_Row_Index',
            'columns[0][name]': '',
            'columns[0][searchable]': 'false',
            'columns[0][orderable]': 'false',
            'columns[0][search][value]': '',
            'columns[0][search][regex]': 'false',
            'columns[1][data]': 'number',
            'columns[1][name]': '',
            'columns[1][searchable]': 'false',
            'columns[1][orderable]': 'true',
            'columns[1][search][value]': '',
            'columns[1][search][regex]': 'false',
            'columns[2][data]': 'name',
            'columns[2][name]': '',
            'columns[2][searchable]': 'false',
            'columns[2][orderable]': 'true',
            'columns[2][search][value]': '',
            'columns[2][search][regex]': 'false',
            'columns[3][data]': 'buyerAmount',
            'columns[3][name]': '',
            'columns[3][searchable]': 'false',
            'columns[3][orderable]': 'true',
            'columns[3][search][value]': '',
            'columns[3][search][regex]': 'false',
            'columns[4][data]': 'sellerAmount',
            'columns[4][name]': '',
            'columns[4][searchable]': 'false',
            'columns[4][orderable]': 'true',
            'columns[4][search][value]': '',
            'columns[4][search][regex]': 'false',
            'columns[5][data]': 'totalAmount',
            'columns[5][name]': '',
            'columns[5][searchable]': 'false',
            'columns[5][orderable]': 'true',
            'columns[5][search][value]': '',
            'columns[5][search][regex]': 'false',
            'columns[6][data]': 'differ',
            'columns[6][name]': '',
            'columns[6][searchable]': 'false',
            'columns[6][orderable]': 'true',
            'columns[6][search][value]': '',
            'columns[6][search][regex]': 'false',
            'columns[7][data]': 'matchingAmount',
            'columns[7][name]': '',
            'columns[7][searchable]': 'false',
            'columns[7][orderable]': 'true',
            'columns[7][search][value]': '',
            'columns[7][search][regex]': 'false',
            'order[0][column]': '5',
            'order[0][dir]': 'desc',
            'start': '0',
            'length': '-1',
            'search[value]': '',
            'search[regex]': 'false',
            'date': date_str,
            # 'date': '2026-01-05',
        }

        response = requests.get('https://www.sharesansar.com/top-brokers', params=params, headers=headers)
        data = response.json()['data']
        return  pd.DataFrame(data)

    all_dfs = []
    start_date = datetime(2025, 7, 17)
    # end_date = datetime(2025, 7, 28)
    end_date = datetime.today()  # or a fixed date, e.g., datetime(2026, 1, 5)
    current_date = start_date
    while current_date <= end_date:
        df = get_top_brokers(current_date)
        df['date'] = current_date.strftime("%Y-%m-%d")
        print(f"Total data: {len(df)} for date: {current_date}")
        if not df.empty:
            all_dfs.append(df)
        current_date += timedelta(days=1)

    # ---------------------------
    # Combine all data and append to PostgreSQL
    # ---------------------------
    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        final_df.to_sql('top_brokers', engine, if_exists='replace', index=False)
        print(f"Done! Appended {len(final_df)} rows to 'top_brokers'.")
    else:
        print("No data fetched for any date.")


if __name__ == "__main__":
    get_today_data()