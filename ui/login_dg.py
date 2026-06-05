from time import sleep
from utils.helper import show_message, ensure_session_management_folder
import json
from config.config import session_management_path_dg, url_login_dgtrade, credentials_dg, cookies_management_path_dg, chrome_profile_bot_dg
import ddddocr
import pickle
import os
import base64
from playwright.sync_api import sync_playwright

xpath_button_login = "//button[@type='submit']"
xpath_input_username = "//input[@placeholder='Enter your username']"
xpath_input_password = "//input[@placeholder='Enter your password']"
xpath_popup_msg = "//div[@class='toast-text']"
xpath_input_captcha = "//input[@placeholder='Enter Captcha']"
url_login = url_login_dgtrade

ocr = ddddocr.DdddOcr()


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


def setup_chrome_driver(playwright):
    temp_profile = chrome_profile_bot_dg
    os.makedirs(temp_profile, exist_ok=True)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=temp_profile,
        headless=False,
        args=['--start-maximized'],
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://dgtrade.trishakti.com.np:8080/bom/index.html#/dashboard")
    return page, context


def clear_input_fields(page, xpath_value):
    page.locator(xpath_value).fill("")


def login_dg():    
    ensure_session_management_folder()
    show_message("Logging to DG Trade. Expecting CAPTCHA from user.", 'white')

    playwright = sync_playwright().start()
    page, context = setup_chrome_driver(playwright)

    sleep(3)

    try:
        close_btn = page.locator("//div[@class='modal-dialog modal-sm']//button[@aria-label='Close'][normalize-space()='×']")
        if close_btn.is_visible():
            close_btn.click()
    except Exception:
        pass

    is_captcha_correct = False

    while not is_captcha_correct:
        try:
            captcha_img = page.locator('img[alt="captcha"]')
            captcha_img.wait_for(timeout=8000)

            base64_src = captcha_img.get_attribute("src")

            if not base64_src.startswith("data:image"):
                print("[❌] CAPTCHA image src does not contain base64 data, refreshing page.")
                page.reload()
                continue

            img_data = base64.b64decode(base64_src.split(",")[1])
            captcha_text = ocr.classification(img_data)
            show_message(f"CAPTCHA: {captcha_text}")

            clear_input_fields(page, xpath_input_username)
            clear_input_fields(page, xpath_input_password)
            clear_input_fields(page, xpath_input_captcha)

            page.locator(xpath_input_username).fill(credentials_dg['username'])
            page.locator(xpath_input_password).fill(credentials_dg['password'])
            page.locator(xpath_input_captcha).fill(captcha_text)
            page.locator(xpath_button_login).click()

            try:
                page.locator("//div[normalize-space()='Invalid Captcha']").wait_for(timeout=3000)
                page.reload()
                show_message("Wrong captcha", 'red')
                sleep(1.3)
            except:
                show_message("Logged in DG.", "green")

                page.locator("//a[@aria-label='Dropdown toggle'][normalize-space()='Setup & Utility']").wait_for(timeout=5000)
                is_captcha_correct = True

                cookies = page.context.cookies()

                with open(cookies_management_path_dg, "wb") as f:
                    pickle.dump(cookies, f)

                show_message(f"cookies saved to {cookies_management_path_dg}", 'white')

                save_local_storage_data(page)

                show_message("Please Wait . . . .\n\n", 'white')

                try:
                    page.context.close()
                except Exception as e:
                    show_message("Error while closing the driver.", "red")

        except Exception as e:
            page.goto("https://dgtrade.trishakti.com.np:8080/bom/index.html#/login")
            continue

if __name__ == "__main__":         
    login_dg()
