import os
from time import sleep
from utils.helper import show_message, ensure_session_management_folder
from config.config import base_url_tms, credentials_tms, chrome_profile_bot_dg
from .xpaths import *
import pickle
from config.config import session_management_path_tms_cookies, session_management_path_tms_session_id_path
import ddddocr
import base64
from playwright.sync_api import sync_playwright

ocr = ddddocr.DdddOcr()
captured_session_ids = set()


def handle_response(response):
    headers = response.headers
    if 'host-session-id' in headers:
        captured_session_ids.add(headers['host-session-id'])


def save_cookies(page):
    cookies = page.context.cookies()
    with open(session_management_path_tms_cookies, "wb") as f:
        pickle.dump(cookies, f)
    show_message(f"Cookies saved to {session_management_path_tms_cookies}.")


def extract_session_ids():
    if captured_session_ids:
        with open(session_management_path_tms_session_id_path, "w") as f:
            for sid in captured_session_ids:
                f.write(sid + "\n")
        show_message(f"Host-Session-IDs saved to {session_management_path_tms_session_id_path}.")
    else:
        show_message("⚠ No Host-Session-IDs found.")


def setup_chrome_driver(playwright):
    temp_profile = chrome_profile_bot_dg
    os.makedirs(temp_profile, exist_ok=True)

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=temp_profile,
        headless=False,
        args=['--start-maximized'],
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.on("response", handle_response)
    page.goto("https://tms48.nepsetms.com.np/tms/dashboard")
    return page, context


def clear_input_fields(page, xpath_value):
    page.locator(xpath_value).fill("")


def login_tms():   
    ensure_session_management_folder()
    show_message("EXECUTE TMS . . . . .")
    
    playwright = sync_playwright().start()
    page, context = setup_chrome_driver(playwright)
    page.goto(url=base_url_tms)
    is_captcha_correct = False
    while True:
        try:
            page.locator("//a[normalize-space()='Forgot Password?']").wait_for(timeout=3000)
            show_message("Please provide CAPTCHA")
            
            captcha_element = page.locator('img.captcha-image-dimension')
            captcha_url = captcha_element.get_attribute('src')
            show_message(f"Captcha URL: {captcha_url}")
            
            base64_image = page.evaluate("""
                async (blobUrl) => {
                    const res = await fetch(blobUrl);
                    const blob = await res.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                }
            """, captcha_url)
            
            base64_data = base64_image.split(",")[1]
            img_bytes = base64.b64decode(base64_data)
            captcha_text = ocr.classification(img_bytes)
            show_message(f"Captcha Text: {captcha_text}")
            
            clear_input_fields(page, xpath_input_username)
            clear_input_fields(page, xpath_input_password)
            page.locator(xpath_input_username).fill(credentials_tms['username'])
            page.locator(xpath_input_password).fill(credentials_tms['password'])
            page.locator(xpath_input_captcha).fill(captcha_text)
            page.locator(xpath_button_login).click()
            try:
                page.locator("//span[@class='toast-title']").wait_for(timeout=3000)
                page.reload()
                show_message("Wrong captcha", 'red')
            except Exception as e:
                is_captcha_correct = True
                pass
        except Exception as e:
            is_captcha_correct = True
            pass

        if is_captcha_correct:
                page.locator("//span[contains(text(),'Search Client')]").wait_for(timeout=100000)
                save_cookies(page=page)
                extract_session_ids()
                show_message("Please Wait . . . .\n\n", 'white')
                try:
                    page.context.close()
                    break
                except Exception as e:
                    show_message("Error while closing the driver.", "red")

if __name__ == "__main__":         
    login_tms()
