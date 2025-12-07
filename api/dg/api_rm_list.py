from time import sleep
from ui.login_dg import login_dg
import pandas as pd
from api.dg.shared_api_dg import get_headers
from utils.helper import get_today_date, show_message
import requests


def get_rm_clients_total_pages(rm_id, branch_id):
    while True:
        try:
            params = {
                    'pageNumber': '0',
                    'dateFrom': '2024-07-16',
                    'dateTo': get_today_date(),
                    'reportType': 'relationOfficer',
                    'agentId': rm_id,
                    'branch': branch_id,
                    'relationOfficerType': 'I',

                }

            response = requests.get(
                'https://dgtrade.trishakti.com.np:8080/bom/api/customer/customer-registration/relation-officer-wise-detail',
                params=params,
                headers=get_headers(),
            )

            if response.status_code == 200:
                total_pages = response.json().get('totalPages', 0)
                return total_pages
            else:
                login_dg()
        except Exception as e:
            sleep(2)

def get_clients_of_rm(rm_df:pd.DataFrame, working_dir:str):
    data = []
    for index, row in rm_df.iterrows():
        rm_id = str(row['rm_id'])
        branch_id = str(row['branch_id'])
        rm_name = str(row['userCode'])
        show_message(f"Extracting data for rm {rm_id}")
        total_pages = get_rm_clients_total_pages(rm_id=rm_id, branch_id=branch_id)
        show_message(f" ->total pages = {total_pages}")
        for x in range(0, total_pages+1):
            show_message(f"  ->->Extracting from page no {x}/{total_pages}")
            params = {
                'pageNumber': str(x),
                'dateFrom': '2024-07-16',
                'dateTo': get_today_date(),
                'reportType': 'relationOfficer',
                'agentId': rm_id,
                'branch': branch_id,
                'relationOfficerType': 'I',

            }

            while True:
                try:
                    response = requests.get(
                        'https://dgtrade.trishakti.com.np:8080/bom/api/customer/customer-registration/relation-officer-wise-detail',
                        params=params,
                        headers=get_headers(),
                    )

                    if response.status_code == 200:
                        # total_pages = response.json().get('totalPages', 0)
                        raw_data = response.json().get('data', [])
                        new_data = [
                                {
                                    "clientName": item["clientName"],
                                    "rm_name": rm_name,
                                    # "branch": item['branchCode'],
                                    
                                }
                                for item in raw_data
                            ]
                        data.extend(new_data)
                        break
                    else:
                        login_dg()
                except Exception as e:
                    sleep(2)

    df = pd.DataFrame(data)
    df['clientCode'] = df['clientName'].str.extract(r'^(.*?)\s*\[(.*?)\]$')[1]
    df['clientName'] = df['clientName'].str.extract(r'^(.*?)\s*\[(.*?)\]$')[0]

    filepath = working_dir + "\\" + "rm_child_data.xlsx"
    show_message(f"RM child ata filepath : {filepath}")
    df.to_excel(filepath, index=False)
    return filepath


def fetch_all_rms(working_dir:str):
    show_message("Fetching RM Data. Please wait . . . .", "yellow")
    data = []
    for x in range(1,7):
        params = {
            'pageNumber': '0',
            'dateFrom': '2024-07-16',
            'dateTo': get_today_date(),
            'reportType': 'relationOfficer',
            'branch': str(x),
            'relationOfficerType': 'I',

        }
       
        while True:
            try:
                show_message(f"Extracting rm of branch {x}")
                response = requests.get(
                    'https://dgtrade.trishakti.com.np:8080/bom/api/customer/customer-registration/relation-officer-wise',
                    params=params,
                    # cookies=cookies,
                    headers=get_headers(),
                )

                if response.status_code == 200:
                    raw_data = response.json().get('data', [])
                    new_data = [
                            {
                                "userCode": item["userName"],
                                "rm_id": item["id"],
                                "branch": item['branchCode'],
                                "branch_id": x 
                            }
                            for item in raw_data
                        ]
                    data.extend(new_data)
                    break
                else:
                    login_dg()
            except Exception as e:
                sleep(2)

    rm_df =pd.DataFrame(data)
    # rm_df.to_excel("rm_list.xlsx", index=False)
    rm_child_data_filepath = get_clients_of_rm(rm_df=rm_df, working_dir=working_dir)
    show_message(f"RM Child data filepath: {rm_child_data_filepath}")

    return rm_child_data_filepath

if __name__ == "__main__":
    fetch_all_rms(working_dir=r"C:\Users\Robot\Desktop\rmdata")