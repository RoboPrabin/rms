import pandas as pd
import re
from seleniumwire import webdriver
from config.config import session_management_path_tms, output_folder_path,session_management_path_dg
import json
import os
import tkinter as tk
from tkinter import messagebox
import termcolor
from datetime import datetime
import streamlit as st
from config import config
from cryptography.fernet import Fernet
import re
import socket
import requests
from streamlit_javascript import st_javascript
from datetime import datetime, timedelta
from config.config import due_list_flag_path
import secrets
import string
from typing import Final
import nepali_datetime

# def get_user_agent() -> str:
#     js = """
#     <script>
#     const userAgent = navigator.userAgent;
#     document.querySelector('body').setAttribute('data-user-agent', userAgent);
#     </script>
#     """
#     st.markdown(js, unsafe_allow_html=True)
    
#     # Try to read back via query params (requires page reload if complex)
#     try:
#         user_agent = st.session_state.get("user_agent", None)
#         if user_agent:
#             return user_agent
#     except Exception:
#         pass
    
#     # fallback
#     return "Unknown"
def rename_all_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename all DataFrame columns by converting snake_case to Title Case with spaces.
    
    Example:
        citizenship_number -> Citizenship Number
        status -> Status
        created_at -> Created At
    """
    def format_col(col: str) -> str:
        # Replace underscores with spaces, capitalize each word
        return col.replace("_", " ").title()
    
    new_columns = {col: format_col(col) for col in df.columns}
    return df.rename(columns=new_columns)



def validate_phone(phone: str) -> bool:
    """
    Validate a phone number:
    - Must be exactly 10 digits
    - Must start with 9
    """
    # Regex: start with 9, followed by 9 digits (total 10)
    pattern = r"^9\d{9}$"
    return bool(re.match(pattern, phone))


def validate_email(email: str) -> bool:
    """
    Validate an email address using regex.
    Returns True if valid, False otherwise.
    """
    if not email:
        return False

    # Basic RFC 5322 compliant regex for email validation
    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    return re.match(pattern, email) is not None


def convert_ad_to_bs(ad_date: str) -> str:
    try:
        ad_dt = datetime.strptime(ad_date, "%Y-%m-%d")
        bs_date = nepali_datetime.date.from_datetime_date(ad_dt.date())
        return bs_date.strftime("%Y-%m-%d")
    except Exception as e:
        return ""


def get_default_platforms():
    return  [
            "TMS",
            "DG",
            "webcdas",
            "CM",
            "OFFICIAL_EMAIL",
            "OFFICIAL_PHONE_NUMBER"
        ]
def get_employee_types():
    return  [
            "BRO",
            "FRO",
            "GENERAL STAFF",
            "INTERN",]

def get_work_locations():
    return  [
            "KATHMANDU",
            "LALITPUR",
            "BANEPA",
            "POKHARA",
            "HETAUDA",
            "MAHENDRANAGAR",
        ]

def eliminate_top_padding():
    st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem;  /* Adjust or set to 0rem */
        }
    </style>
    """, unsafe_allow_html=True)


def get_platform_options():
    return {
        "Webcdas":"https://webcdas.cdsc.com.np/",
        "DG":"https://dgtrade.trishakti.com.np:8080/bom/index.html#/login",
        "RMS":"https://holdings.trishakti.com.np:9999/",
        "Customer Screening": "http://192.168.1.177:8099/CustomerAccount/Login?ReturnUrl=%2F",
        "Gmail": "https://mail.google.com",
        "Facebook": "https://facebook.com",
        "Instagram": "https://instagram.com",
        "Twitter (X)": "https://twitter.com",
        "LinkedIn": "https://linkedin.com",
        "Outlook": "https://outlook.com",
        "GitHub": "https://github.com",
        "GitLab": "https://gitlab.com",
        "Custom": ""   
    }


def get_alias_name(loggedin_username:str):
    # 1) Get all clientCodes assigned to this RM
    query_clients = """
        SELECT alias
        FROM app_user
        WHERE username = %s
    """
    loggedin_username = pd.read_sql(query_clients,get_holding_engine(), params=(loggedin_username,))
    alias = loggedin_username.loc[0, "alias"]
    return alias



