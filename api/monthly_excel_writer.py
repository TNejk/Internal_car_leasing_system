import os
import psycopg2
import pytz
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl import Workbook

class MonthlyExcelWriter:
    """
    Monthly batch Excel writer for car lease reports.
    Designed to run once per month automatically in Docker container.
    """
    
    def __init__(self):
        # Database configuration from environment variables
        self.db_host = os.getenv('DB_HOST')
        self.db_port = os.getenv('DB_PORT')
        self.db_user = os.getenv('POSTGRES_USER')
        self.db_pass = os.getenv('POSTGRES_PASS')
        self.db_name = os.getenv('POSTGRES_DB')
        
        # Slovakia timezone configuration
        self.bratislava_tz = pytz.timezone('Europe/Bratislava')
        
        # Excel styling to match original format
        self._init_styles()
        
    def _init_styles(self):
        """Initialize Excel styling constants to match original format."""
        self.red_flag_ft = Font(bold=True, color="B22222")
        self.red_flag_fill = PatternFill("solid", "B22222")
        self.header_fill = PatternFill("solid", "00CCFFFF")
        self.header_ft = Font(bold=True, color="000000", size=20)
        self.data_ft = Font(size=17)
        
        self.header_border = Border(
            left=Side(border_style="medium", color='FF000000'),
            right=Side(border_style="medium", color='FF000000'),
            top=Side(border_style="medium", color='FF000000'),
            bottom=Side(border_style="medium", color='FF000000')
        )
        
        self.header_alignment = Alignment(
            horizontal='center',
            vertical='center'
        )
    
    def connect_to_db(self) -> tuple:
        """Establish database connection."""
        try:
            db_con = psycopg2.connect(
                dbname=self.db_name, 
                user=self.db_user, 
                host=self.db_host, 
                port=self.db_port, 
                password=self.db_pass
            )
            cur = db_con.cursor()
            return db_con, cur
        except psycopg2.Error as e:
            print(f"ERROR: Database connection failed: {e}")
            return None, None
    
    def get_sk_date(self) -> datetime:
        """Get current time in Slovakia (Bratislava) timezone."""
        dt_obj = datetime.now()
        utc_time = dt_obj.replace(tzinfo=pytz.utc) if dt_obj.tzinfo is None else dt_obj.astimezone(pytz.utc)
        bratislava_time = utc_time.astimezone(self.bratislava_tz)
        return bratislava_time
    
    def convert_to_bratislava_timezone(self, dt_obj) -> str:
        """Convert datetime object to Slovakia timezone string in original format."""
        if dt_obj is None:
            return "NULL"
        
        # Handle timezone-aware datetime
        if dt_obj.tzinfo is None:
            utc_time = pytz.utc.localize(dt_obj)
        else:
            utc_time = dt_obj.astimezone(pytz.utc)
        
        bratislava_time = utc_time.astimezone(self.bratislava_tz)
        # Match original format: "25-02-2025 21:04"
        return bratislava_time.strftime("%d-%m-%Y %H:%M")
    
    def get_month_date_range(self, year: int, month: int) -> tuple:
        """Get start and end datetime for a specific month in Slovakia timezone."""
        # Start of month in Slovakia timezone
        start_date = datetime(year, month, 1, 0, 0, 0)
        
        # Start of next month
        if month == 12:
            end_date = datetime(year + 1, 1, 1, 0, 0, 0)
        else:
            end_date = datetime(year, month + 1, 1, 0, 0, 0)
        
        # Convert to timezone-aware datetimes in Bratislava timezone
        start_date = self.bratislava_tz.localize(start_date)
        end_date = self.bratislava_tz.localize(end_date)
        
        return start_date, end_date
    
    def get_lease_data_for_month(self, year: int, month: int) -> List[Dict[str, Any]]:
        """
        Get all lease data for a specific month.
        Includes leases that started in that month, regardless of when they ended.
        """
        conn, cur = self.connect_to_db()
        if not conn:
            raise RuntimeError("Could not establish database connection")
        
        try:
            start_date, end_date = self.get_month_date_range(year, month)
            
            query = """
                SELECT 
                    l.id_lease,
                    l.start_of_lease, 
                    l.end_of_lease, 
                    l.time_of_return, 
                    l.note, 
                    l.status,
                    l.private, 
                    l.car_health_check, 
                    l.dirty, 
                    l.exterior_damage, 
                    l.interior_damage, 
                    l.collision,
                    c.name AS car_name, 
                    c.stk, 
                    c.drive_type, 
                    c.gas,
                    d.email,
                    d.name AS driver_name       
                FROM lease AS l
                JOIN car AS c ON l.id_car = c.id_car
                JOIN driver AS d ON l.id_driver = d.id_driver
                WHERE l.start_of_lease >= %s AND l.start_of_lease < %s
                ORDER BY l.start_of_lease ASC;
            """
            
            cur.execute(query, (start_date, end_date))
            raw_data = cur.fetchall()
            
            # Convert to list of dictionaries for easier handling
            lease_data = []
            for row in raw_data:
                lease_record = {
                    'id_lease': row[0],
                    'start_of_lease': row[1],
                    'end_of_lease': row[2],
                    'time_of_return': row[3],
                    'note': row[4] or '',
                    'status': row[5],  # True = active/completed, False = cancelled
                    'private': row[6],
                    'car_health_check': row[7],
                    'dirty': row[8],
                    'exterior_damage': row[9],
                    'interior_damage': row[10],
                    'collision': row[11],
                    'car_name': row[12],
                    'stk': row[13],
                    'drive_type': row[14] or '',
                    'gas': row[15] or '',
                    'email': row[16],
                    'driver_name': row[17],
                    # Add calculated fields
                    'is_cancelled': not row[5],  # status = False means cancelled
                    'is_multi_month': self._is_multi_month_lease(row[1], row[2]),
                    'late_return': self._calculate_late_return(row[2], row[3]) if row[3] else False
                }
                lease_data.append(lease_record)
            
            return lease_data
            
        except Exception as e:
            print(f"ERROR: Failed to get lease data: {e}")
            raise
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
    
    def _is_multi_month_lease(self, start_date, end_date) -> bool:
        """Check if a lease spans multiple months."""
        if not start_date or not end_date:
            return False
        return start_date.month != end_date.month or start_date.year != end_date.year
    
    def _calculate_late_return(self, end_date, return_date) -> bool:
        """Calculate if a lease was returned late."""
        if not return_date or not end_date:
            return False
        return return_date > end_date 
    
    def create_excel_report(self, year: int, month: int, force_rebuild: bool = False) -> str:
        """
        Create monthly Excel report matching original format exactly.
        """
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(os.getcwd(), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate filename: "2025.04 ICLS Report.xlsx"
        filename = f"{year}.{month:02d} ICLS Report.xlsx"
        filepath = os.path.join(reports_dir, filename)
        
        # Check if file already exists and force_rebuild is False
        if os.path.exists(filepath) and not force_rebuild:
            print(f"INFO: Report already exists: {filename}")
            return filename
        
        try:
            # Get lease data for the month
            lease_data = self.get_lease_data_for_month(year, month)
            print(f"INFO: Found {len(lease_data)} leases for {year}-{month:02d}")
            
            # Create workbook
            wb = Workbook()
            
            # Remove default sheet
            if "Sheet" in wb.sheetnames:
                wb.remove(wb["Sheet"])
            
            # Create summary sheet first
            self._create_summary_sheet(wb, lease_data, year, month)
            
            # Create leases data sheet (matching original format)
            self._create_leases_sheet(wb, lease_data, year, month)
            
            # Save workbook
            wb.save(filepath)
            print(f"INFO: Report created successfully: {filename}")
            
            return filename
            
        except Exception as e:
            print(f"ERROR: Failed to create Excel report: {e}")
            raise
    
    def _create_summary_sheet(self, wb: Workbook, lease_data: List[Dict], year: int, month: int):
        """Create summary statistics sheet."""
        ws = wb.create_sheet("Prehľad", 0)
        
        # Title
        ws["B2"] = f"Mesačný prehľad - {year}.{month:02d}"
        ws["B2"].font = Font(bold=True, size=24)
        ws["B2"].alignment = self.header_alignment
        
        # Statistics
        total_leases = len(lease_data)
        completed_leases = len([l for l in lease_data if not l['is_cancelled'] and l['time_of_return']])
        cancelled_leases = len([l for l in lease_data if l['is_cancelled']])
        active_leases = len([l for l in lease_data if not l['is_cancelled'] and not l['time_of_return']])
        private_leases = len([l for l in lease_data if l['private']])
        multi_month_leases = len([l for l in lease_data if l['is_multi_month']])
        late_returns = len([l for l in lease_data if l['late_return']])
        
        # Damage statistics
        damaged_cars = len([l for l in lease_data if l['car_health_check']])
        dirty_cars = len([l for l in lease_data if l['dirty']])
        collisions = len([l for l in lease_data if l['collision']])
        
        stats = [
            ("Celkový počet rezervácií:", total_leases),
            ("Dokončené rezervácie:", completed_leases),
            ("Zrušené rezervácie:", cancelled_leases),
            ("Aktívne rezervácie:", active_leases),
            ("Súkromné rezervácie:", private_leases),
            ("Viacmesačné rezervácie:", multi_month_leases),
            ("Neskoré vrátenia:", late_returns),
            ("", ""),
            ("Poškodené autá:", damaged_cars),
            ("Znečistené autá:", dirty_cars),
            ("Kolízie:", collisions),
        ]
        
        row = 4
        for label, value in stats:
            if label:  # Skip empty rows
                ws[f"B{row}"] = label
                ws[f"B{row}"].font = Font(bold=True)
                ws[f"C{row}"] = value
            row += 1
        
        # Set column widths
        ws.column_dimensions['B'].width = 30
        ws.column_dimensions['C'].width = 15
    
    def _create_leases_sheet(self, wb: Workbook, lease_data: List[Dict], year: int, month: int):
        """Create main leases data sheet matching original format exactly."""
        ws = wb.create_sheet("Rezervácie")
        
        # Headers matching original format exactly
        headers = [
            "", "", "Čas od", "Čas do", "Auto", "SPZ", "Typ", "Email", 
            "Odovzdanie", "Meškanie", "Poznámka", "Poškodenie", "Zašpinené", 
            "Pš.Interiér", "Pš.Exterier", "Kolízia"
        ]
        
        # Add two empty filler rows like original
        filler = [""] * len(headers)
        ws.append(filler)
        ws.append(filler)
        
        # Write headers in row 3
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            if col >= 3:  # Skip first two empty columns
                cell.font = self.header_ft
                cell.alignment = self.header_alignment
                cell.fill = self.header_fill
                cell.border = self.header_border
        
        # Red flag cell in B3
        red_flag_cell = ws.cell(row=3, column=2)
        red_flag_cell.font = self.red_flag_ft
        red_flag_cell.fill = self.red_flag_fill
        red_flag_cell.border = self.header_border
        
        # Set row height and column widths matching original
        ws.row_dimensions[3].height = 35
        for col in range(3, len(headers) + 1):
            col_letter = openpyxl.utils.get_column_letter(col)
            ws.column_dimensions[col_letter].width = 23
        
        # Write data starting from row 4
        row = 4
        for lease in lease_data:
            # Convert dates to Slovakia timezone display format
            start_time = self.convert_to_bratislava_timezone(lease['start_of_lease'])
            end_time = self.convert_to_bratislava_timezone(lease['end_of_lease'])
            
            # Handle return time
            if lease['is_cancelled']:
                return_time = "ZRUŠENÉ"
            elif lease['time_of_return']:
                return_time = self.convert_to_bratislava_timezone(lease['time_of_return'])
            else:
                return_time = "NULL"
            
            # Prepare drive type info matching original format
            drive_info = f"{lease['gas']}, {lease['drive_type']}" if lease['gas'] and lease['drive_type'] else (lease['gas'] or lease['drive_type'] or "")
            
            # Create row data matching original format exactly
            row_data = [
                "", "",  # Empty columns like original
                start_time,
                end_time,
                lease['car_name'],
                lease['stk'],
                drive_info,
                lease['email'],
                return_time,
                "ÁNO" if lease['late_return'] else "NIE",
                lease['note'],
                "ÁNO" if lease['car_health_check'] else "NIE",
                "ÁNO" if lease['dirty'] else "NIE",
                "ÁNO" if lease['interior_damage'] else "NIE",
                "ÁNO" if lease['exterior_damage'] else "NIE",
                "ÁNO" if lease['collision'] else "NIE"
            ]
            
            # Write row
            for col, value in enumerate(row_data, 1):
                ws.cell(row=row, column=col, value=value)
            
            # Highlight cancelled leases with light red background
            if lease['is_cancelled']:
                for col in range(3, len(headers) + 1):
                    cell = ws.cell(row=row, column=col)
                    cell.fill = PatternFill("solid", "FFE6E6")
            
            row += 1

    def generate_previous_month_report(self, force_rebuild: bool = False) -> str:
        """
        Generate report for the previous month.
        This is the method that would typically be called by cron jobs.
        """
        current_date = self.get_sk_date()
        
        # Calculate previous month
        if current_date.month == 1:
            prev_month = 12
            prev_year = current_date.year - 1
        else:
            prev_month = current_date.month - 1
            prev_year = current_date.year
        
        print(f"INFO: Generating report for {prev_year}-{prev_month:02d}")
        return self.create_excel_report(prev_year, prev_month, force_rebuild)
    
    def generate_current_month_report(self, force_rebuild: bool = False) -> str:
        """
        Generate report for the current month.
        Useful for testing or mid-month reports.
        """
        current_date = self.get_sk_date()
        print(f"INFO: Generating current month report for {current_date.year}-{current_date.month:02d}")
        return self.create_excel_report(current_date.year, current_date.month, force_rebuild)
    
    def run_monthly_task(self):
        """
        Run the complete monthly task: generate report and clean old ones.
        This is the main method for automatic Docker execution.
        """
        try:
            print(f"INFO: Starting monthly Excel report generation at {self.get_sk_date()}")
            
            # Generate previous month report
            filename = self.generate_previous_month_report()
            print(f"SUCCESS: Generated report: {filename}")
                        
            print("INFO: Monthly task completed successfully")
            
        except Exception as e:
            print(f"ERROR: Monthly task failed: {e}")
            raise


def main():
    """
    Main function for automatic monthly report generation.
    Runs without arguments for Docker container automation.
    """
    writer = MonthlyExcelWriter()
    
    try:
        # Run the complete monthly task automatically
        writer.run_monthly_task()
            
    except Exception as e:
        print(f"ERROR: Failed to generate monthly report: {e}")
        exit(1)


if __name__ == "__main__":
    main()