import requests
from utils import helper
from .shared_api_tms import get_headers, get_cookie
def refresh_token():
    while True:
        response = requests.post('https://tms48.nepsetms.com.np/tmsapi/authApi/authenticate/refresh', cookies=get_cookie(), headers=get_headers())
        if response.status_code == 200:
            helper.show_message("🤖 💥 Token refreshed successfully ")
            new_cookies = response.cookies.get_dict()
            helper.show_message(f"Fetched new token successfully.", "green")
            # helper.show_message(f"{new_cookies}", "green")
            return new_cookies, get_headers()
        else:
            helper.show_message(f"Failed to get refresh token: {response.status_code}", "red")
            helper.show_message(f"Response Text: {response.text}", "red")