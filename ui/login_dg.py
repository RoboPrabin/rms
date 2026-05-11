# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.common.keys import Keys
# from selenium import webdriver
# from utils.helper import show_message, get_user_input, ensure_session_management_folder
# import json
# from selenium.webdriver.support import expected_conditions as EC
# from config import session_management_path_dg, url_login_dgtrade, credentials_dg

# xpath_button_login = "//button[@type='submit']"
# xpath_input_username = "//input[@placeholder='Enter your username']"
# xpath_input_password = "//input[@placeholder='Enter your password']"
# xpath_popup_msg = "//div[@class='toast-text']"
# xpath_input_captcha = "//input[@placeholder='Enter Captcha']"
# url_login = url_login_dgtrade




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
 
# def setup_chrome_driver():
#     chrome_options = Options()
#     chrome_options.add_argument('--incognito')
#     chrome_options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
#     # chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
#     driver = webdriver.Chrome(options=chrome_options)
#     driver.maximize_window()
#     return driver



# def clear_input_fields(driver:webdriver.Chrome, xpath_value:str):
#     driver.find_element(By.XPATH, xpath_value).send_keys(Keys.CONTROL + "a")
#     driver.find_element(By.XPATH, xpath_value).send_keys(Keys.DELETE)

# def login_dg():    
#     ensure_session_management_folder()
#     show_message("Logging to DG Trade. Expecting CAPTCHA from user.", 'white')
#     driver = setup_chrome_driver()
#     driver.get(url=url_login)


#     is_captcha_correct = False
#     while not is_captcha_correct:
#         input_value = get_user_input("DG TRADE")
#         clear_input_fields(driver, xpath_input_username)
#         clear_input_fields(driver, xpath_input_password)
#         driver.find_element(By.XPATH, xpath_input_username).send_keys(credentials_dg['username'])
#         driver.find_element(By.XPATH, xpath_input_password).send_keys(credentials_dg['password'])
#         driver.find_element(By.XPATH, xpath_input_captcha).send_keys(input_value)
#         driver.find_element(By.XPATH, xpath_button_login).click()
#         try:
#             incorrect_captcha = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//div[normalize-space()='Invalid Captcha']")))
#             driver.refresh()
#             show_message("Wrong captcha", 'red')
#         except Exception as e:
#                 WebDriverWait(driver , 10).until(EC.presence_of_element_located((By.XPATH, "//a[@aria-label='Dropdown toggle'][normalize-space()='Setup & Utility']")))
#                 is_captcha_correct = True
#                 # save_cookies_data(driver)
#                 save_local_storage_data(driver)
#                 show_message("Please Wait . . . .\n\n", 'white')
#                 try:
#                     driver.close()
#                     driver.quit()
#                 except Exception as e:
#                     show_message("Error while closing the driver.", "red")
            
# if __name__ == "__main__":         
#     login_dg()


from time import sleep
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
# from selenium import webdriver
from seleniumwire import webdriver
from utils.helper import show_message, ensure_session_management_folder
import json
from selenium.webdriver.support import expected_conditions as EC
from config.config import session_management_path_dg, url_login_dgtrade, credentials_dg, cookies_management_path_dg, chrome_profile_bot_dg
import capsolver
import pickle
import os
xpath_button_login = "//button[@type='submit']"
xpath_input_username = "//input[@placeholder='Enter your username']"
xpath_input_password = "//input[@placeholder='Enter your password']"
xpath_popup_msg = "//div[@class='toast-text']"
xpath_input_captcha = "//input[@placeholder='Enter Captcha']"
url_login = url_login_dgtrade


def solve_captcha(base64_image: str) -> str:
    """
    Send CAPTCHA image base64 to CapSolver and return solved text.
    Raises exception on failure.
    """
    capsolver.api_key = "CAP-0258EF6064A2E8274663BCAC67127F0A7105E2D1827C71E448E4D7F7548AB716"
    solution = capsolver.solve({
        "type": "ImageToTextTask",
        "module": "common",
        "body": base64_image
    })
    show_message("CAPTCHA:" + solution["text"])
    return solution["text"]


