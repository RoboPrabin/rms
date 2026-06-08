
# from time import sleep
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.common.keys import Keys
# # from selenium import webdriver
# from seleniumwire import webdriver
# from utils.helper import show_message, ensure_session_management_folder
# import json
# from selenium.webdriver.support import expected_conditions as EC
# from config.config import session_management_path_dg, url_login_dgtrade, credentials_dg, cookies_management_path_dg
# import capsolver
# import pickle
# import os
# xpath_button_login = "//button[@type='submit']"
# xpath_input_username = "//input[@placeholder='Enter your username']"
# xpath_input_password = "//input[@placeholder='Enter your password']"
# xpath_popup_msg = "//div[@class='toast-text']"
# xpath_input_captcha = "//input[@placeholder='Enter Captcha']"
# url_login = url_login_dgtrade


# def solve_captcha(base64_image: str) -> str:
#     """
#     Send CAPTCHA image base64 to CapSolver and return solved text.
#     Raises exception on failure.
#     """
#     capsolver.api_key = "CAP-0258EF6064A2E8274663BCAC67127F0A7105E2D1827C71E448E4D7F7548AB716"
#     solution = capsolver.solve({
#         "type": "ImageToTextTask",
#         "module": "common",
#         "body": base64_image
#     })
#     show_message("CAPTCHA:" + solution["text"])
#     return solution["text"]


# def save_local_storage_data(driver:webdriver.Chrome):
#     local_storage_data = driver.execute_script("""
#     var items = {};
#     for (var i = 0; i < window.localStorage.length; i++) {
#         var key = window.localStorage.key(i);
#         items[key] = window.localStorage.getItem(key);
#     }
#     return items;
#     """)
#     with open(session_management_path_dg, 'w') as f:
#         json.dump(local_storage_data, f, indent=4)
#     show_message(f"local_storage data saved to {session_management_path_dg}", 'white')
# #  https://dgtrade.trishakti.com.np:8080/bom/index.html#/dashboard
# def setup_chrome_driver():
#     # script_dir = os.path.abspath(os.path.dirname(__file__))
#     chrome_options = Options()
#     chrome_options.add_argument("--start-maximized")
#     chrome_options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
#     chrome_options.add_experimental_option("useAutomationExtension", False)

#     driver = webdriver.Chrome(options=chrome_options)
#     driver.maximize_window()
#     driver.get("https://dgtrade.trishakti.com.np:8080/bom/index.html#/dashboard")
#     return driver


# # def setup_chrome_driver():
# #     chrome_options = Options()
# #     chrome_options.add_argument('--incognito')
# #     chrome_options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
# #     # chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
# #     driver = webdriver.Chrome(options=chrome_options)
# #     driver.maximize_window()
# #     return driver

# def is_captcha_request_present(driver: webdriver.Chrome) -> bool:
#     """Check intercepted requests for any CAPTCHA-related URLs."""
#     for request in driver.requests:
#         if request.response and "captcha" in request.url.lower():
#             show_message(f"[ℹ️] CAPTCHA-related request found: {request.url}", 'green')
#             return True
#     return False

# def clear_input_fields(driver:webdriver.Chrome, xpath_value:str):
#     driver.find_element(By.XPATH, xpath_value).send_keys(Keys.CONTROL + "a")
#     driver.find_element(By.XPATH, xpath_value).send_keys(Keys.DELETE)

# def login_dg():    
#     ensure_session_management_folder()
#     show_message("Logging to DG Trade. Expecting CAPTCHA from user.", 'white')

#     driver = setup_chrome_driver()
#     # driver.get(url=url_login)

#     sleep(3)

#     try:
#         if driver.find_element(
#             By.XPATH,
#             "//div[@class='modal-dialog modal-sm']//button[@aria-label='Close'][normalize-space()='×']"
#         ).is_displayed():

#             driver.find_element(
#                 By.XPATH,
#                 "//div[@class='modal-dialog modal-sm']//button[@aria-label='Close'][normalize-space()='×']"
#             ).click()

