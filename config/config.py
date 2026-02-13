from pathlib import Path
import time
# PROJECT_PATH = r"D:\Trishakti\Projects\RPA\rms"
# chrome_profile_bot_dg = r"D:\Profile\ChromeProfileBot"
# GALLERY_PATH = r"D:\Trishakti_Gallery"

PROJECT_PATH = r"E:\Trishakti\Projects\rms"
chrome_profile_bot_dg = r"E:\Trishakti\ChromeProfileBot"
GALLERY_PATH = r"E:\Trishakti\Trishakti_Gallery"


login_animation_path = PROJECT_PATH + r"\assets\anim\login.json"
otp_animation_path = PROJECT_PATH + r"\assets\anim\otp.json"

# Set expiry for 8 hours from now (60 sec * 60 min * 8)
# session_expiry_time = int(time.time()) + (3600 * 8)
# session_expiry_time = 30
session_expiry_time = 28800   #8 hours
# session_expiry_time = int(time.time()) + 20

# ---------------- CONFIG ----------------
dg_api_userName = "tri-api"
dg_api_password = "Bq!92Xw#Tz6@"
BASE_API = "https://dgtrade.trishakti.com.np:8080/bom/"
LOGIN_API = BASE_API + "tp-data/authenticate"
AC_CODE_API = BASE_API + "tp-data/account/by-nepse"
LEDGER_API = BASE_API + "tp-data/account/ledger"
KYC_API = BASE_API + "tp-data/account/client-details"



MASTER_PASSWORD = "prabin"

CLIENT_DATA_FILEPATH = PROJECT_PATH + r"\data\input\client_data.xlsx"
OUTPUT_CLIENT_DATA_FILEPATH = PROJECT_PATH + r"\data\output\holdings.xlsx"
OUTPUT_CLIENT_DATA_FILEPATH_FINAL = PROJECT_PATH + r"\data\output\holdings_FINAL.xlsx"

MEROSHARE_URL = "https://meroshare.cdsc.com.np/#/login"


due_list_flag_path = PROJECT_PATH + r"\data\flag\due_list_flag.txt"

# Create output directory
output_folder_path = PROJECT_PATH + r"\data\output"

REFRESH_TIME_IN_SECONDS = 50000
RM_REFRESH_TIME_IN_SECONDS = 60

FLOORSHEET_UPLOAD_TIIME = "03:14 PM"

postgresql_config = {
    "db_user": "postgres",
    "db_password" : "admin",
    "db_host" : "172.17.26.6" ,        
    # "db_host" : "localhost" ,        
    "db_port" : "5432",          
    "db_name" : "client_holdings"
}





# Get Desktop path
desktop_path = Path.home() / "Desktop"
cost_benefit_project_path = desktop_path / "server" / "RPA" / "Cost Benefit"
mis_project_path = desktop_path / "server" / "RPA" / "MIS"


# SESSION MANAGEMENT
rpa_session_management_default_path = (
    desktop_path / "server" / "RPA" / "SessionManagement"
)
session_management_path_tms = (
    rpa_session_management_default_path / "TMS" / "cookies_tms.json"
)
session_management_path_tms_cookies = (
    rpa_session_management_default_path / "TMS" / "cookies_tms.pkl"
)
session_management_path_tms_session_id_path = (
    rpa_session_management_default_path / "TMS" / "session_id.txt"
)
cookies_management_path_dg = (
    rpa_session_management_default_path / "DG" / "cookies_dg.pkl"
)

session_management_path_dg = (
    rpa_session_management_default_path / "DG" / "local_storage_dg.pkl"
)
session_management_path_global_ime = (
    rpa_session_management_default_path / "GLOBALBANK" / "local_storage_global_ime.json"
)


url_login_dgtrade = "https://dgtrade.trishakti.com.np:8080/bom/index.html#/login"
# DG CREDENTIALS
credentials_dg = {"username": "AUTOBOT", "password": "Autom@ti0n"}
# credentials_dg = {"username": "PRABIN", "password": "Trishakti@48"}





# BASE URL TMS
base_url_tms = "https://tms48.nepsetms.com.np"


credentials_tms = {
    "username": "DEV-PROD",
    "password": "Dev.Prod@319",
    "server_id": "105675",
}


credentials_tms_for_collateral_only = {
    "username": "DEV-TEST",
    "password": "Dev@Test90",
    "server_id": "105674",
}