def save_local_storage_data(driver:webdriver.Chrome):
    local_storage_data = driver.execute_script("""
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
#  https://dgtrade.trishakti.com.np:8080/bom/index.html#/dashboard
def setup_chrome_driver():
    # script_dir = os.path.abspath(os.path.dirname(__file__))
    # temp_profile = os.path.join(script_dir, "ChromeProfileMis")
    temp_profile = chrome_profile_bot_dg
    os.makedirs(temp_profile, exist_ok=True)  # Just create an empty dir

    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={temp_profile}")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    driver.get("https://dgtrade.trishakti.com.np:8080/bom/index.html#/dashboard")
    return driver


# def setup_chrome_driver():
#     chrome_options = Options()
#     chrome_options.add_argument('--incognito')
#     chrome_options.add_experimental_option("excludeSwitches", ['enable-automation', 'enable-logging'])
#     # chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
#     driver = webdriver.Chrome(options=chrome_options)
#     driver.maximize_window()
#     return driver

def is_captcha_request_present(driver: webdriver.Chrome) -> bool:
    """Check intercepted requests for any CAPTCHA-related URLs."""
    for request in driver.requests:
        if request.response and "captcha" in request.url.lower():
            show_message(f"[ℹ️] CAPTCHA-related request found: {request.url}", 'green')
            return True
    return False

def clear_input_fields(driver:webdriver.Chrome, xpath_value:str):
    driver.find_element(By.XPATH, xpath_value).send_keys(Keys.CONTROL + "a")
    driver.find_element(By.XPATH, xpath_value).send_keys(Keys.DELETE)

def login_dg():    
    ensure_session_management_folder()
    show_message("Logging to DG Trade. Expecting CAPTCHA from user.", 'white')

    driver = setup_chrome_driver()
    # driver.get(url=url_login)

    sleep(3)

    try:
        if driver.find_element(
            By.XPATH,
            "//div[@class='modal-dialog modal-sm']//button[@aria-label='Close'][normalize-space()='×']"
        ).is_displayed():

            driver.find_element(
                By.XPATH,
                "//div[@class='modal-dialog modal-sm']//button[@aria-label='Close'][normalize-space()='×']"
            ).click()

    except Exception as e:
        pass

    is_captcha_correct = False

    while not is_captcha_correct:
        try:
            is_captcha_request_present(driver=driver)

            captcha_img = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'img[alt="captcha"]')
                )
            )

            base64_src = captcha_img.get_attribute("src")

            if not base64_src.startswith("data:image"):
                print("[❌] CAPTCHA image src does not contain base64 data, refreshing page.")
                driver.refresh()
                continue

            # ASK USER TO ENTER CAPTCHA
            captcha_text = input("Enter CAPTCHA shown in DG Trade: ").strip()

            clear_input_fields(driver, xpath_input_username)
            clear_input_fields(driver, xpath_input_password)
            clear_input_fields(driver, xpath_input_captcha)

            driver.find_element(By.XPATH, xpath_input_username).send_keys(
                credentials_dg['username']
            )

            driver.find_element(By.XPATH, xpath_input_password).send_keys(
                credentials_dg['password']
            )

            driver.find_element(By.XPATH, xpath_input_captcha).send_keys(
                captcha_text
            )

            driver.find_element(By.XPATH, xpath_button_login).click()

            try:
                incorrect_captcha = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[normalize-space()='Invalid Captcha']")
                    )
                )

                driver.refresh()
                show_message("Wrong captcha", 'red')
                sleep(1.3)

            except:
                # LOGIN SUCCESS
                show_message("Logged in DG.", "green")

                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//a[@aria-label='Dropdown toggle'][normalize-space()='Setup & Utility']"
                    ))
                )

                is_captcha_correct = True

                cookies = driver.get_cookies()

                with open(cookies_management_path_dg, "wb") as f:
                    pickle.dump(cookies, f)

                show_message(
                    f"cookies saved to {cookies_management_path_dg}",
                    'white'
                )

                save_local_storage_data(driver)

                show_message("Please Wait . . . .\n\n", 'white')

                try:
                    driver.close()
                    driver.quit()

                except Exception as e:
                    show_message("Error while closing the driver.", "red")

        except Exception as e:
            driver.get("https://dgtrade.trishakti.com.np:8080/bom/index.html#/login")
            continue
if __name__ == "__main__":         
    login_dg()