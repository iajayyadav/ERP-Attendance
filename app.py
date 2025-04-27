from flask import Flask, render_template, request, send_from_directory
import requests
from bs4 import BeautifulSoup
import csv
import re
import os

app = Flask(__name__)

# Constants
login_url = 'https://sgi.accsofterp.com/AccSoft_SGI/StudentLogin.aspx'
attendance_url = 'https://sgi.accsofterp.com/AccSoft_SGI/Parents/StuAttendanceStatus.aspx'

# Function to format roll number
def format_roll_number(i):
    if i < 100:
        return f'0133CY2210{i:02d}'
    return f'0133CY221{i:02d}'

# Scraper function
def scrape_attendance(start_roll, end_roll):
    os.makedirs('results', exist_ok=True)
    csv_filename = 'attendance_report.csv'
    csv_path = os.path.join('results', csv_filename)

    with open(csv_path, 'w', newline='', encoding='utf-8') as file:
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
                response = session.get(login_url, timeout=10)
                soup = BeautifulSoup(response.text, 'html.parser')

                viewstate = soup.find('input', {'id': '__VIEWSTATE'})['value']
                eventvalidation = soup.find('input', {'id': '__EVENTVALIDATION'})['value']
                viewstategen = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']
            except Exception as e:
                print(f"❌ Error loading login page: {e}")
                writer.writerow([roll, 'Login Page Error', ''])
                continue

            login_payload = {
                '__VIEWSTATE': viewstate,
                '__EVENTVALIDATION': eventvalidation,
                '__VIEWSTATEGENERATOR': viewstategen,
                'ctl00$cph1$txtStuUser': roll,
                'ctl00$cph1$txtStuPsw': roll,
                'ctl00$cph1$btnStuLogin': 'Login'
            }

            login_response = session.post(login_url, data=login_payload)

            if "Attendance Status" not in login_response.text:
                print("❌ Login failed.")
                writer.writerow([roll, 'Login Failed', ''])
                continue

            attendance_response = session.get(attendance_url)
            attendance_soup = BeautifulSoup(attendance_response.text, 'html.parser')

            name_input = attendance_soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtStudentName'})
            attendance_span = attendance_soup.find('span', {'id': 'ctl00_ContentPlaceHolder1_lblPer119'})

            student_name = name_input['value'] if name_input else "Unknown"
            attendance_text = attendance_span.get_text(strip=True) if attendance_span else "N/A"

            match = re.search(r'(\d+(\.\d+)?)', attendance_text)
            attendance = match.group(1) if match else "N/A"

            print(f"👤 Name: {student_name}")
            print(f"📊 Attendance: {attendance}")

            writer.writerow([roll, student_name, attendance])

    return csv_filename

# Routes
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        start_roll = int(request.form['start_roll'])
        end_roll = int(request.form['end_roll'])

        if start_roll > end_roll:
            return render_template('index.html', message="⚠️ Start roll number must be less than end roll number.")

        filename = scrape_attendance(start_roll, end_roll)

        return render_template('index.html', message="✅ Scraping completed!", download_link=f"/download/{filename}")

    except Exception as e:
        print(f"Error: {e}")
        return render_template('index.html', message=f"❌ An error occurred: {str(e)}")

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory('results', filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