def generate_secure_password(length: int = 12) -> str:
    """
    Generate a cryptographically secure random password
    with uppercase, lowercase, digits, and symbols.
    """

    if length < 8:
        raise ValueError("Password length must be at least 8 characters")

    UPPER: Final = string.ascii_uppercase
    LOWER: Final = string.ascii_lowercase
    DIGITS: Final = string.digits
    SYMBOLS: Final = "!@#$%?"

    ALL_CHARS: Final = UPPER + DIGITS + SYMBOLS

    # Ensure at least one character from each category
    password_chars = [
        secrets.choice(UPPER),
        secrets.choice(DIGITS),
        secrets.choice(SYMBOLS),
    ]

    # Fill the remaining length
    for _ in range(length - len(password_chars)):
        password_chars.append(secrets.choice(ALL_CHARS))

    # Shuffle to avoid predictable placement
    secrets.SystemRandom().shuffle(password_chars)

    return "".join(password_chars)





def get_today_date():
    today = datetime.now()
    formatted_date = today.strftime('%Y-%m-%d')
    return formatted_date


def get_date_from_folderpath(folderpath):
    # Extract the date from the folder path
    date_str = folderpath.split("\\")[-1]  # Get the last part of the path
    return date_str


def update_due_list_flag(filepath:str):
    """
    Update the due list flag file with today's date.
    
    :return: None
    """
    # Get today's date in 'YYYY-MM-DD' format
    # today_date = get_today_date()
    
    # Write today's date to the flag file
    with open(due_list_flag_path, 'w') as file:
        file.write(filepath)

def has_downloaded_due_list_today()-> bool:
    """
    Check if the due list has been downloaded today.
    
    :return: True if the due list has been downloaded today, False otherwise.
    """
    # Get today's date in 'YYYY-MM-DD' format
    today_date = datetime.now().strftime('%d-%b-%Y')

    # Check if the file exists and if its name contains today's date
    if os.path.exists(due_list_flag_path):
        with open(due_list_flag_path, 'r') as file:
            content = file.read()
            return today_date in content
    return False

def get_folder_path_from_flag()-> str:
    """
    Get the folder path from the due list flag file.
    
    :return: The folder path if it exists, otherwise None.
    """
    if os.path.exists(due_list_flag_path):
        with open(due_list_flag_path, 'r') as file:
            content = file.read()
            return content.strip()
    return None


def get_tplustwo_date():
    tplustwo = datetime.now() + timedelta(days=2)
    formatted_date = tplustwo.strftime('%Y-%m-%d')
    return formatted_date


def get_list_of_status_for_communication_report(role:str):
    if role.upper() == "BRO":
        return ["PENDING", "POSTPONED", "CANCELLED", "COMPLETED"]
    else:
        return ["PENDING", "APPROVED", "POSTPONED", "CANCELLED"]


def get_list_of_status_for_project_request():
    return ["PIPELINE", "IN-PROGRESS", "COMPLETED", "DROPPED"]



def get_user_agent():
    user_agent = st_javascript("navigator.userAgent")
    return user_agent

def prettify_columns(df: pd.DataFrame) -> pd.DataFrame:
    def convert(col: str) -> str:
        # Replace underscores with spaces
        col = col.replace("_", " ")
        # Insert space before capital letters (camelCase → camel Case)
        col = re.sub(r'(?<!^)(?=[A-Z])', ' ', col)
        # Title case the whole string
        return col.strip().title()
    
    df = df.rename(columns={col: convert(col) for col in df.columns})
    return df


