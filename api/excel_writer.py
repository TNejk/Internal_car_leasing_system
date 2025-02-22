from datetime import datetime, timedelta, timezone
import os
from tkinter.font import Font

import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl import Workbook

import pytz

class writer():

    def convert_to_datetime(self, string):
        try:
            # Parse string, handling timezone if present
            dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
            return dt_obj
        except: #? Ok now bear with me, it may look stupid, be stupid and make me look stupid, but it works :) Did i mention how much i hate dates
            try:
                dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M")
                return dt_obj
            except ValueError as e:
                raise ValueError(f"Invalid datetime format: {string}") from e

    def get_sk_date(self):
        bratislava_tz = pytz.timezone('Europe/Bratislava')
        # Ensure the datetime is in UTC before converting
        dt_obj = datetime.now()
        utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
        bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
        return bratislava_time.strftime("%Y-%m-%d %H:%M:%S") 

    def get_sk_date_str(self):
        # Ensure the datetime is in UTC before converting
        bratislava_tz = pytz.timezone('Europe/Bratislava')
        dt_obj = datetime.now()
        utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
        bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
        return bratislava_time.strftime("%Y-%m-%d %H:%M:%S") 

    def compare_timeof(self, a_timeof, today):
        timeof = self.convert_to_datetime(string=a_timeof)
        diff = today - timeof
        # If the lease from date is a minute behind the current date, dont allow the lease
        # This gives the user 2 minutes to make a reservation, before being time blocked by leasing into the past
        if (diff.total_seconds()/60) >= 2:
            return True

    def get_latest_file(self, folder_path, use_modification_time=True):
        try:
            if not os.path.exists(folder_path):
                raise FileNotFoundError(f"The folder '{folder_path}' does not exist.")
            
            if not os.path.isdir(folder_path):
                raise NotADirectoryError(f"'{folder_path}' is not a directory.")

            latest_file = None
            latest_time = 0

            # Use os.scandir for better performance
            with os.scandir(folder_path) as entries:
                for entry in entries:
                    if entry.is_file():
                        # Use modification time or creation time based on the parameter
                        file_time = entry.stat().st_mtime 
                        
                        if file_time > latest_time:
                            latest_time = file_time
                            latest_file = entry.path

            return latest_file

        except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as e:
            print(f"An error occurred: {e}")
            return None


    def write_report(self, recipient, car_name, stk, drive_type, timeof, timeto):
        """
        Writes to a csv lease file about a new lease being made, if no such file exists it creates it.
        
        If a report is too old it creates a new one each month. 
        ex: '2025-01-21 15:37:00ICLS_report.csv'
        """
        # To fix the wierd seconds missing error, i will just get rid of the seconds manually
        if timeof.count(":") > 1:
            timeof = timeof[:-3]
            
        if timeto.count(":") > 1:
            timeto = timeto[:-3]

        
        latest_file = self.get_latest_file(f"{os.getcwd()}/reports")

        # Use year and month to check if a new excel spreadsheet needs to be created
        # '2025-01-21 15:37:00ICLS_report.csv'  '2025-01-21 15:37:26_ICLS_report.csv'
        try:
            # /app/reports/'2025-01-21 17:51:44exc_ICLS_report.csv' -> 2025-01-21 18:53:46
            split_date = latest_file.split("-")
            spl_year = split_date[0].removeprefix("/app/reports/")
            spl_month = split_date[1]

            # "%Y-%m-%d %H:%M:%S"
            current_date = self.get_sk_date().split("-")
            cur_year = current_date[0]
            cur_month = current_date[1]
            
            #timeof = timeof.strftime("%Y-%m-%d %H:%M:%S")
            if int(cur_year) == int(spl_year) and int(cur_month) == int(spl_month):
                wb = openpyxl.load_workbook(latest_file)
                # If a sheet name has been made before compare it with today, if its not equal create a new worksheet with the new days number
                all_sheets = wb.sheetnames
                if len(all_sheets) >0:
                    cur_day = self.convert_to_datetime(self.get_sk_date_str())
                if int(all_sheets[-1]) == cur_day.day:
                    # Select the last sheet, that should correspond to the current day
                    ws = wb[wb.sheetnames[-1]]
                else: 
                    ws = wb.create_sheet(f"{cur_day.day}")


                data = [["","",timeof, timeto, car_name, stk, drive_type, recipient, "NULL", "NULL", "NULL"]]
                for row in data:
                    ws.append(row)

                wb.save(latest_file)

            else:
                # Define styles
                red_flag_ft = Font(bold=True, color="B22222")
                red_flag_fill = PatternFill("solid", "B22222")
                Header_fill = PatternFill("solid", "00CCFFFF")
                Header_ft = Font(bold=True, color="000000", size=20)
                Data_ft = Font(size=17)  # New font for data cells

                Header_border = Border(
                    left=Side(border_style="medium", color='FF000000'),
                    right=Side(border_style="medium", color='FF000000'),
                    top=Side(border_style="medium", color='FF000000'),
                    bottom=Side(border_style="medium", color='FF000000')
                )

                header_alignment = Alignment(
                    horizontal='center',
                    vertical='center'
                )
                wb = Workbook()
                del wb["Sheet"]
                ws = wb.create_sheet(f"{self.convert_to_datetime(self.get_sk_date_str()).day}")
                #email_ft = Font(bold=True, color="B22222")
                filler = ["","","","","","","",""]
                data = [filler,filler,["", "", "Čas od", "Čas do", "Auto", "SPZ", "Typ","Email", "Odovzdanie", "Meškanie", "Poznámka"],["","",timeof, timeto, car_name, stk, drive_type, recipient, "NULL","NULL","NULL"]]

                for row in data:
                    ws.append(row)
                    # Format red flag cell (B3)
                red_flag_cell = ws["B3"]
                red_flag_cell.font = red_flag_ft
                red_flag_cell.fill = red_flag_fill
                red_flag_cell.border = Header_border
                email_cell = ws["B3"]
                #email_cell.font = email_ft

                # Set row height for header row
                ws.row_dimensions[3].height = 35

                # Set column widths for data columns
                for col in ["C", "D", "E", "F", "G", "H", "I", "J","K"]:
                    ws.column_dimensions[col].width = 23

                # Format header row (C3:J3)
                for row_cells in ws["C3:K3"]:
                    for cell in row_cells:
                        cell.font = Header_ft
                        cell.alignment = header_alignment
                        cell.fill = Header_fill
                        cell.border = Header_border

                # Format data rows (from row 4 onwards, columns C-J)
                # for row in ws.iter_rows(min_row=4, min_col=3, max_col=10):
                #     for cell in row:
                #         cell.font = Data_ft
                # Set row height for data rows (from row 4 to the last row)
                wb.save(f"{os.getcwd()}/reports/{self.get_sk_date()}_EXCEL_ICLS_report.xlsx")

        except Exception as e: #? ONLY HAPPENDS IF THE DIRECTORY IS EMPTY, SO LIKE ONCE
            with open(f"{os.getcwd()}/reports/{self.get_sk_date()}_ERRORt.txt", "a+") as file:
                file.write(f"{e}")

            # Define styles
            red_flag_ft = Font(bold=True, color="B22222")
            red_flag_fill = PatternFill("solid", "B22222")
            Header_fill = PatternFill("solid", "00CCFFFF")
            Header_ft = Font(bold=True, color="000000", size=20)
            Data_ft = Font(size=17)  # New font for data cells
            Header_border = Border(left=Side(border_style="medium", color='FF000000'),right=Side(border_style="medium", color='FF000000'),top=Side(border_style="medium", color='FF000000'),bottom=Side(border_style="medium", color='FF000000'))
            header_alignment = Alignment(horizontal='center',vertical='center')

            wb = Workbook()
            del wb["Sheet"]
            ws = wb.create_sheet(f"{self.convert_to_datetime(self.get_sk_date_str()).day}")
            filler = ["","","","","","","",""]
            data = [filler,filler,["", "", "Čas od", "Čas do", "Auto", "SPZ", "TYP","Email", "Odovzdanie", "Meškanie", "Poznámka"],["","",timeof, timeto, car_name, stk, drive_type, recipient,"NULL","NULL","NULL"]]
            for row in data:
                ws.append(row)
                # Format red flag cell (B3)
            red_flag_cell = ws["B3"]
            red_flag_cell.font = red_flag_ft
            red_flag_cell.fill = red_flag_fill
            red_flag_cell.border = Header_border
            email_cell = ws["B3"]
            # Set row height for header row
            ws.row_dimensions[3].height = 35
            # Set column widths for data columns
            for col in ["C", "D", "E", "F", "G", "H", "I", "J", "K"]:
                ws.column_dimensions[col].width = 23
            # Format header row (C3:J3)
            for row_cells in ws["C3:K3"]:
                for cell in row_cells:
                    cell.font = Header_ft
                    cell.alignment = header_alignment
                    cell.fill = Header_fill
                    cell.border = Header_border
            # Format data rows (from row 4 onwards, columns C-J)
            # for row in ws.iter_rows(min_row=4, min_col=3, max_col=10):
            #     for cell in row:
            #         cell.font = Data_ft
                    # Set row height for data rows (from row 4 to the last row)
            wb.save(f"{os.getcwd()}/reports/{self.get_sk_date()}_NW_ICLS_report.xlsx")