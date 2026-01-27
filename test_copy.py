from db import db
import requests
from config import config
# ---------------- API HELPERS ----------------
def get_token(username=config.dg_api_userName, password=config.dg_api_password):
    resp = requests.post(
        config.LOGIN_API,
        json={"userName": username, "password": password},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json().get("token")


def get_accode(nepse_code, token):
    resp = requests.get(
        config.AC_CODE_API,
        headers={"Authorization": f"Bearer {token}"},
        params={"nepseCode": nepse_code},
        timeout=30
    )
    resp.raise_for_status()
    return resp.text

def get_kyc_details(ac_code, token):
    resp = requests.get(
        config.KYC_API,
        headers={"Authorization": f"Bearer {token}"},
        params={"acCode": ac_code},
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()




# df = db.get_unique_client_code_from_floorsheet()
# df.rename(columns={'clientcode': 'Client Code'}, inplace=True)
# # After creating/renaming df
# df.columns = [str(col) for col in df.columns]
# df['Client Name'] = ''
# df['Occupation'] = ''
# df['Company'] = ''
# token = get_token()

# for idx, row in df.iterrows():
#     if str(row['Client Name']).strip():
#         continue

#     nepse_code = str(row['Client Code']).upper()
#     accode = get_accode(nepse_code=nepse_code, token=token)
#     response = get_kyc_details(ac_code=accode, token=token)

#     name = response.get('client', {}).get('clientName', '')
#     occ = None
#     comp = None

#     occ_list = response.get('occupation', [])
#     if occ_list and isinstance(occ_list, list):
#         o = occ_list[0]
#         occ  = o.get('occupation', None)
#         comp = o.get('organizationName', None)

#     df.loc[idx, 'Client Name'] = name
#     df.loc[idx, 'Occupation']  = occ
#     df.loc[idx, 'Company']     = comp
#     print(f"Processing completed: {nepse_code}, {occ}, {comp}")
#     if idx == 5:
#         break

# df.to_excel("info.xlsx", index=False)







from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock


def fetch_client_info(idx, nepse_code, token):
    try:
        accode = get_accode(nepse_code=nepse_code, token=token)
        response = get_kyc_details(ac_code=accode, token=token)

        name = response.get('client', {}).get('clientName', '')
        occ = ''
        comp = ''

        occ_list = response.get('occupation', [])
        if isinstance(occ_list, list) and occ_list:
            o = occ_list[0]
            occ = o.get('occupation', '')
            comp = o.get('organizationName', '')

        return idx, nepse_code, name, occ, comp

    except Exception as e:
        return idx, nepse_code, '', '', ''



df = db.get_unique_client_code_from_floorsheet()
df.rename(columns={'clientcode': 'Client Code'}, inplace=True)
df.columns = df.columns.astype(str)

df['Client Name'] = ''
df['Occupation'] = ''
df['Company'] = ''

token = get_token()
tasks = []
rows_to_process = []

for idx, row in df.iterrows():
    if str(row['Client Name']).strip():
        continue

    nepse_code = str(row['Client Code']).upper()
    rows_to_process.append((idx, nepse_code))

total = len(rows_to_process)
processed = 0
lock = Lock()

print(f"🚀 Total records to process: {total}")
with ThreadPoolExecutor(max_workers=6) as executor:
    futures = [
        executor.submit(fetch_client_info, idx, nepse_code, token)
        for idx, nepse_code in rows_to_process
    ]

    for future in as_completed(futures):
        idx, nepse_code, name, occ, comp = future.result()

        # Update DataFrame safely (main thread only)
        df.loc[idx, 'Client Name'] = name
        df.loc[idx, 'Occupation'] = occ
        df.loc[idx, 'Company'] = comp

        # Progress tracking
        with lock:
            processed += 1
            remaining = total - processed

        print(f"✅ {processed}/{total} processed | "f"⏳ Remaining: {remaining} | "f"Client Code: {nepse_code} | "f"OCCUPATION: {occ} | "f"COMPANY: {comp}")
df.to_excel("info.xlsx", index=False)
