import requests
from utils import helper
# from .shared_api_tms import get_headers, get_cookie
from ui.login_tms import login_tms
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .api_refresh_token import refresh_token
from utils.helper import show_message

# Setup retry-enabled session
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)
adapter = HTTPAdapter(max_retries=retries)
session.mount("http://", adapter)
session.mount("https://", adapter)


def get_client_server_id(headers, cookies, client_code: str):
    while True:
        print("Trying to get server_id ...... ")
        response = session.get(
            f"https://tms48.nepsetms.com.np/tmsapi/orderbook/search-all-client/{client_code}",
            headers=headers,
            cookies=cookies,
        )

        data = response.json() if response.status_code == 200 else []

        if response.status_code == 200:
            if len(data) >= 1:
                client_server_id = data[0].get("id", 0)
                # Always return a tuple
                return client_server_id, cookies, headers
            else:
                # No client found
                return 0, cookies, headers

        elif response.status_code == 401:
            show_message(f"Unauthorized, refreshing token...")
            cookies, headers = refresh_token(cookies=cookies, headers=headers)

        else:
            show_message(f"Error {response.status_code}: {response.text}")
            return 0, cookies, headers




def load_collateral_for_specific_client(
    headers,
    cookies,
    amount: int,
    client_code: str,
    loaded_by:str,
) -> str:
    client_server_id, cook, head = get_client_server_id(headers=headers, cookies=cookies, client_code=client_code)
    show_message(f"Server id : {client_server_id}", color='green')
    if client_server_id != 0:
        # print(topup_amount, non_cash_collateral)
        if client_server_id is not None:
            json_data = {
                "cashCollateralAmount": 0,
                "chequeCollateralAmount": 0,
                "chequeDate": None,
                "chequeNo": None,
                # 'clientGroupId': 101,
                "clientGroupId": None,
                "clientDealerMasterId": client_server_id,
                "collateralExpiryDate": None,
                "collateralMultiplicationFactor": 1,
                "collateralUtilized": 0,
                "creditForSale": amount,
                "fundTransferAmount": 0,
                "nonCashCollateralAmount": 0,
                "remarks": "RMS Collateral loaded by ".upper() + loaded_by,
                "topUpAmount": 0,
            }

            response = session.post(
                "https://tms48.nepsetms.com.np/tmsapi/clientApi/rms-limit-setup/non-cash-collateral",
                headers=head,
                json=json_data,
                cookies=cook,
            )

            if response.status_code == 200:
                # show_message(
                #     "Collateral added successfully :: Server Response -> "
                #     + response.json()["message"],
                #     "green",
                # )
                return response.json()["message"]
            else:
                # login_tms()
                show_message(f"Load Collateral function. {response.text} | {response.status_code}", color='red')
        else:
            return None
    else:
        show_message(f"Client code {client_code} not found", "red")
        return "Invalid Client Code"



























# import requests
# from utils import helper
# # from .shared_api_tms import get_headers, get_cookie
# from ui.login_tms import login_tms
# from requests.adapters import HTTPAdapter
# from urllib3.util.retry import Retry
# from .api_refresh_token import refresh_token
# from utils.helper import show_message
# # Setup retry-enabled session
# session = requests.Session()
# retries = Retry(
#     total=5,
#     backoff_factor=5,
#     status_forcelist=[500, 502, 503, 504],
#     allowed_methods=["GET", "POST"],
# )
# adapter = HTTPAdapter(max_retries=retries)
# session.mount("http://", adapter)
# session.mount("https://", adapter)


# def get_client_server_id(headers, cookies, client_code: str):
#     while True:
#         response = session.get(
#             f"https://tms48.nepsetms.com.np/tmsapi/orderbook/search-all-client/{client_code}",
#             headers=headers,
#             cookies=cookies,
#         )
#         if response.status_code == 200:
#             # print(response.json())
#             if len(response.json()) >= 1:

#                 client_server_id = response.json()[0].get("id", 0)
#                 # show_message(f"Client code :: {client_code}  ->  Client Server ID :: {client_server_id}", 'magenta')
#                 return client_server_id
#             elif len(response.json()) > 1:
#                 client_server_id = response.json()[0].get("id", 0)
#                 return client_server_id
#             else:
#                 return 0
#         elif response.status_code == 401:
#             show_message(f"get_client_server_id {response.status_code}")
#             login_tms()
#         else:
#             show_message(f"get_client_server_id {response.status_code}")
#             show_message(f"{response.text}")
#             login_tms()



# def load_collateral_for_specific_client(
#     headers,
#     cookies,
#     topup_amount: int,
#     client_code: str,
#     loaded_by:str,
# ) -> str:
#     while True:
#         client_server_id = get_client_server_id(headers=headers, cookies=cookies, client_code=client_code)
#         if client_server_id != 0:
#             # print(topup_amount, non_cash_collateral)
#             if client_server_id is not None:
#                 json_data = {
#                     "cashCollateralAmount": 0,
#                     "chequeCollateralAmount": 0,
#                     "chequeDate": None,
#                     "chequeNo": None,
#                     # 'clientGroupId': 101,
#                     "clientGroupId": None,
#                     "clientDealerMasterId": client_server_id,
#                     "collateralExpiryDate": None,
#                     "collateralMultiplicationFactor": 1,
#                     "collateralUtilized": 0,
#                     "creditForSale": 0,
#                     "fundTransferAmount": 0,
#                     "nonCashCollateralAmount": 0,
#                     "remarks": "RMS Collateral loaded by ".upper() + loaded_by,
#                     "topUpAmount": topup_amount,
#                 }

#                 response = session.post(
#                     "https://tms48.nepsetms.com.np/tmsapi/clientApi/rms-limit-setup/non-cash-collateral",
#                     headers=headers(),
#                     json=json_data,
#                     cookies=cookies(),
#                 )

#                 if response.status_code == 200:
#                     show_message(
#                         "Collateral added successfully :: Server Response -> "
#                         + response.json()["message"],
#                         "green",
#                     )
#                     return response.json()["message"]
#                 else:
#                     login_tms()
#             else:
#                 return None
#         else:
#             show_message(f"Client code {client_code} not found", "red")
#             return "Invalid Client Code"
