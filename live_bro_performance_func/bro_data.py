from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
import pandas as pd
import openpyxl
import os
from utils.helper import show_message
import xlwings as xw


def update_summary_report_with_comma_and_number_format(file_path):
    # Load workbook
    wb = openpyxl.load_workbook(file_path)

    # Function to apply number formatting and right alignment
    def format_cells(sheet):
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, (int, float)):  # Check if it's a number
                    cell.number_format = '#,##0.00;[Red](#,##0.00)'  # Format numbers properly
                    cell.alignment = Alignment(horizontal="right")  # Align right

    # Loop through all sheets and apply formatting
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        format_cells(ws)
    # Save the changes back to the same file
    wb.save(file_path)


def autofit_columns(filepath: str):
    # show_message("Formatting the Sheets.....", 'white')
    wb = openpyxl.load_workbook(filepath)
    thin_border = Border(left=Side(style='thin'),
                         right=Side(style='thin'),
                         top=Side(style='thin'),
                         bottom=Side(style='thin'))

    # Loop through each sheet in the workbook
    for ws in wb.worksheets:
        if ws.title !="Sheet1":
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter  # Get the column letter
                
                for cell in col:
                    try:  
                        if cell.value is not None:
                            max_length = max(max_length, len(str(cell.value)))
                            # Align cell content to the left
                            cell.alignment = Alignment(horizontal='left')
                            # Add border to the cell
                            cell.border = thin_border
                    except:
                        pass
                
                # Set adjusted column width
                adjusted_width = max_length + 6
                ws.column_dimensions[column].width = adjusted_width + 6
    wb.save(filepath)


def separate_data_by_bro_in_folder(filepath: str):
    show_message("Extracting BRO data. Please wait . . . .", "yellow")
    from openpyxl import load_workbook
    # Get the directory path where the original file is located
    dir_path = os.path.dirname(filepath)
    get_date = dir_path.split("\\")[-1]
    
    # Load the Excel file
    df = pd.read_excel(filepath)

    df["rmName"] = df["rmName"].fillna("N/A")
    # Open workbook using openpyxl to rename the first sheet
    wb = load_workbook(filepath)
    
    # Rename the first sheet to "All Branches Data"
    main_sheet = wb.sheetnames[0]  # Get the first sheet name
    ws = wb[main_sheet]
    # ws.title = "All Branch Data"

    # Save changes to the original file with renamed sheet
    wb.save(filepath)
    # Create a new file for each unique branch
    for bro in df["rmName"].unique():

        # if "N/A" in bro:
        #     continue
        # bro = str(bro).replace("/", "")

        # Filter data for that branch
        branch_data = df[df["rmName"] == bro]  

        if not len(branch_data)>0:
            continue
        
        
        if bro.upper() == "N/A":
            print("\n\n")
            show_message(f"N/A data has found with length of {len(branch_data)}.", "yellow")


        # # Convert branch name into a valid Excel sheet name (max 31 chars, no special chars)
        # sheet_name = str(bro)[:31]
        # print(sheet_name, bro)
        # from time import sleep
        # sleep(1000)
        new_dir_path = os.path.join(dir_path, "BRO")
        
        if not os.path.exists(new_dir_path):
            os.mkdir(new_dir_path)
        if bro == "N/A":
            bro = bro.replace("N/A", "NAN")
            show_message(f"Message NAN found as {bro}", "red")
            # from time import sleep
            # sleep(1000)
        branch_filename = os.path.join(new_dir_path, f"BRO_{bro}_Traders Due Report.xlsx")
        # branch_filename = os.path.join(new_dir_path, f"BRO_{sheet_name}_{get_date}_Cost_Benefit.xlsx")

        with pd.ExcelWriter(branch_filename, engine="openpyxl") as writer:
            branch_data.to_excel(writer, index=False)
        show_message(f"Bro data saved as {branch_filename}")
        # color_rows_based_on_client_zone(filepath=branch_filename)
        update_summary_report_with_comma_and_number_format(file_path=branch_filename)
        # autofit_columns(branch_filename)
        # Open workbook
        app = xw.App(visible=False)
        wb = app.books.open(branch_filename)

        # Autofit all sheets
        for sheet in wb.sheets:
            sheet.autofit()

        # Save and close
        wb.save()
        wb.close()
    work_dir = os.path.dirname(filepath)
    output_dir_path = work_dir +"\\" + "BRO"
    show_message("Extracting bro data completed.", "green")
    return output_dir_path