def get_client_ip() -> str:
    try:
        # Attempt 1: Streamlit server info (works in some deployments)
        server_info = st.runtime.scriptrunner.get_script_run_ctx()
        if server_info and hasattr(server_info, 'session_info'):
            # Some Streamlit deployments may expose session info
            ip = server_info.session_info.user_ip
            if ip:
                return ip
    except Exception:
        pass

    try:
        # Attempt 2: External service (works if internet available)
        ip = requests.get("https://api.ipify.org").text
        return ip
    except Exception:
        pass

    try:
        # Attempt 3: Local IP fallback
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip
    except Exception:
        pass

    # Default if everything fails
    return "0.0.0.0"


# def show_message(message: str, color: str='white'):
#     current_time = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")  
#     print(termcolor.colored(f" [{current_time}] {message.upper()}", color))

def validate_phone(phone: str) -> bool:
    """
    Validate a phone number:
    - Must be exactly 10 digits
    - Must start with 9
    """
    # Regex: start with 9, followed by 9 digits (total 10)
    pattern = r"^9\d{9}$"
    return bool(re.match(pattern, phone))


def is_valid_password(password: str) -> bool:
    """
    Validates a password:
    - Minimum 6 characters
    - At least 1 uppercase letter
    - At least 1 digit
    - At least 1 special symbol
    """
    if len(password) < 6:
        return False

    # Regex: uppercase, digit, symbol
    pattern = r'^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$'
    return bool(re.match(pattern, password))

# def format_negative_numbers(df):
#     df = df.map(lambda x: f"({abs(x):,})" if isinstance(x, (int, float)) and x < 0 else f"{x:,}" if isinstance(x, (int, float)) else x)
#     return df

def is_valid_email(email: str) -> bool:
    """
    Validate an email address using regex.
    Returns True if valid, False otherwise.
    """
    if not email:
        return False

    # Basic RFC 5322 compliant regex for email validation
    pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    return re.match(pattern, email) is not None


def format_negative_numbers(df):
    def fmt(x):
        if isinstance(x, (int, float)):
            return f"({abs(x):,})" if x < 0 else f"{x:,}"
        return x
    
    for col in df.columns:
        if col.lower() != "boid":       # skip boid intelligently
            df[col] = df[col].map(fmt)
    
    return df


def adjust_ui():
    st.markdown("""
           <style>
               div[data-testid="stVerticalBlock"]:not(section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]) {
                    margin-top: 0px !important;
                }
            </style>
            """, unsafe_allow_html=True)

def hide_login_page():
    st.markdown("""
    <style>
        /* Hide the Login page (first item) forever */
        section[data-testid="stSidebarNav"] li:nth-child(1) {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)

def default_ttl():
    return 63

def get_hero_role():
    return ['MANAGER', 'ADMIN']


def logout_if_unauthorized():
    role = get_hero_role()
    if not st.session_state['role'] in role:
        st.error("You are not authorized to access this page.", icon=':material/warning:')
        # if st.button("Go to login page"):
        #     st.switch_page("Homepage.py")
        st.stop()
        
# Load key from environment
# key = os.getenv("SECRET_KEY")
# if not key:
#     raise ValueError("SECRET_KEY not found in environment variables")

# cipher = Fernet(key.encode())

# def encrypt_password(password: str) -> str:
#     encrypted = cipher.encrypt(password.encode())
#     return encrypted.decode()

# def decrypt_password(encrypted_password: str) -> str:
#     decrypted = cipher.decrypt(encrypted_password.encode())
#     return decrypted.decode()

@st.cache_resource
def get_holding_engine()->str:
    return f"postgresql+psycopg2://{config.postgresql_config['db_user']}:{config.postgresql_config['db_password']}@{config.postgresql_config['db_host']}:{config.postgresql_config['db_port']}/{config.postgresql_config['db_name']}"

@st.cache_resource
def get_intranet_engine()->str:
    # return f"postgresql+psycopg2://{config.postgresql_config['db_user']}:{config.postgresql_config['db_password']}@172.17.26.6:{config.postgresql_config['db_port']}/{'trishakti_db'}"
    return f"postgresql+psycopg2://{config.postgresql_config['db_user']}:{config.postgresql_config['db_password']}@{config.postgresql_config['db_host']}:{config.postgresql_config['db_port']}/{'trishakti_db'}"

def hide_components():
    # Hide sidebar
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: none; }
            .block-container { padding-top: 2rem; }
        </style>
    """, unsafe_allow_html=True)


    st.markdown("""
        <style>
            h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {
                text-decoration: none !important;
                visibility: hidden !important;
            }
        </style>
    """, unsafe_allow_html=True)

    return st