#     except Exception as e:
#         pass

#     is_captcha_correct = False

#     while not is_captcha_correct:
#         try:
#             is_captcha_request_present(driver=driver)

#             captcha_img = WebDriverWait(driver, 8).until(
#                 EC.presence_of_element_located(
#                     (By.CSS_SELECTOR, 'img[alt="captcha"]')
#                 )
#             )

#             base64_src = captcha_img.get_attribute("src")

#             if not base64_src.startswith("data:image"):
#                 print("[❌] CAPTCHA image src does not contain base64 data, refreshing page.")
#                 driver.refresh()
#                 continue

#             # ASK USER TO ENTER CAPTCHA
#             captcha_text = input("Enter CAPTCHA shown in DG Trade: ").strip()

#             clear_input_fields(driver, xpath_input_username)
#             clear_input_fields(driver, xpath_input_password)
#             clear_input_fields(driver, xpath_input_captcha)

#             driver.find_element(By.XPATH, xpath_input_username).send_keys(
#                 credentials_dg['username']
#             )

#             driver.find_element(By.XPATH, xpath_input_password).send_keys(
#                 credentials_dg['password']
#             )

#             driver.find_element(By.XPATH, xpath_input_captcha).send_keys(
#                 captcha_text
#             )

#             driver.find_element(By.XPATH, xpath_button_login).click()

#             try:
#                 incorrect_captcha = WebDriverWait(driver, 3).until(
#                     EC.presence_of_element_located(
#                         (By.XPATH, "//div[normalize-space()='Invalid Captcha']")
#                     )
#                 )

#                 driver.refresh()
#                 show_message("Wrong captcha", 'red')
#                 sleep(1.3)

#             except:
#                 # LOGIN SUCCESS
#                 show_message("Logged in DG.", "green")

#                 WebDriverWait(driver, 5).until(
#                     EC.presence_of_element_located((
#                         By.XPATH,
#                         "//a[@aria-label='Dropdown toggle'][normalize-space()='Setup & Utility']"
#                     ))
#                 )

#                 is_captcha_correct = True

#                 cookies = driver.get_cookies()

#                 with open(cookies_management_path_dg, "wb") as f:
#                     pickle.dump(cookies, f)

#                 show_message(
#                     f"cookies saved to {cookies_management_path_dg}",
#                     'white'
#                 )

#                 save_local_storage_data(driver)

#                 show_message("Please Wait . . . .\n\n", 'white')

#                 try:
#                     driver.close()
#                     driver.quit()

#                 except Exception as e:
#                     show_message("Error while closing the driver.", "red")

#         except Exception as e:
#             driver.get("https://dgtrade.trishakti.com.np:8080/bom/index.html#/login")
#             continue
# if __name__ == "__main__":         
#     login_dg()


from time import sleep
from playwright.sync_api import sync_playwright
from utils.helper import show_message, ensure_session_management_folder
import json
from config.config import session_management_path_dg, url_login_dgtrade, credentials_dg, cookies_management_path_dg
import ddddocr
import base64
import pickle
import asyncio
import threading

xpath_button_login = "//button[@type='submit']"
xpath_input_username = "//input[@placeholder='Enter your username']"
xpath_input_password = "//input[@placeholder='Enter your password']"
xpath_popup_msg = "//div[@class='toast-text']"
xpath_input_captcha = "//input[@placeholder='Enter Captcha']"
url_login = url_login_dgtrade

ocr = ddddocr.DdddOcr(show_ad=False)


def solve_captcha(image_bytes: bytes) -> str:
    result = ocr.classification(image_bytes)
    show_message(f"CAPTCHA: {result}")
    return result


def save_local_storage_data(page):
    local_storage_data = page.evaluate("""
    var items = {};
    for (var i = 0; i < window.localStorage.length; i++) {
        var key = window.localStorage.key(i);
        items[key] = window.localStorage.getItem(key);
    }
    return items;
    """)
    with open(session_management_path_dg, 'w') as f:
        json.dump(local_storage_data, f, indent=4)
    show_message(f"local_storage data saved to {session_management_path_dg}", 'white')


