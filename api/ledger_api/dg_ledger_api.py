from config.config import LOGIN_API, AC_CODE_API, LEDGER_API, dg_api_password, dg_api_userName
import requests

# st.set_page_config(page_title="Custom Hotkeys", layout="wide")
# ---------------- API HELPERS ----------------
def get_token():
    resp = requests.post(
        LOGIN_API,
        json={"userName": dg_api_userName, "password": dg_api_password},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json().get("token")


def get_account_code(token, nepse_code):
    resp = requests.get(
        AC_CODE_API,
        headers={"Authorization": f"Bearer {token}"},
        params={"nepseCode": nepse_code},
        timeout=30
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        return resp.status_code


def get_ledger(token, nepse_code, date_from, date_to):
    ac_code = get_account_code(token=token, nepse_code=nepse_code)
    resp = requests.get(
        LEDGER_API,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "acCode": ac_code,
            "dateFrom": date_from,
            "dateTo": date_to
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()
