import pandas as pd
from db import db

# Load KYC data
rows = db.get_kyc()
df_kyc = pd.DataFrame(rows, columns=['client_code', 'client_fullname', 'branch', 'boid'])

# Load mapped data
df_mapped = pd.read_excel(r"C:\Users\Prabin\Desktop\mapping client till 31-01-2026.xlsx")  # has column "CLIENT ID"

# Merge on client ID vs client_code
df_merge = df_mapped.merge(
    df_kyc,
    left_on="CLIENT ID",
    right_on="client_code",
    how="left",   # keep all mapped clients
    indicator=True  # adds a column "_merge" showing match status
)

# Assign status based on merge indicator
df_merge["Status"] = df_merge["_merge"].apply(
    lambda x: "MATCHED" if x == "both" else "NOT MATCHED"
)

# Drop the helper column if not needed
df_merge = df_merge.drop(columns=["_merge"])

df_merge.to_excel("mani.xlsx", index=False)