import ast
from api.tms import api_collateral
from db import db
from ui.login_tms_collateral import login_tms_for_collateral
from config.config import credentials_tms_for_collateral_only




# cookies, session_id = db.get_tms_session()

# def get_headers(referer:str ='https://tms48.nepsetms.com.np/tms/member/search/client-search',):
#     return {
#         'accept': 'application/json, text/plain, */*',
#         'accept-language': 'en-US,en;q=0.9',
#         'content-type': 'application/json',
#         'host-session-id': session_id,
#         'origin': 'https://tms48.nepsetms.com.np',
#         'priority': 'u=1, i',
#         'referer': referer,
#         'request-owner': credentials_tms_for_collateral_only['server_id'],
#         'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
#         'sec-ch-ua-mobile': '?0',
#         'sec-ch-ua-platform': '"Windows"',
#         'sec-fetch-dest': 'empty',
#         'sec-fetch-mode': 'cors',
#         'sec-fetch-site': 'same-origin',
#         'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
#         'x-xsrf-token': cookies['XSRF-TOKEN'],

#     }



# result = api_collateral.load_collateral_for_specific_client(headers=get_headers(), cookies=cookies, amount=100000, 
#             client_code="20250329860", loaded_by="PRABIN CHAND TEST" )


login_tms_for_collateral()