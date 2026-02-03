import os
import shutil
from my_captcha.extract_captcha import extract_captcha
from time import sleep
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from utils.helper import show_message, get_user_input, ensure_session_management_folder
from utils.helper import save_cookies_data, update_cookies
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config.config import base_url_tms, credentials_tms_for_collateral_only, chrome_profile_bot_dg
from seleniumwire import webdriver
from .xpaths import *   
import pickle
from config.config import session_management_path_tms_cookies,session_management_path_tms_session_id_path
from db import db

# Save cookies to a pickle file
def save_cookies(driver):
    cookies = driver.get_cookies()
    show_message(f"Cookies found.")
    return cookies

def extract_session_ids(driver):
    session_ids = set()
    for request in driver.requests:
        if request.response:
            if 'host-session-id' in request.headers:
                session_ids.add(request.headers['host-session-id'])
            if 'host-session-id' in request.response.headers:
                session_ids.add(request.response.headers['host-session-id'])

    if session_ids:
        show_message(f"Session id found.")
        return session_ids
    else:
        show_message("⚠️ No Host-Session-IDs found.")


def setup_chrome_driver():
    # script_dir = os.path.abspath(os.path.dirname(__file__))
    # temp_profile = os.path.join(script_dir, "ChromeProfile")
    # temp_profile = chrome_profile_bot_dg
    # os.makedirs(temp_profile, exist_ok=True)  # Just create an empty dir


    chrome_options = Options()
    # chrome_options.add_argument(f"--user-data-dir={temp_profile}")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    driver.get("https://tms48.nepsetms.com.np/tms/dashboard")
    return driver


def clear_input_fields(driver:webdriver.Chrome, xpath_value:str):
    driver.find_element(By.XPATH, xpath_value).send_keys(Keys.CONTROL + "a")
    driver.find_element(By.XPATH, xpath_value).send_keys(Keys.DELETE)

def extract_host_session_id()->str:
    for request in driver.requests:
        if request.response and "host-session-id" in request.headers:
            host_session_id = request.headers['host-session-id']
            if host_session_id:
                # show_message(f"Found host-session-id: {host_session_id}")
                return host_session_id
    return None



def login_tms_for_collateral():   
    # ensure_session_management_folder()
    global driver
    show_message("EXECUTE TMS FOR COLLATERAL . . . . .")
    driver = setup_chrome_driver()
    driver.get(url=base_url_tms)
    is_captcha_correct = False
    while True:
        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//a[normalize-space()='Forgot Password?']")))
            show_message("Please provide CAPTCHA")
            # input_value = get_user_input("TMS")
            input_value = extract_captcha(driver=driver)
            clear_input_fields(driver, xpath_input_username)
            clear_input_fields(driver, xpath_input_password)
            driver.find_element(By.XPATH, xpath_input_username).send_keys(credentials_tms_for_collateral_only['username'])
            driver.find_element(By.XPATH, xpath_input_password).send_keys(credentials_tms_for_collateral_only['password'])
            driver.find_element(By.XPATH, xpath_input_captcha).send_keys(input_value)
            driver.find_element(By.XPATH, xpath_button_login).click()
            try:
                WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//span[@class='toast-title']")))
                driver.refresh()
                show_message("Wrong captcha", 'red')
            except Exception as e:
                is_captcha_correct = True
                pass
        except Exception as e:
            is_captcha_correct = True
            pass

        if is_captcha_correct:
                WebDriverWait(driver , 100).until(EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'Search Client')]")))
                cookies = save_cookies(driver=driver)
                session_id = extract_session_ids(driver=driver)
                db.upsert_tms_session(cookies=cookies, session_id=session_id, created_by="ADMIN", updated_by="ADMIN")
                show_message("Please Wait . . . .\n\n", 'white')
                try:
                    driver.close()
                    driver.quit()
                    break
                except Exception as e:
                    show_message("Error while closing the driver.", "red")



if __name__ == "__main__":         
    login_tms_for_collateral()