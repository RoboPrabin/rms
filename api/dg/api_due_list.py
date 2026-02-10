import requests
from api.dg.shared_api_dg import get_headers
from ui.login_dg import login_dg
from utils.helper import (get_tplustwo_date, 
                          create_folder_with_datetime, 
                          get_date_from_folderpath, 
                          show_message, update_due_list_flag, 
                          has_downloaded_due_list_today,
                          get_folder_path_from_flag)
import pandas as pd



def extract_client_code_from_duelist(duelist_filepath: str) -> None:
    """
    Reads a duelist file, extracts the client code from clientName 
    by splitting and slicing, adds it as a new column 'clientCode',
    and saves back to the same file.
    
    :param duelist_filepath: Path to the duelist Excel file
    """
    # Read the duelist Excel file
    df_duelist = pd.read_excel(duelist_filepath)

    # Define a function to extract code using split and slice
    def extract_code(name):
        if isinstance(name, str):
            parts = name.strip().split(' ')
            if parts:
                last_part = parts[-1]
                return last_part[1:-1]  # Remove the '[' and ']'
        return None  # Safe fallback

    # Apply the function to clientName
    df_duelist['clientCode'] = df_duelist['clientName'].apply(extract_code)
    df_duelist['adjustedBalance'] = df_duelist['adjustedBalance'] * -1

    # Save back to the same file (overwrite)
    df_duelist.to_excel(duelist_filepath, index=False)

    show_message(f"Successfully extracted clientCode and updated file: {duelist_filepath}")


def fetch_due_list():
    if not has_downloaded_due_list_today():
        show_message("Fetching due report from dg. Please Wait ...")
        while True:
            params = {
                'pageNumber': '0',
                'date': get_tplustwo_date(),
                'dueType': 'DR',
                'otherDp': 'false',
                'ownDp': 'false',
            }

            response = requests.get('https://dgtrade.trishakti.com.np:8080/bom/api/account/report/due', params=params, headers=get_headers())
            if response.status_code == 200:
                show_message("Due Report fetched successfully.", 'green')
                folder_path = create_folder_with_datetime()
                date_name = get_date_from_folderpath(folder_path)
                filepath = f"{folder_path}\\due_report_{date_name}.xlsx"
                pd.DataFrame(response.json()).to_excel(filepath, index=False)

                extract_client_code_from_duelist(duelist_filepath=filepath) 
                update_due_list_flag(filepath=filepath)
                break
            else:
                show_message("❌ API call failed", 'red')
                login_dg()

    else:
        filepath = get_folder_path_from_flag()
        show_message("Due list already downloaded today at " + filepath, 'green')
    return filepath