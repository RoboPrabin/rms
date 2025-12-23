import json
import requests
from db import db



userName = "tri-api"
password = "Bq!92Xw#Tz6@"

base_api = "https://dgtrade.trishakti.com.np:8080/bom/"

acCode_api = base_api + "tp-data/account/by-nepse"
login_api = base_api + "tp-data/authenticate"
ledger_api = base_api + "tp-data/account/ledger"

response = requests.post(login_api, json={"userName": userName, "password": password})

token  = response.json().get("token")
db.store_jwt_token(token)




# print(token)
# get_acCode_api = acCode_api
# response = requests.get(get_acCode_api, headers={"Authorization": f"Bearer {token}"}, params={"nepseCode": "KK294195"})
# ac_code = response.json()

# response = requests.get(ledger_api, headers={"Authorization": f"Bearer {token}"}, params={"acCode": ac_code, "dateFrom": "2024-01-01", "dateTo": "2024-02-31"})
# print(json.dumps(response.json(), indent=4))






# import streamlit as st
# import requests
# import pandas as pd

# # ---------------- CONFIG ----------------
# USER_NAME = "tri-api"
# PASSWORD = "Bq!92Xw#Tz6@"

# BASE_API = "https://dgtrade.trishakti.com.np:8080/bom/"
# LOGIN_API = BASE_API + "tp-data/authenticate"
# AC_CODE_API = BASE_API + "tp-data/account/by-nepse"
# LEDGER_API = BASE_API + "tp-data/account/ledger"


# # ---------------- API HELPERS ----------------
# def get_token(username, password):
#     resp = requests.post(
#         LOGIN_API,
#         json={"userName": username, "password": password},
#         timeout=30
#     )
#     resp.raise_for_status()
#     return resp.json().get("token")


# def get_account_code(token, nepse_code):
#     resp = requests.get(
#         AC_CODE_API,
#         headers={"Authorization": f"Bearer {token}"},
#         params={"nepseCode": nepse_code},
#         timeout=30
#     )
#     resp.raise_for_status()
#     return resp.json()


# def get_ledger(token, ac_code, date_from, date_to):
#     resp = requests.get(
#         LEDGER_API,
#         headers={"Authorization": f"Bearer {token}"},
#         params={
#             "acCode": ac_code,
#             "dateFrom": date_from,
#             "dateTo": date_to
#         },
#         timeout=30
#     )
#     resp.raise_for_status()
#     return resp.json()


# # ---------------- UI ----------------
# st.set_page_config(page_title="Ledger Viewer", layout="wide")
# st.title("📒 Client Ledger")

# with st.spinner("Fetching ledger data…"):
#     token = get_token(USER_NAME, PASSWORD)
#     ac_code = get_account_code(token, "20230716483")
#     ledger = get_ledger(token, ac_code, "2024-01-01", "2024-02-29")

# # ---------------- HEADER INFO ----------------
# st.subheader("Opening Summary")

# col1, col2, col3 = st.columns(3)

# col1.metric("Opening Balance", ledger.get("opening", 0))
# col2.metric("Current Balance", ledger.get("balance", "0.00"))
# col3.metric("Balance Type", ledger.get("balanceType", "-"))

# st.divider()

# # ---------------- MAIN LEDGER TABLE ----------------
# st.subheader("Ledger Transactions")

# data_rows = ledger.get("data", [])

# if not data_rows:
#     st.warning("No ledger transactions found.")
# else:
#     df_ledger = pd.DataFrame(data_rows)

#     # Optional: column ordering (corporate polish)
#     preferred_cols = [
#         "transactionDate",
#         "voucherNo",
#         "referenceNo",
#         "particulars",
#         "dr",
#         "cr",
#         "balance",
#         "balanceType",
#         "enteredBy",
#         "reconciled"
#     ]

#     existing_cols = [c for c in preferred_cols if c in df_ledger.columns]
#     df_ledger = df_ledger[existing_cols]

#     st.dataframe(df_ledger, use_container_width=True)

# # ---------------- UNBILLED TRANSACTIONS ----------------
# ubilled = ledger.get("ubilledTransactions", [])

# if ubilled:
#     st.divider()
#     st.subheader("Unbilled Transactions")

#     df_ubilled = pd.DataFrame(ubilled)

#     preferred_ubilled_cols = [
#         "transactionDate",
#         "particulars",
#         "debit",
#         "credit",
#         "balance",
#         "tr"
#     ]

#     existing_ub_cols = [c for c in preferred_ubilled_cols if c in df_ubilled.columns]
#     df_ubilled = df_ubilled[existing_ub_cols]

#     st.dataframe(df_ubilled, use_container_width=True)
# else:
#     st.info("No unbilled transactions available.")
