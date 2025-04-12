# This new version should only be triggered once a month, at 00:00 the day of the next month
# It will still generate the same excel, but now the leases will be ordered by when they actually began
# Also it will have a front page with statistics, most used car, most leases done, most damage by user etc.
# This will be called by a cron job, so no while loop hogging the thread
#* The cron job can be set in a docker linux container


# The files will now be called just by their year and month: 2025.04 ICLS Report.xlsx
# No checks will be made if another file exists as the cron job will take care of that

# ? Maybe implement a force rebuild function, so the admin can generate a report whenver, if the cron job fucks itself


import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl import Workbook
from datetime import datetime
import os
import psycopg2
import pytz


db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_user = os.getenv('POSTGRES_USER')
db_pass = os.getenv('POSTGRES_PASS')
db_name = os.getenv('POSTGRES_DB')

class ExcelWriter:
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

    def connect_to_db(self):
        try:
            db_con = psycopg2.connect(dbname=db_name, user=db_user, host=db_host, port=db_port, password=db_pass)
            cur = db_con.cursor()
            return db_con, cur
        except psycopg2.Error as e:
            return None, str(e)
    
    def get_month_lengths(self, month,leap_year=False) -> int:
        lengths = {
            1: 31,
            2: 29 if leap_year else 28,
            3: 31,
            4: 30,
            5: 31,
            6: 30,
            7: 31,
            8: 31,
            9: 30,
            10: 31,
            11: 30,
            12: 31
        }
        return lengths[month]

    def isLeapYear(self, year:int) ->bool:
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return True
        else:
            return False

    def convert_to_datetime(self, string) -> datetime:
        try:
            # Parse string, handling timezone if present
            dt_obj = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
            return dt_obj
        except Exception as e: 
            raise ValueError(f"Invalid datetime format: {string}") from e

    def get_sk_date(self) -> datetime:
        bratislava_tz = pytz.timezone('Europe/Bratislava')

        dt_obj = datetime.now()
        utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
        bratislava_time = utc_time.astimezone(bratislava_tz)  # Convert to Bratislava timezone
        return bratislava_time
    
    # Get lease data from the DB, take only from the last month
    # Order it by their starting day, if a value does not exist, replace with NULL
    def get_lease_data(self) -> list:
        conn, curr = self.connect_to_db()

        query = """
            SELECT 
                l.start_of_lease, l.end_of_lease, l.time_of_return, l.note, l.damaged, l.private, l.car_health_check, l.dirty, l.exterior_damage, l.interior_damage, l.collision
                c.name, c.stk, c.drive_type, c.gas,
                d.email, 
                  
            FROM lease AS l
            JOIN car AS c 
                ON l.id_car = c.id_car
            JOIN driver AS d 
                ON l.id_driver = d.id_driver;
            """
        curr.execute(query=query)
        res = curr.fetchall()

        # Order the results by soonest starting day
        ordered_res = []
        for i in res:
            print(i)
            print(i)
            dt_starting_date = self.convert_to_datetime(i[0])



    # Create the excel file
    def createExcel(self) -> object:
        wb = Workbook()

        current_time = self.get_sk_date()


        current_month = self.get_month_lengths( 
                int(current_time.month), 
                self.isLeapYear(current_time.year) 
            )

        for day in range(1, current_month):

            ws = wb.create_sheet(str(day))
            filler = ["","","","","","","",""]
            data = [filler,filler,["", "", "Čas od", "Čas do", "Auto", "SPZ", "Typ","Email", "Odovzdanie", "Meškanie", "Poznámka", "Poškodenie","Zašpinené", "Pš.Interiér", "Pš.Exterier", "Kolizia"]]

            for row in data:
                ws.append(row)

            # Format red flag cell (B3)
            red_flag_cell = ws["B3"]
            red_flag_cell.font   = self.red_flag_ft
            red_flag_cell.fill   = self.red_flag_fill
            red_flag_cell.border = self.Header_border
            email_cell           = ws["B3"]


            # Set row height for header row
            ws.row_dimensions[3].height = 35

            # Set column widths for data columns
            for col in ["C", "D", "E", "F", "G", "H", "I", "J","K", "L", "M", "N", "O", "P"]:
                ws.column_dimensions[col].width = 23

            # Format header row (C3:J3)
            for row_cells in ws["C3:P3"]:
                for cell in row_cells:
                    cell.font      = self.Header_ft
                    cell.alignment = self.header_alignment
                    cell.fill      = self.Header_fill
                    cell.border    = self.Header_border
        wb_name = f"{current_time.year}.{current_time.month} ICLS Report.xlsx"
        wb.save(f"{os.getcwd()}/reports{wb_name}")


obj = ExcelWriter()

obj.createExcel()
obj.get_lease_data()