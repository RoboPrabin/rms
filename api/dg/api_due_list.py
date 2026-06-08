# from time import sleep

# import requests
# from api.dg.shared_api_dg import get_cookies, get_headers
# from ui.login_dg import login_dg
# from utils.helper import (get_tplustwo_date, 
#                           create_folder_with_datetime, 
#                           get_date_from_folderpath, 
#                           show_message, update_due_list_flag, 
#                           has_downloaded_due_list_today,
#                           get_folder_path_from_flag)
# import pandas as pd



# def extract_client_code_from_duelist(duelist_filepath: str) -> None:
#     """
#     Reads a duelist file, extracts the client code from clientName 
#     by splitting and slicing, adds it as a new column 'clientCode',
#     and saves back to the same file.
    
#     :param duelist_filepath: Path to the duelist Excel file
#     """
#     # Read the duelist Excel file
#     df_duelist = pd.read_excel(duelist_filepath)

#     # Define a function to extract code using split and slice
#     def extract_code(name):
#         if isinstance(name, str):
#             parts = name.strip().split(' ')
#             if parts:
#                 last_part = parts[-1]
#                 return last_part[1:-1]  # Remove the '[' and ']'
#         return None  # Safe fallback

#     # Apply the function to clientName
#     df_duelist['clientCode'] = df_duelist['clientName'].apply(extract_code)
#     df_duelist['adjustedBalance'] = df_duelist['adjustedBalance'] * -1

#     # Save back to the same file (overwrite)
#     df_duelist.to_excel(duelist_filepath, index=False)

#     show_message(f"Successfully extracted clientCode and updated file: {duelist_filepath}")


# def fetch_due_list():
    
#     if not has_downloaded_due_list_today():
#         show_message("Fetching due report from dg. Please Wait ...")
#         while True:
#             params = {
#                 'pageNumber': '0',
#                 'date': get_tplustwo_date(),
#                 'dueType': 'DR',
#                 'calcBy': 'settlementDate',
#                 'agentDues': 'false',
#                 'otherDp': 'false',
#                 'ownDp': 'false',
#             }
#             print("\n\n")
#             headers = get_headers()
#             cookies = get_cookies()
#             print(headers)
#             response = requests.get(
#                 'https://dgtrade.trishakti.com.np:8080/bom/api/account/report/due',
#                 params=params,
#                 headers=headers,
#                 cookies=cookies,
#             )
#             print("\n")
#             print(response.text, response.status_code)
#             print("\n\n")
#             if response.status_code == 200:
#                 show_message("Due Report fetched successfully.", 'green')
#                 folder_path = create_folder_with_datetime()
#                 date_name = get_date_from_folderpath(folder_path)
#                 filepath = f"{folder_path}\\due_report_{date_name}.xlsx"
#                 pd.DataFrame(response.json()).to_excel(filepath, index=False)

#                 extract_client_code_from_duelist(duelist_filepath=filepath) 
#                 update_due_list_flag(filepath=filepath)
#                 break
#             else:
#                 show_message(f"❌ API call failed: {response.status_code}", 'red')
#                 login_dg()

#     else:
#         filepath = get_folder_path_from_flag()
#         show_message("Due list already downloaded today at " + filepath, 'green')
#     return filepath
















import asyncio
import base64

import ddddocr
import pandas as pd
import requests
from playwright.async_api import async_playwright

from utils.helper import (
    create_folder_with_datetime,
    get_date_from_folderpath,
    get_folder_path_from_flag,
    get_tplustwo_date,
    has_downloaded_due_list_today,
    show_message,
    update_due_list_flag,
)

LOGIN_URL = "https://dgtrade.trishakti.com.np:8080/bom/index.html#/login"
DASHBOARD_URL_FRAGMENT = "#/dashboard"
USERNAME = "AUTOBOT"
PASSWORD = "Autom@ti0n"

_ocr = ddddocr.DdddOcr(show_ad=False)