def setup_chrome_page():
    p = sync_playwright().start()
    try:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-gpu",
                "--disable-software-rasterizer",
            ],
        )
        context = browser.new_context(no_viewport=True)
    except Exception:
        p.stop()
        raise

    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://dgtrade.trishakti.com.np:8080/bom/index.html#/dashboard")
    return p, context, page


def is_captcha_request_present(responses_list) -> bool:
    """Check intercepted responses for any CAPTCHA-related URLs."""
    for resp in responses_list:
        if "captcha" in resp.url.lower():
            show_message(f"[ℹ️] CAPTCHA-related request found: {resp.url}", 'green')
            return True
    return False


def clear_input_fields(page, xpath_value: str):
    page.locator(xpath_value).fill("")


def _login_dg_sync():    
    ensure_session_management_folder()
    show_message("Logging to DG Trade. Solving CAPTCHA automatically.", 'white')

    p, context, page = setup_chrome_page()

    sleep(3)

    captured_responses = []
    page.on("response", lambda resp: captured_responses.append(resp))

    try:
        if page.locator(
            "//div[@class='modal-dialog modal-sm']//button[@aria-label='Close'][normalize-space()='×']"
        ).is_visible():

            page.locator(
                "//div[@class='modal-dialog modal-sm']//button[@aria-label='Close'][normalize-space()='×']"
            ).click()

    except Exception as e:
        pass

    is_captcha_correct = False

    while not is_captcha_correct:
        try:
            is_captcha_request_present(captured_responses)

            captcha_img = page.locator('img[alt="captcha"]')
            captcha_img.wait_for(timeout=8000)

            base64_src = captcha_img.get_attribute("src")

            if not base64_src.startswith("data:image"):
                print("[❌] CAPTCHA image src does not contain base64 data, refreshing page.")
                page.reload()
                continue

            image_bytes = base64.b64decode(base64_src.split(",")[1])
            captcha_text = solve_captcha(image_bytes)

            clear_input_fields(page, xpath_input_username)
            clear_input_fields(page, xpath_input_password)
            clear_input_fields(page, xpath_input_captcha)

            page.locator(xpath_input_username).fill(
                credentials_dg['username']
            )

            page.locator(xpath_input_password).fill(
                credentials_dg['password']
            )

            page.locator(xpath_input_captcha).fill(
                captcha_text
            )

            page.locator(xpath_button_login).click()

            try:
                page.locator("//div[normalize-space()='Invalid Captcha']").wait_for(timeout=3000)

                page.reload()
                show_message("Wrong captcha", 'red')
                sleep(1.3)

            except:
                # LOGIN SUCCESS
                show_message("Logged in DG.", "green")

                page.locator(
                    "//a[@aria-label='Dropdown toggle'][normalize-space()='Setup & Utility']"
                ).wait_for(timeout=5000)

                is_captcha_correct = True

                cookies = context.cookies()

                with open(cookies_management_path_dg, "wb") as f:
                    pickle.dump(cookies, f)

                show_message(
                    f"cookies saved to {cookies_management_path_dg}",
                    'white'
                )

                save_local_storage_data(page)

                show_message("Please Wait . . . .\n\n", 'white')

                try:
                    page.close()
                    context.close()
                    p.stop()

                except Exception as e:
                    show_message("Error while closing the driver.", "red")

        except Exception as e:
            page.goto("https://dgtrade.trishakti.com.np:8080/bom/index.html#/login")
            continue


def _run_login_dg_in_thread():
    result = {"error": None}

    def target():
        try:
            _login_dg_sync()
        except Exception as e:
            result["error"] = e

    thread = threading.Thread(target=target, name="DGPlaywrightLogin")
    thread.start()
    thread.join()

    if result["error"]:
        raise result["error"]


def login_dg():
    # try:
    #     asyncio.get_running_loop()
    # except RuntimeError:
    # _login_dg_sync()
    # else:
    _run_login_dg_in_thread()


if __name__ == "__main__":         
    login_dg()
