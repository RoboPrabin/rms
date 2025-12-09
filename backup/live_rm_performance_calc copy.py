from live_bro_performance_func.bro_data import separate_data_by_bro_in_folder
from api.dg.api_rm_list import fetch_all_rms
import os
from time import sleep
from api.tms.api_tms_order_book import fetch_trade_order_book
from api.dg.api_due_list import fetch_due_list
from datetime import datetime
from utils.helper import show_message, show_message_box, get_holding_engine
import pandas as pd
import psycopg2
from sqlalchemy import create_engine


def extract_rm_child_data(filepath: str):
    # Database connection details
    host = "192.168.1.14"
    dbname = "trishakti_db"
    user = "postgres"
    password = "Broker48"
    port = "5432"

    # Output file
    show_message(message="Extracting RM Child Data from DB....", color="green")
    conn = None
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=host, dbname=dbname, user=user, password=password, port=port
        )
        print("✅ Database connection successful.")

        # Create cursor and execute join query
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.rm_name, b.client_code
            FROM rm_tbl a
            INNER JOIN client_rm b
            ON a.u_id = b.rm_id;
        """
        )

        # Fetch rows and column names
        rows = cur.fetchall()
        col_names = [desc[0] for desc in cur.description]

        # Create DataFrame
        df = pd.DataFrame(rows, columns=col_names)
        print(f"📄 {len(df)} rows fetched.")
        df.rename(columns={"client_code": "clientCode"}, inplace=True)
        # Save to Excel
        df.to_excel(filepath, index=False)
        print(f"✅ Data exported to '{filepath}'.")
        return filepath
    except Exception as e:
        print("❌ Error:", e)

    finally:
        if conn:
            conn.close()
            print("🔒 Database connection closed.")


def today_folder_path(folder_path: str):
    """
    Check if the folder path contains today's date.
    """
    filename = str(folder_path).split("\\")[-1]
    return folder_path.replace(filename, "")[:-1]


def fetch_order_book():
    duelist_filepath = fetch_due_list()
    folder_path = today_folder_path(folder_path=duelist_filepath)
    show_message(message=f"Folderpath: {folder_path}")
    duelist_df = pd.read_excel(duelist_filepath)
    
    rm_filepath = extract_rm_child_data(filepath=r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\Whole Rm List.xlsx")
    rm_df = pd.read_excel(rm_filepath)
    tms_all_client_filepath = (r"D:\Trishakti\Projects\RPA\track_stock_price\data\output\tms_client_data.xlsx")
    orderbook_df = fetch_trade_order_book()

    # Load the Excel files
    # orderbook_df = pd.read_excel(order_book_filepath)
    rm_df["clientCode"] = rm_df["clientCode"].astype(str)

    tms_all_client_df = pd.read_excel(tms_all_client_filepath)

    merged_df = orderbook_df.merge(
        duelist_df[
            [
                "clientCode",
                "clientName",
                "branch",
                "collateral",
                "mobile",
                "adjustedBalance",
            ]
        ],
        left_on="clientMemberCode",
        right_on="clientCode",
        how="left",
    )

    # Merge dataframes to match clientmembercode and update clientName with clientfullname
    merged_df = merged_df.merge(
        tms_all_client_df[["clientmembercode", "clientfullname", "clientbranch"]],
        left_on="clientMemberCode",
        right_on="clientmembercode",
        how="left",
    )

    # Update clientName with clientfullname where matched, keep original clientName if no match
    merged_df["clientName"] = merged_df["clientfullname"].combine_first(
        merged_df["clientName"]
    )

    # Drop the redundant clientfullname and clientmembercode columns
    merged_df = merged_df.drop(
        columns=["clientfullname", "clientmembercode"], errors="ignore"
    )

    merged_df["clientName"] = (
        merged_df["clientName"].str.split("[").str[0].fillna("N/F")
    )
    merged_df["branch"] = merged_df["branch"].fillna("N/F")
    merged_df["collateral"] = merged_df["collateral"].fillna(0)
    merged_df["mobile"] = merged_df["mobile"].fillna("N/F")
    merged_df["adjustedBalance"] = merged_df["adjustedBalance"].fillna(0)

    merged_df = merged_df.rename(columns={"adjustedBalance": "ledgerBalance"})
    merged_df["adjustedBalance"] = merged_df["ledgerBalance"] + merged_df["netAmount"]
    merged_df = merged_df.drop(columns=["clientCode"], errors="ignore")

    # Merge with rm_child_data to extract Rm Name
    merged_df_with_rm = merged_df.merge(
        rm_df[["clientCode", "rm_name"]],
        left_on="clientMemberCode",
        right_on="clientCode",
        how="left",
    )

    # Fill NaN values for unmatched Rm Name
    merged_df_with_rm["rm_name"] = merged_df_with_rm["rm_name"].fillna("N/A")
    merged_df_with_rm["clientbranch"] = merged_df_with_rm["clientbranch"].fillna("N/F")

    # Convert clientName and clientbranch to uppercase
    merged_df_with_rm["clientName"] = merged_df_with_rm["clientName"].str.upper()
    merged_df_with_rm["clientbranch"] = merged_df_with_rm["clientbranch"].str.upper()
    merged_df_with_rm['dateTime'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    desired_columns = [
        "rm_name",
        "clientMemberCode",
        "clientName",
        "clientbranch",
        "buy/sell",
        "buyAmount",
        "sellAmount",
        "netAmount",
        "ledgerBalance",
        "adjustedBalance",
        "collateral",
        "dateTime"
    ]

    # Reorder columns
    merged_df_with_rm = merged_df_with_rm[
        desired_columns
        + [col for col in merged_df_with_rm.columns if col not in desired_columns]
    ]
    merged_df_with_rm.drop(
        columns=["clientCode", "branch", "mobile"], inplace=True, errors="ignore"
    )
    # merged_df_with_rm.sort_values(by='rm_name', inplace=True)
    merged_df_with_rm = merged_df_with_rm.sort_values(
        by=["rm_name", "netAmount"], ascending=[True, True]
    )
    merged_df_with_rm = merged_df_with_rm.rename(columns={"rm_name": "rmName"})
    merged_df_with_rm = merged_df_with_rm.rename(columns={"clientbranch": "branch"})

    engine = create_engine(get_holding_engine())
    merged_df_with_rm.to_sql(
    "order_book",        
    engine,              
    if_exists="replace",  
    index=False          
    )

    show_message(f"Data dumbed to db.", color="green")





   

if __name__ == "__main__":
    while True:
        fetch_order_book()
        print("Waiting for 30 sec")
        sleep(30)