import requests
from utils.helper import read_cookies_from_file
from ui.login_tms import login_tms 
from config.config import session_management_path_tms_cookies, session_management_path_tms_session_id_path, credentials_tms
import pickle
from utils import helper

def refresh_token():
    while True:
        response = requests.post('https://tms48.nepsetms.com.np/tmsapi/authApi/authenticate/refresh', 
                                
                                cookies=get_cookie(), headers=get_headers())
        if response.status_code == 200:
            new_cookies = response.cookies.get_dict()
            helper.show_message("🔄️ Token refreshed successfully ")
            with open(session_management_path_tms_cookies, "wb") as f:
                pickle.dump(new_cookies, f)
            helper.show_message(f"Cookies saved to {session_management_path_tms_cookies}.")
            break
        else:
            helper.show_message(f"Failed to get refresh token: {response.status_code}", "red")
            helper.show_message(f"Response Text: {response.text}", "red")
            helper.show_message(f"Logging TMS ...", "yellow")
            login_tms()
            return
        
        

def load_cookies():
    has_domain = False
    with open(session_management_path_tms_cookies, "rb") as f:
        cookies = pickle.load(f)
    for cookie in cookies:
        if 'domain' in cookie:
            has_domain = True
            break

    if has_domain:
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        # if 'XSRF-TOKEN' in cookie_dict:
        #     xsrf = cookie_dict['XSRF-TOKEN']
        return cookie_dict
    else:
        return cookies


def get_xsrf():
    has_domain = False
    with open(session_management_path_tms_cookies, "rb") as f:
        cookies = pickle.load(f)
    for cookie in cookies:
        if 'domain' in cookie:
            has_domain = True
            break

    if has_domain:
        cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
        if 'XSRF-TOKEN' in cookie_dict:
            xsrf = cookie_dict['XSRF-TOKEN']
        return xsrf
    else:
        return cookies['XSRF-TOKEN']


def load_session_ids():
    with open(session_management_path_tms_session_id_path, "r") as f:
        session_ids = f.readlines()
    session_ids = [sid.strip() for sid in session_ids]
    return session_ids


def get_cookie():
    return load_cookies()


def get_headers(referer:str ='https://tms48.nepsetms.com.np/tms/administration/reports-grid'):
    session_ids = load_session_ids()
    xsrf = get_xsrf()
    return {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json',
        'host-session-id': session_ids[0],
        'origin': 'https://tms48.nepsetms.com.np',
        'priority': 'u=1, i',
        'referer': referer,
        'request-owner': credentials_tms['server_id'],
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'x-xsrf-token': xsrf,

    }

