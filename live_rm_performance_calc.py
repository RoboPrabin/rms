
import os
import pickle

from ui.login_tms import login_tms
os.system("")

from live_bro_performance_func.bro_data import separate_data_by_bro_in_folder
from api.dg.api_rm_list import fetch_all_rms
import os
from time import sleep
from api.tms.api_tms_order_book import fetch_trade_book, fetch_order_book
from api.dg.api_due_list import fetch_due_list
from datetime import datetime
from utils.helper import show_message, show_message_box, get_holding_engine
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from datetime import datetime, time
import sys
from time import sleep



def extract_rm_child_data():
    engine = None
    conn = None
    try:
        # Create SQLAlchemy engine using your helper
        engine = create_engine(get_holding_engine())
        conn = engine.connect()
        show_message("✅ Database connection successful to client_rm_map for RM Child data.")

        # Execute query directly into DataFrame
        query = """
            SELECT "rmName", "clientCode"
            FROM client_rm_map
        """
        df = pd.read_sql(query, conn)
        show_message(f"   > RM child 📄 {len(df)} rows fetched.")
        # Rename columns for consistency
        df.rename(columns={"client_code": "clientCode"}, inplace=True)
        return df

    except Exception as e:
        print("❌ Error:", e)

    finally:
        if conn:
            conn.close()
        if engine:
            engine.dispose()

def extract_kyc_data():
    engine = None
    conn = None
    try:
        # Create SQLAlchemy engine using your helper
        engine = create_engine(get_holding_engine())
        conn = engine.connect()
        show_message("✅ Database connection successful to kyc for KYC Data.")

        # Execute query directly into DataFrame
        query = """
            SELECT "clientmembercode", "clientfullname", "clientbranch"
            FROM kyc
        """
        df = pd.read_sql(query, conn)
        show_message(f"   > KYC 📄 {len(df)} rows fetched.")
        return df

    except Exception as e:
        show_message("❌ Error:" + str(e), color='red')

    finally:
        if conn:
            conn.close()
        if engine:
            engine.dispose()

def today_folder_path(folder_path: str):
    """
    Check if the folder path contains today's date.
    """
    filename = str(folder_path).split("\\")[-1]
    return folder_path.replace(filename, "")[:-1]

def push_trade_book_to_db(merged_df_with_rm:pd.DataFrame):
    engine = create_engine(get_holding_engine())
    merged_df_with_rm.to_sql(
    "trade_book",        
    engine,              
    if_exists="replace",  
    index=False          
    )
    show_message(f"'TRADE BOOK' data dumbed to trade_book Table.", color="cyan")
    show_message(f"=" * 100)
    print("\n")

def fetch_order_and_trade_book():
    duelist_filepath = fetch_due_list()
    folder_path = today_folder_path(folder_path=duelist_filepath)
    duelist_df = pd.read_excel(duelist_filepath)
    
    rm_df = extract_rm_child_data()
    tms_all_client_df = extract_kyc_data()
    show_message(f"*" * 60)
    
    
    fetch_order_book()
    show_message(f"*" * 60)
    tradebook_df = fetch_trade_book()

    rm_df["clientCode"] = rm_df["clientCode"].astype(str)
    merged_df = tradebook_df.merge(
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
        rm_df[["clientCode", "rmName"]],
        left_on="clientMemberCode",
        right_on="clientCode",
        how="left",
    )

    # Fill NaN values for unmatched Rm Name
    merged_df_with_rm["rmName"] = merged_df_with_rm["rmName"].fillna("N/A")
    merged_df_with_rm["clientbranch"] = merged_df_with_rm["clientbranch"].fillna("N/F")

    # Convert clientName and clientbranch to uppercase
    merged_df_with_rm["clientName"] = merged_df_with_rm["clientName"].str.upper()
    merged_df_with_rm["clientbranch"] = merged_df_with_rm["clientbranch"].str.upper()
    merged_df_with_rm['dateTime'] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    desired_columns = [
        "rmName",
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
        by=["rmName", "netAmount"], ascending=[True, True]
    )
    merged_df_with_rm = merged_df_with_rm.rename(columns={"rmName": "rmName", "clientbranch": "branch"})
    push_trade_book_to_db(merged_df_with_rm=merged_df_with_rm)


def is_within_time_range():
    now = datetime.now().time()
    start = time(11, 0)      # 11:00 AM
    end = time(15, 5)        # 03:05 PM
    return start <= now <= end
 

if __name__ == "__main__":
    login_tms()
    while True:
        if not is_within_time_range():
            print("Time exceeded 03:05 PM. Exiting...")
            sys.exit(0)

        fetch_order_and_trade_book()
        show_message("Waiting for 60 sec", 'yellow')
        sleep(60)
