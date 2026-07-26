import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from utils import helper

intranet_engine = helper.get_holding_engine()

def main():
    print("Fetching client_rm_map data...")
    query = 'SELECT * FROM client_rm_map'
    df = pd.read_sql(query, intranet_engine)

    if df.empty:
        print("No data found.")
        return

    print(f"Total rows: {len(df)}")

    output_file = "Client_RM_Map.xlsx"
    df.to_excel(output_file, index=False)
    print(f"Data exported to: {output_file}")

if __name__ == "__main__":
    main()
