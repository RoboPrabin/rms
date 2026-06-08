from config.config import cookies_management_path_dg, session_management_path_dg
import pickle
import json


def get_cookies():
    try:
        with open(cookies_management_path_dg, 'rb') as f:
            cookies = pickle.load(f)
    except FileNotFoundError:
        return {}

    return {
        cookie['name']: cookie['value']
        for cookie in cookies
        if cookie.get('name') and cookie.get('value')
    }


def get_headers():
    with open(session_management_path_dg, 'r') as f:
        local_storage = json.load(f)

        bom_session_id = local_storage.get('bom-sessionId', '')
        em = local_storage.get('em', '')
        
        pn = local_storage.get('pn', '')
        if not pn:
            # Older DG sessions stored Pn inside tempem.
            tempem_raw = local_storage.get('tempem', '[]')
            try:
                tempem_list = json.loads(tempem_raw)
                pn = tempem_list[2] if len(tempem_list) > 2 else ''
            except json.JSONDecodeError:
                pn = ''

        token = local_storage.get('token', '')

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Access-Control-Allow-Origin': '*',
        'Authorization': 'Bearer ' + token,
        'Connection': 'keep-alive',
        'Em': em,
        'Pn': pn,
        'Referer': 'https://dgtrade.trishakti.com.np:8080/bom/index.html',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'X-Session-Id': bom_session_id,
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    return headers
