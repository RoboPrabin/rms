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

def format_negative_numbers(df):
    df = df.map(lambda x: f"({abs(x):,})" if isinstance(x, (int, float)) and x < 0 else f"{x:,}" if isinstance(x, (int, float)) else x)
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
key = os.getenv("SECRET_KEY")
if not key:
    raise ValueError("SECRET_KEY not found in environment variables")

cipher = Fernet(key.encode())

def encrypt_password(password: str) -> str:
    encrypted = cipher.encrypt(password.encode())
    return encrypted.decode()

def decrypt_password(encrypted_password: str) -> str:
    decrypted = cipher.decrypt(encrypted_password.encode())
    return decrypted.decode()

@st.cache_resource
def get_holding_engine()->str:
    return f"postgresql+psycopg2://{config.postgresql_config['db_user']}:{config.postgresql_config['db_password']}@{config.postgresql_config['db_host']}:{config.postgresql_config['db_port']}/{config.postgresql_config['db_name']}"

@st.cache_resource
def get_intranet_engine()->str:
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