def convert_columns_to_str(df:pd.DataFrame):
    df['boid'] = df['boid'].astype(str)
    df['ledgerBalance'] = pd.to_numeric(df['ledgerBalance'], errors='coerce').fillna(0.0)
    df['ledgerBalance'] = df['ledgerBalance'].apply(lambda x: f"{x:.2f}")
    df['ledgerBalance'] = df['ledgerBalance'].astype(float)
    return df


def camel_to_title(name):
    s1 = re.sub('([a-z])([A-Z])', r'\1 \2', name)
    return s1.title()

def format_with_comma(x):
    if pd.api.types.is_numeric_dtype(x):
        return x.apply(lambda val: f"{val:,.0f}" if pd.notna(val) else "")
    return x


def format_dataframe(df: pd.DataFrame):
    df = df.rename(columns=camel_to_title)
    
    def add_comma(x):
        return f"{x:,.2f}" if pd.notna(x) else ""
    
    # All numeric columns
    numeric_cols = df.select_dtypes(include=['number']).columns
    
    # Exclude "Boid" (case-insensitive & strip spaces)
    cols_to_format = [col for col in numeric_cols if col.strip().lower() != "boid"]
    
    # Apply comma formatting only to selected columns
    df[cols_to_format] = df[cols_to_format].map(add_comma)
    
    return df


# SHOW MESSAGES __________________________________________________________________
def show_message_box(title:str = "Demo purpose only", message:str = "Delete some data from summary report."):
    root = tk.Tk()
    root.attributes('-topmost', True)  
    root.withdraw()  # Hide the main window
    messagebox.showinfo(title=title, message=message)
    root.destroy()

def show_message(message: str, color: str='white'):
    current_time = datetime.now().strftime("%I:%M:%S %p")  # 12-hour format with AM/PM
    print(termcolor.colored(f" [{current_time}] {message.upper()}", color))

def show_message_debug(message: str, color: str='magenta'):
    current_time = datetime.now().strftime("%I:%M:%S %p") 
    print(termcolor.colored(f" [{current_time}] DEBUG: {message}", color))


# USER INPUT WORKS _______________________________________________________________
def ask_for_retry(msg:str='retry'):
    # Create the main application window (it won't be shown)
    root = tk.Tk()
    root.attributes('-topmost', True)  # Make sure it's on top
    root.withdraw()  # Hide the root window

    # Show the messagebox and store the response
    response = messagebox.askyesno("Question", f"Do you want to {msg}?")

    # Print the response (True for Yes, False for No)
    return response

def get_user_input(which_platform:str):
    root = tk.Tk()
    root.withdraw()  # Hide the main root window

    user_input = None
    while not user_input:
        custom_dialog = CustomDialog(root, "CAPTCHA", "Please enter captcha for " + which_platform, width=50)
        root.wait_window(custom_dialog.top)  # Wait until the dialog is closed
        user_input = custom_dialog.result
        if not user_input:
            # show_message(f"CAPTCHA entered: {user_input}", 'white')
        # else:
            print("No input provided. Please try again.")

    root.destroy()
    return user_input


def ensure_session_management_folder():
    # Get desktop path
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    
    # Define base hierarchy
    server_folder = os.path.join(desktop_path, "Server")
    rpa_folder = os.path.join(server_folder, "RPA")
    session_folder = os.path.join(rpa_folder, "SessionManagement")
    
    # Subfolders inside SessionManagement
    tms_folder = os.path.join(session_folder, "TMS")
    dg_folder = os.path.join(session_folder, "DG")
    globalbank_folder = os.path.join(session_folder, "GLOBALBANK")




