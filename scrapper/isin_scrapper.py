import io
import requests
from bs4 import BeautifulSoup
import pandas as pd
from utils.helper import show_message, get_holding_engine
from sqlalchemy import create_engine

# BASE_URL = "https://cdsc.com.np/Home.Investor.isinscript?page={}"
BASE_URL = "https://cdsc.com.np/isinscrip?page={}"
HEADERS = {'User-Agent': 'Mozilla/5.0'}


def dump_to_db(df: pd.DataFrame, table_name: str = "isin"):
    # Get SQLAlchemy engine from your helper
    engine = create_engine(get_holding_engine())

    # Dump DataFrame to SQL table
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",   # options: 'fail', 'replace', 'append'
        index=False            # don’t write DataFrame index as a column
    )
    show_message(f"ISIN data dumped to isin table.", color="green")

def get_total_pages():
    response = requests.get(BASE_URL.format(1), headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    pagination = soup.select_one('ul.pagination')
    if not pagination:
        return 1  # fallback if pagination isn't present

    li_tags = pagination.find_all('li')
    # Get the highest number (skip 'Next', 'Prev', etc.)
    page_numbers = [int(li.get_text(strip=True)) for li in li_tags if li.get_text(strip=True).isdigit()]
    return max(page_numbers)

def scrape_table_from_page(page_number):
    response = requests.get(BASE_URL.format(page_number), headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.select_one('#listall table')
    if not table:
        return pd.DataFrame()

    df = pd.read_html(io.StringIO(str(table)))[0]
    return df

def scrape_isin_from_cdas_website():
    show_message("Extracting data from CDAS website. Please wait . . .", 'yellow')
    total_pages = get_total_pages()
    show_message(f"Total pages found in CDAS: {total_pages}")

    all_dataframes = []
    for page in range(1, total_pages + 1):
        show_message(f"Scraping page {page}/{total_pages}...")
        df = scrape_table_from_page(page)
        if not df.empty:
            all_dataframes.append(df)

    combined_df = pd.concat(all_dataframes, ignore_index=True)
    combined_df = combined_df.drop(columns="S.N")
    # combined_df.to_excel(filename, index=False)
    dump_to_db(df=combined_df)

if __name__ == "__main__":
    scrape_isin_from_cdas_website()
