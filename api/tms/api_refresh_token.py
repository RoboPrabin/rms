import requests
from utils import helper
from .shared_api_tms import get_headers, get_cookie
from ui.login_tms import login_tms


def refresh_token(cookies, headers):
    while True:
        response = requests.post('https://tms48.nepsetms.com.np/tmsapi/authApi/authenticate/refresh', 
                                
                                cookies=cookies, headers=headers)
        if response.status_code == 200:
            new_cookies = response.cookies.get_dict()
            helper.show_message("🔄️ Token refreshed successfully ")
            return new_cookies, headers
        else:
            helper.show_message(f"Failed to get refresh token: {response.status_code}", "red")
            helper.show_message(f"Response Text: {response.text}", "red")
            try:
                err_response = response.json()
                if err_response['message'] == 'INVALID_REFRESH_TOKEN':
                    login_tms()
                else:
                    return cookies, headers
            except Exception as e:
                helper.show_message(f"Error parsing response 'err_response' JSON: {e}", "red")
                return cookies, headers