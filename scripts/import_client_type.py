import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from db import db

FILE = r"C:\Users\anjit\Downloads\clients Moniter (1).xlsx"

SHEET_MAP = {
    "Peps Clients": "PEPS",
    "Special Clients": "SPECIAL CLIENT",
}

kyc_rows = db.get_kyc()
code_to_name = {}
for row in kyc_rows:
    code = str(row[0]).strip() if row[0] else ""
    name = str(row[1]).strip() if row[1] else ""
    if code:
        code_to_name[code] = name

xls = pd.ExcelFile(FILE)
total = 0
skipped = 0
for sheet_name, client_type in SHEET_MAP.items():
    if sheet_name not in xls.sheet_names:
        print(f"Sheet '{sheet_name}' not found, skipping")
        continue
    df = pd.read_excel(xls, sheet_name=sheet_name)
    codes = df["Clients Code"].astype(str).str.strip().tolist()
    for code in codes:
        if not code or code.lower() in ("nan", "none", ""):
            continue
        client_name = code_to_name.get(code, "")
        if not client_name:
            skipped += 1
            print(f"  SKIPPED {code} -> no KYC name found")
            continue
        try:
            db.insert_notable_client(
                client_code=code,
                client_name=client_name,
                reason="",
                noted_by="ADMIN",
                client_type=client_type,
            )
            total += 1
            print(f"  Inserted {code} ({client_name}) -> {client_type}")
        except Exception as e:
            print(f"  Error inserting {code}: {e}")

print(f"\nDone. {total} inserted, {skipped} skipped (no KYC name).")