# DG WORKS ______________________________________
def get_session_data():
    with open(session_management_path_dg, 'r') as f:
        local_storage = json.load(f)
        bom_session_id = dict(local_storage).get('bom-sessionId')
        em = dict(local_storage).get('em')
        tempem_list = json.loads(local_storage['tempem'])
        pn = tempem_list[2]
        token = dict(local_storage).get('token')
    return token, em, pn, bom_session_id

def save_cookies_data(driver:webdriver.Chrome):
    cookies = driver.get_cookies()
    with open(session_management_path_tms, 'w') as f:
        json.dump(cookies, f, indent=4)
    show_message(f"TMS Cookies saved to {session_management_path_tms}n", 'white')    

def update_cookies(session_id):
    # Load the existing JSON data
    with open(session_management_path_tms, 'r') as file:
        cookies = json.load(file)
    # Append new cookie entry
    new_cookie = {
        "domain": ".tms48.nepsetms.com.np",
        "expiry": 1744207577,
        "httpOnly": False,
        "name": "host-session-id",
        "path": "/",
        "sameSite": "Lax",
        "secure": True,
        "value": session_id
    }
    
    cookies.append(new_cookie)  # Add the new cookie
    
    # Save back to the file
    with open(session_management_path_tms, 'w') as file:
        json.dump(cookies, file, indent=4)

def read_cookies_from_file():
    with open(session_management_path_tms, 'r') as f:
        local_storage = json.load(f)
        xsrf_token_name = dict(local_storage[0]).get('name')
        xsrf_value = dict(local_storage[0]).get('value')

        aid_name = dict(local_storage[1]).get('name')
        aid_value = dict(local_storage[1]).get('value')

        rid_name = dict(local_storage[2]).get('name')
        rid_value = dict(local_storage[2]).get('value')

        host_session_id = dict(local_storage[3]).get('value')
        # print(host_session_id)
        return xsrf_value, aid_value, rid_value, host_session_id

def create_folder_with_datetime():
    """
    Creates a folder with the current date and time in 12-hour format (AM/PM).
    
    :param base_path: The directory where the new folder should be created.
    :return: The full path of the created folder.
    """
    # Format date-time as "YYYY-MM-DD hh-mm-ss AM/PM"
    # folder_name = datetime.now().strftime("%Y-%m-%d %I-%M-%S %p")
    folder_name = datetime.now().strftime("%d-%b-%Y %I-%M-%S %p")

    
    # Create full folder path
    folder_path = os.path.join(output_folder_path, folder_name)

    # Create the folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)

    return folder_path

class CustomDialog:
    def __init__(self, parent, title, prompt, width=30):
        self.result = None
        
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        
        tk.Label(self.top, text=prompt).pack(pady=10)

        self.entry = tk.Entry(self.top, width=width)
        self.entry.pack(pady=6)
        self.entry.pack(padx=5)
        
        self.entry.focus()

        # Bind the Enter key to the OK button
        self.entry.bind("<Return>", self.on_ok)

        button_frame = tk.Frame(self.top)
        button_frame.pack(pady=5)

        tk.Button(button_frame, text="   OK   ", command=self.on_ok).pack(side=tk.LEFT, padx=50)
        # tk.Button(button_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT)

        # Bring the window to the foreground and make it topmost
        self.top.lift()
        self.top.attributes("-topmost", True)
        self.top.after_idle(self.top.attributes, '-topmost', False)  # Remove topmost attribute after it's focused

        # Center the window on the screen
        self.center_window()

    def center_window(self):
        self.top.update_idletasks()  # Ensure the geometry information is up-to-date
        screen_width = self.top.winfo_screenwidth()
        screen_height = self.top.winfo_screenheight()
        window_width = self.top.winfo_width()
        window_height = self.top.winfo_height()

        position_right = int(screen_width / 2 - window_width / 2)
        position_down = int(screen_height / 2 - window_height / 2)

        self.top.geometry(f"+{position_right}+{position_down}")

    def on_ok(self, event=None):
        self.result = self.entry.get()
        self.top.destroy()

    def on_cancel(self):
        self.top.destroy()
