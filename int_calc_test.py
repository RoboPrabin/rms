from openpyxl.utils import get_column_letter
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Border, Side
import tkinter as tk
from tkinter import messagebox
from time import sleep
import pandas as pd
import json

from pages.InterestCalculation import get_account_code, get_ledger

# filepath = r"D:\Project-2025\buy_ageing\ledger - Copy - Copy.xlsx"
output_filename = r"C:\Users\Prabin\Desktop\BillAgeing.xlsx"
output_columns = ['Transaction Date', 'Particulars', 'Dr', 'Cr', 'Ageing' ,'Closing Balance']
data = []
sell_rows_to_skip = []
settelled_from_sold = False



def format_excel_file(excel_filepath:str):
    # Load workbook and sheet
    file_path = excel_filepath
    # file_path = r"C:\Users\Prabin\Desktop\buy_ageing\ageing_output_2.xlsx"
    wb = load_workbook(file_path)
    ws = wb.active

    # Style definitions
    yellow_fill = PatternFill(start_color='EBF1DE', end_color='EBF1DE', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Header processing: find column index of 'Ageing'
    header = [cell.value for cell in ws[1]]
    ageing_col_index = header.index('Ageing') + 1
    particulars_col_index = header.index('Particulars') + 1
    particulars_col_letter = get_column_letter(particulars_col_index)
    ws.column_dimensions[particulars_col_letter].width = 50

    # Sheet size
    max_row = ws.max_row
    max_col = ws.max_column
    col_max_len = {}
    for row in range(1, max_row + 1):
        has_ageing = False
        if row >= 2: 
            ageing_cell = ws.cell(row=row, column=ageing_col_index)
            has_ageing = ageing_cell.value is not None and str(ageing_cell.value).strip() != ""

        for col in range(1, max_col + 1):
            cell = ws.cell(row=row, column=col)
            # Apply border to every cell
            cell.border = thin_border
            # Apply yellow fill only if Ageing is present in the row
            if has_ageing:
                cell.fill = yellow_fill

            if col != particulars_col_index:
                val = str(cell.value) if cell.value is not None else ""
                col_max_len[col] = max(col_max_len.get(col, 0), len(val))
        # Set width for other columns based on max length
    for col_idx, max_len in col_max_len.items():
        col_letter = get_column_letter(col_idx)
        adjusted_width = max_len + 2  # add padding
        ws.column_dimensions[col_letter].width = adjusted_width

    wb.save(file_path)

def show_msg(title="Message", message="This is a message"):
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    messagebox.showinfo(title, message)
    root.destroy()

def delay(second):
    sleep(second)

def write_ageing_data():
    if settelled_from_sold:
        ageing = sell_transaction_date - buy_transaction_date
        buy_ageing = ageing
        sell_ageing = ""
    else:
        buy_ageing = 0
        sell_ageing = ""

    buy_extracted = [buy_row.get('Transaction Date', ''),buy_row.get('Particulars', ''),buy_row.get('Dr', ''),buy_row.get('Cr', ''), buy_ageing, closing_amount]
    data.append(buy_extracted)

    if settelled_from_sold:
        sell_extracted = [sell_row.get('Transaction Date', ''),sell_row.get('Particulars', ''),sell_row.get('Dr', ''),sell_row.get('Cr', ''),sell_ageing ,closing_amount]
        data.append(sell_extracted)

    data.append(['' for _ in output_columns])

def refine_ageing(filepath:str): 
    df = pd.read_excel(filepath)
    # Ensure 'Transaction Date' is datetime formatted
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date']).dt.date

    for index, row in df.iterrows():
        if pd.isna(row['Ageing']):
            continue

        if int(row['Ageing']) == 0:
            current_txn_date = row['Transaction Date']
            
            if index >= 2:
                prev_txn_date = df.at[index - 2, 'Transaction Date']
            else:
                prev_txn_date = pd.NaT

            # Calculate date difference
            if not pd.isna(prev_txn_date):
                buy_age = (current_txn_date - prev_txn_date).days
            else:
                buy_age = None

            print(f"\n✅ Found Ageing 0 at Excel Row: {index + 2}")
            print(f"📅 Current Transaction Date: {current_txn_date.strftime('%Y-%m-%d')}")
            print(f"📅 Previous Transaction Date (-2 rows): {prev_txn_date.strftime('%Y-%m-%d') if not pd.isna(prev_txn_date) else 'N/A'}")
            print(f"📊 Buy Age (in days): {buy_age}")

            if buy_age is not None and buy_age < 0:
                df.at[index, "Ageing"] = buy_age
            else:
                for i in range(index - 3, -1, -1): 
                    past_date = df.at[i, 'Transaction Date']
                    if pd.isna(past_date):
                        continue
                    delta = (current_txn_date - past_date).days
                    if delta < 0:
                        df.at[index, "Ageing"] = delta
                        print(f"🔁 Backtracked to index {i} → Date: {past_date.strftime('%Y-%m-%d')}")
                        print(f"📉 Updated Ageing at index {index} = {delta}")
                        break
                else:
                    # If no negative found
                    print(f"⚠️ Could not find a past date before current date for index {index}")



    df['Transaction Date'] = pd.to_datetime(df['Transaction Date']).dt.strftime('%Y-%m-%d')
    df["Ageing"] = df["Ageing"].abs()

    df.to_excel(filepath, index=False)

def main():
    global sell_transaction_date, buy_transaction_date, buy_row, sell_row, closing_amount, settelled_from_sold
    output_filepath = r"C:\Users\Prabin\Desktop\Ledger_.xlsx"
    df = pd.read_excel(output_filepath)
    closing_amount = 0.0
    for buy_index, buy_row in df.iterrows():
        temp_closing_amount = 0.0
        need_settlement_from_sell = False
        buy_particulars = str(buy_row['Particulars']).lower()
        buy_amount = float(buy_row['Dr'])
        buy_transaction_date = pd.to_datetime(str(buy_row['Transaction Date']))
      
        if 'being share purchased' in buy_particulars:
            # print(f"Purchased found and picked index is: {buy_index+2}")  

            if closing_amount <= 0:
                temp_closing_amount = closing_amount
                closing_amount = buy_amount + temp_closing_amount
                # print(f"Buy bill of index { buy_index+2} has been settled at index {buy_index+2} with new closing amount {closing_amount}")
                # print("\n\n")
                if closing_amount <= 0:
                    settelled_from_sold = False
                    write_ageing_data()
                    continue
                else:
                    need_settlement_from_sell = True

            # show_msg(message=f"Purchased picked from index {buy_index+2}, with amount of  {buy_amount}")

            for sell_index, sell_row in df.iloc[buy_index+1:].iterrows():
                sell_particulars = str(sell_row['Particulars']).lower()
                sell_amount = float(sell_row['Cr'])
                sell_transaction_date = pd.to_datetime(str(sell_row['Transaction Date']))
                if sell_index in sell_rows_to_skip:
                    # print(f"Skipped sell index {sell_index+2}")
                    continue


                if 'being share sold' in sell_particulars or 'received in bank' in sell_particulars:
                    # show_msg(message=f"Sold found at index {sell_index+2} with cr: {sell_amount}")
                    if need_settlement_from_sell:
                        closing_amount = closing_amount - sell_amount
                        sell_rows_to_skip.append(sell_index)
                    else:
                        closing_amount = buy_amount - sell_amount
                        sell_rows_to_skip.append(sell_index)

                    # show_msg(message=f"Now closing amount is {closing_amount}")
                    if closing_amount<=0:
                        settelled_from_sold = True
                        write_ageing_data()
                        break
    

    
    output_df = pd.DataFrame(data, columns=output_columns)
    output_df.drop(columns=['Closing Balance'], inplace=True)
    output_df.to_excel(output_filename, index=False)
    
    
    
    # refine_ageing(filepath=output_filename)
    format_excel_file(excel_filepath=output_filepath)
    return output_df


# def fetch_ledger(client_code = 'dku24', from_date = '2000-07-31', to_date = '2026-01-18'):
#     client_code = client_code.upper()
#     # token = get_token()
#     token = "eyJhbGciOiJIUzUxMiJ9.eyJqdGkiOiIxODFkMDRlNi02YjI0LTRkOGUtYjdjNC1lOTFjYjkzODQwNjQiLCJ1c2VySWQiOiJVc3ItY29kZSIsImlhdCI6MTc2OTAzMDE2OCwiZXhwIjoxNzY5MTA1Njk5fQ.eq7LOMgk-6LhVLtOe9RubZsp5s46Kf3TBgNupr3ypu3BAKGHAspy1Yqc3JAmfJ7ZuApCtCcPNqN4eUo2K2z5FQ"
#     acc_code = get_account_code(token=token, nepse_code=client_code)
#     ledger_data = get_ledger(token=token, ac_code=acc_code, date_from=from_date, date_to=to_date)['data']
#     # print(json.dumps(ledger_data, indent=4))
#     df = pd.DataFrame(ledger_data)
#     ordered_cols = [
#         "transactionDate", "clearanceDate", "referenceNo",
#         "voucherNo", "particulars", "dr", "cr", "balance", "balanceType"
#     ]
#     # number_cols = ["Dr", "Cr", "Balance"]
#     df = df[[c for c in ordered_cols if c in df.columns]]
#     print(df.head())
#     return df


if __name__ == "__main__":

    main()
    # output_df.to_excel(r"C:\Users\Prabin\Desktop\BillAgeing.xlsx", index=False)

    # df = fetch_ledger(client_code='20250430483')
    # df.to_excel(output_filepath)