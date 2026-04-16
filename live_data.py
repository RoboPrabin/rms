# from playwright.async_api import async_playwright
# import asyncio
# import psycopg2
# from psycopg2 import extras

# USERNAME = "ANJIT_48"
# PASSWORD = "Anjit@48"


# def get_connection():
#     return psycopg2.connect(
#         host="172.17.26.6",
#         dbname="margin_trading",
#         user="postgres",
#         password="admin",
#         cursor_factory=psycopg2.extras.DictCursor
#     )


# def clean_number(value):
#     if value is None:
#         return None
#     value = value.replace(",", "").replace("%", "").strip()
#     try:
#         return float(value)
#     except:
#         return None


# async def scrape_and_store(page):
#     print("📥 Scraping live market data...")

#     rows = page.locator(".live-data-table tbody tr")
#     count = await rows.count()

#     print(f"✅ Found {count} rows")

#     # ✅ REMOVE DUPLICATES USING DICT
#     unique_data = {}

#     for i in range(count):
#         row = rows.nth(i)
#         cols = row.locator("td")

#         col_count = await cols.count()
#         if col_count < 9:
#             continue

#         values = []
#         for j in range(col_count):
#             text = await cols.nth(j).inner_text()
#             values.append(text.strip())

#         symbol = values[0]

#         # overwrite duplicates → keep latest
#         unique_data[symbol] = (
#             symbol,
#             clean_number(values[1]),
#             clean_number(values[2]),
#             clean_number(values[3]),
#             clean_number(values[4]),
#             clean_number(values[5]),
#             clean_number(values[6]),
#             clean_number(values[7]),
#             clean_number(values[8]),
#         )

#     data_list = list(unique_data.values())

#     if not data_list:
#         print("⚠️ No data scraped, skipping insert")
#         return

#     conn = get_connection()
#     cur = conn.cursor()

#     # ✅ REPLACE OLD DATA
#     cur.execute("TRUNCATE TABLE live_data")

#     insert_query = """
#         INSERT INTO live_data (
#             symbol, ltp, point_change, percent_change,
#             open, high, low, volume, previous_close
#         )
#         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#     """

#     extras.execute_batch(cur, insert_query, data_list)

#     conn.commit()
#     cur.close()
#     conn.close()

#     print(f"🔄 Inserted {len(data_list)} unique rows\n")


# async def fetch_data():
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=False)
#         page = await browser.new_page()

#         await page.goto("https://tms48.nepsetms.com.np/login")

#         await page.fill('input[placeholder="Client Code/ User Name"]', USERNAME)
#         await page.fill('input[placeholder="Password"]', PASSWORD)

#         print("\n👉 Look at the browser and read the CAPTCHA")
#         captcha = await asyncio.to_thread(input, "Enter CAPTCHA: ")

#         await page.fill('input[placeholder="Enter Captcha"]', captcha)

#         await page.click('input[value="Login"]')

#         print("⏳ Waiting for login to complete...")

#         try:
#             await page.wait_for_url("**/tms/**", timeout=15000)
#         except:
#             print("❌ Login failed")
#             return

#         print("✅ Login successful")

#         await page.goto("https://tms48.nepsetms.com.np/tms/mwDashboard")

#         # ✅ Correct selector
#         await page.wait_for_selector(".live-data-table tbody tr", state="attached", timeout=10000)

#         await asyncio.sleep(2)

#         print("📊 Live market loaded")

#         # 🔁 Run every 5 sec
#         while True:
#             await scrape_and_store(page)
#             await asyncio.sleep(2)


# asyncio.run(fetch_data())

from playwright.async_api import async_playwright
import asyncio
import psycopg2
from psycopg2 import extras
import time

USERNAME = "ANJIT_48"
PASSWORD = "Anjit@48"


def get_connection():
    return psycopg2.connect(
        host="172.17.26.6",
        dbname="margin_trading",
        user="postgres",
        password="admin",
        cursor_factory=psycopg2.extras.DictCursor
    )


def clean_number(value):
    if value is None:
        return None
    value = value.replace(",", "").replace("%", "").strip()
    try:
        return float(value)
    except:
        return None


# 🚀 FAST SCRAPER
async def scrape_fast(page):
    return await page.evaluate("""
        () => {
            const rows = document.querySelectorAll('.live-data-table tbody tr');
            const data = {};

            rows.forEach(row => {
                const cols = row.querySelectorAll('td');
                if (cols.length < 9) return;

                const get = i => cols[i]?.innerText?.trim() || null;

                const symbol = get(0);

                data[symbol] = [
                    symbol,
                    get(1),
                    get(2),
                    get(3),
                    get(4),
                    get(5),
                    get(6),
                    get(7),
                    get(8),
                    get(9)
                ];
            });

            return Object.values(data);
        }
    """)


# 💾 SCRAPE + STORE (FIXED)
async def scrape_and_store(page, conn):
    print("📥 Importing data...")

    try:
        raw_data = await scrape_fast(page)

        if not raw_data:
            print("⚠️ No data found")
            return

        data_list = [
            (
                r[0],
                clean_number(r[1]),
                clean_number(r[2]),
                clean_number(r[3]),
                clean_number(r[4]),
                clean_number(r[5]),
                clean_number(r[6]),
                clean_number(r[7]),
                clean_number(r[8]),
                clean_number(r[9])  
            )
            for r in raw_data
        ]

        cur = conn.cursor()

        # Clear old data
        cur.execute("TRUNCATE TABLE live_data")

        # FIXED INSERT (9 columns only)
        insert_query = """
            INSERT INTO live_data (
                symbol,
                ltp,
                ltv,
                point_change,
                percent_change,
                open,
                high,
                low,
                volume,
                previous_close
            )
            VALUES %s
        """

        extras.execute_values(cur, insert_query, data_list)

        conn.commit()
        cur.close()

        print(f"💾 Saved {len(data_list)} rows")
        print(f"⏳ Time: {time.strftime('%X')}")
        print("=" * 40)

    except Exception as e:
        conn.rollback()   # 🔥 FIX: prevent transaction lock
        print("❌ Error:", e)


# 🚀 MAIN LOOP
async def fetch_data():
    conn = get_connection()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-dev-shm-usage", "--no-sandbox"]
        )

        page = await browser.new_page()

        await page.goto("https://tms48.nepsetms.com.np/login")

        await page.fill('input[placeholder="Client Code/ User Name"]', USERNAME)
        await page.fill('input[placeholder="Password"]', PASSWORD)

        captcha = await asyncio.to_thread(input, "Enter CAPTCHA: ")
        await page.fill('input[placeholder="Enter Captcha"]', captcha)

        await page.click('input[value="Login"]')

        await page.wait_for_url("**/tms/**", timeout=15000)

        await page.goto("https://tms48.nepsetms.com.np/tms/mwDashboard")

        await page.wait_for_selector(".live-data-table tbody tr")

        print("📊 Live market loaded")

        while True:
            start = time.time()

            try:
                await scrape_and_store(page, conn)
            except Exception as e:
                print("❌ Loop Error:", e)

            elapsed = time.time() - start

            # keep 5 sec cycle stable
            await asyncio.sleep(max(1, 5 - elapsed))


asyncio.run(fetch_data())