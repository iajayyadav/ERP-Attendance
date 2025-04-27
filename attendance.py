import requests
from bs4 import BeautifulSoup
import csv
import re

# Constants
login_url = 'https://sgi.accsofterp.com/AccSoft_SGI/StudentLogin.aspx'
attendance_url = 'https://sgi.accsofterp.com/AccSoft_SGI/Parents/StuAttendanceStatus.aspx'

# Function to format roll number
def format_roll_number(i):
    if i < 100:
        return f'0133CY2210{i:02d}'
    return f'0133CY221{i:02d}'

# ⭐ MAIN FUNCTION to scrape attendance
def scrape_attendance(start_roll=1, end_roll=73, csv_filename='attendance_report.csv'):
    with open(csv_filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Roll Number', 'Student Name', 'Attendance'])

        for i in range(start_roll, end_roll + 1):
            roll = format_roll_number(i)
            print(f"\n🔍 Checking for: {roll}")

            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'
            })

            try:
                # Step 1: Get login page
                response = session.get(login_url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')

                viewstate = soup.find('input', {'id': '__VIEWSTATE'})['value']
                eventvalidation = soup.find('input', {'id': '__EVENTVALIDATION'})['value']
                viewstategen = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']
            except Exception as e:
                print(f"❌ Error loading login page: {e}")
                writer.writerow([roll, 'Login Page Error', ''])
                continue

            # Step 2: Login
            login_payload = {
                '__VIEWSTATE': viewstate,
                '__EVENTVALIDATION': eventvalidation,
                '__VIEWSTATEGENERATOR': viewstategen,
                'ctl00$cph1$txtStuUser': roll,
                'ctl00$cph1$txtStuPsw': roll,
                'ctl00$cph1$btnStuLogin': 'Login'
            }

            login_response = session.post(login_url, data=login_payload)

            # Step 3: Check login success
            if "Attendance Status" not in login_response.text:
                print("❌ Login failed.")
                writer.writerow([roll, 'Login Failed', ''])
                continue

            # Step 4: Visit attendance page
            attendance_response = session.get(attendance_url)
            attendance_soup = BeautifulSoup(attendance_response.text, 'html.parser')

            # Step 5: Extract data
            name_input = attendance_soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtStudentName'})
            attendance_span = attendance_soup.find('span', {'id': 'ctl00_ContentPlaceHolder1_lblPer119'})

            student_name = name_input['value'] if name_input else "Unknown"
            attendance_text = attendance_span.get_text(strip=True) if attendance_span else "N/A"
            match = re.search(r'(\d+(\.\d+)?)', attendance_text)
            attendance = match.group(1) if match else "N/A"

            print(f"👤 Name: {student_name}")
            print(f"📊 Attendance: {attendance}")

            # Write to CSV
            writer.writerow([roll, student_name, attendance])

    print(f"\n✅ Attendance report saved to {csv_filename}")