async def _login_and_extract_auth(max_attempts: int = 5) -> tuple[dict, dict]:
    """Returns (headers, cookies) captured from browser after successful login."""
    captured_headers = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        async def on_request(request):
            if "/bom/api/" in request.url:
                captured_headers.update(request.headers)

        page.on("request", on_request)
        await page.goto(LOGIN_URL)
        await page.wait_for_load_state("networkidle")

        for attempt in range(1, max_attempts + 1):
            print(f"Login attempt {attempt}/{max_attempts}")
            await page.fill('input[name="username"]', USERNAME)
            await page.fill('input[name="password"]', PASSWORD)

            captcha_src = await page.get_attribute('img[alt="captcha"]', "src")
            if not captcha_src or not captcha_src.startswith("data:image/png;base64,"):
                print("ERROR: Cannot find captcha image")
                break

            image_b64 = captcha_src.split("base64,", 1)[1]
            captcha_text = _ocr.classification(base64.b64decode(image_b64)).strip()
            print(f"Captcha solved: '{captcha_text}'")

            await page.fill('input[name="captcha"]', captcha_text)
            await page.click('div.text-center:has-text("Login")')
            await page.wait_for_timeout(2000)

            error_el = await page.query_selector("span.text-danger")
            if error_el and "Invalid Captcha" in await error_el.inner_text():
                print("Wrong captcha — retrying")
                await page.fill('input[name="captcha"]', "")
                continue

            if DASHBOARD_URL_FRAGMENT in page.url:
                print("Login SUCCESS")
                await page.wait_for_timeout(2000)
                break
            else:
                print(f"Unexpected state at attempt {attempt}")
        else:
            await browser.close()
            return {}, {}

        context_cookies = await context.cookies()
        cookies = {c["name"]: c["value"] for c in context_cookies}
        await browser.close()
        return captured_headers, cookies


def _build_headers(captured: dict) -> dict:
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": captured.get(
            "user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        ),
        "Access-Control-Allow-Origin": "*",
    }
    key_map = {
        "authorization": "Authorization",
        "pn": "Pn",
        "em": "Em",
        "x-session-id": "X-Session-Id",
        "referer": "Referer",
        "sec-ch-ua": "sec-ch-ua",
        "sec-ch-ua-mobile": "sec-ch-ua-mobile",
        "sec-ch-ua-platform": "sec-ch-ua-platform",
    }
    for raw_key, display_key in key_map.items():
        if raw_key in captured:
            headers[display_key] = captured[raw_key]
    return headers


def extract_client_code_from_duelist(duelist_filepath: str) -> None:
    """
    Reads a duelist file, extracts the client code from clientName
    by splitting and slicing, adds it as a new column 'clientCode',
    and saves back to the same file.

    :param duelist_filepath: Path to the duelist Excel file
    """
    df_duelist = pd.read_excel(duelist_filepath)

    def extract_code(name):
        if isinstance(name, str):
            parts = name.strip().split(' ')
            if parts:
                last_part = parts[-1]
                return last_part[1:-1]
        return None

    df_duelist['clientCode'] = df_duelist['clientName'].apply(extract_code)
    df_duelist['adjustedBalance'] = df_duelist['adjustedBalance'] * -1

    df_duelist.to_excel(duelist_filepath, index=False)
    show_message(f"Successfully extracted clientCode and updated file: {duelist_filepath}")


def fetch_due_list():
    if not has_downloaded_due_list_today():
        show_message("Fetching due report from dg. Please Wait ...")
        while True:
            captured_headers, cookies = asyncio.run(_login_and_extract_auth())
            if not captured_headers:
                show_message("❌ Login failed — cannot fetch due list", 'red')
                return None

            params = {
                'pageNumber': '0',
                'date': get_tplustwo_date(),
                'dueType': 'DR',
                'calcBy': 'settlementDate',
                'agentDues': 'false',
                'otherDp': 'false',
                'ownDp': 'false',
            }
            headers = _build_headers(captured_headers)
            response = requests.get(
                'https://dgtrade.trishakti.com.np:8080/bom/api/account/report/due',
                params=params,
                headers=headers,
                cookies=cookies,
                verify=False,
            )
            print(response.text, response.status_code)

            if response.status_code == 200:
                show_message("Due Report fetched successfully.", 'green')
                folder_path = create_folder_with_datetime()
                date_name = get_date_from_folderpath(folder_path)
                filepath = f"{folder_path}\\due_report_{date_name}.xlsx"
                pd.DataFrame(response.json()).to_excel(filepath, index=False)
                extract_client_code_from_duelist(duelist_filepath=filepath)
                update_due_list_flag(filepath=filepath)
                break
            else:
                show_message(f"❌ API call failed: {response.status_code}", 'red')
    else:
        filepath = get_folder_path_from_flag()
        show_message("Due list already downloaded today at " + filepath, 'green')

    return filepath
