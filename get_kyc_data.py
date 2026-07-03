import pandas as pd
import numpy as np
from db.db import get_connection

conn = get_connection()

def get_kyc_data():
    query = "SELECT * FROM kyc"
    df = pd.read_sql(query, conn)
    
    return df


def export_kyc_to_excel(output_path="kyc_data.xlsx"):
    df = get_kyc_data()

    for col in df.columns:
        if df[col].dtype in (np.int64, np.float64):
            if df[col].min() > 1e12 or df[col].max() > 1e12:
                df[col] = df[col].astype(str)

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="KYC")

    print(f"KYC data exported to {output_path}")
    return df


if __name__ == "__main__":
    export_kyc_to_excel()