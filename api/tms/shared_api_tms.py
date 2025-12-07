from utils.helper import read_cookies_from_file
from ui.login_tms import login_tms 
from config.config import session_management_path_tms_cookies, session_management_path_tms_session_id_path, credentials_tms
import pickle


def load_cookies():
    global xsrf
    xsrf = ''
    with open(session_management_path_tms_cookies, "rb") as f:
        cookies = pickle.load(f)
    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}

    if 'XSRF-TOKEN' in cookie_dict:
        xsrf = cookie_dict['XSRF-TOKEN']
    
    return cookie_dict

def load_session_ids():
    with open(session_management_path_tms_session_id_path, "r") as f:
        session_ids = f.readlines()
    session_ids = [sid.strip() for sid in session_ids]
    return session_ids


def get_cookie():
    # global host_session_id, xsrf
    # xsrf, aid, rid, host_session_id = read_cookies_from_file()
    return load_cookies()


def get_headers(referer:str ='https://tms48.nepsetms.com.np/tms/administration/reports-grid'):
    session_ids = load_session_ids()
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

