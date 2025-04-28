from flask import Flask, render_template, request, send_file
import requests
from bs4 import BeautifulSoup
import csv
import re
import io

app = Flask(__name__)

# Constants
login_url = 'https://sgi.accsofterp.com/AccSoft_SGI/StudentLogin.aspx'
attendance_url = 'https://sgi.accsofterp.com/AccSoft_SGI/Parents/StuAttendanceStatus.aspx'

# Format roll number function
def format_roll_number(i):
    if i < 100:
        return f'0133CY2210{i:02d}'
    return f'0133CY221{i:02d}'

# Scrape logic for one student
def scrape_student(i):
    roll = format_roll_number(i)
    print(f"\n🔍 Checking for: {roll}")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'
    })

    try:
        # Load login page
        response = session.get(login_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        viewstate = soup.find('input', {'id': '__VIEWSTATE'})['value']
        eventvalidation = soup.find('input', {'id': '__EVENTVALIDATION'})['value']
        viewstategen = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']

        # Login payload
        login_payload = {
            '__VIEWSTATE': viewstate,
            '__EVENTVALIDATION': eventvalidation,
            '__VIEWSTATEGENERATOR': viewstategen,
            'ctl00$cph1$txtStuUser': roll,
            'ctl00$cph1$txtStuPsw': roll,
            'ctl00$cph1$btnStuLogin': 'Login'
        }

        # Login request
        login_response = session.post(login_url, data=login_payload)

        # Check login success
        if "Attendance Status" not in login_response.text:
            print("❌ Login failed.")
            return [roll, 'Login Failed']

        # Visit attendance page
        attendance_response = session.get(attendance_url)
        attendance_soup = BeautifulSoup(attendance_response.text, 'html.parser')

        # Extract data
        name_input = attendance_soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtStudentName'})
        attendance_span = attendance_soup.find('span', {'id': 'ctl00_ContentPlaceHolder1_lblPer119'})

        student_name = name_input['value'] if name_input else "Unknown"
        attendance_text = attendance_span.get_text(strip=True) if attendance_span else "N/A"

        match = re.search(r'(\d+(\.\d+)?)', attendance_text)
        attendance = match.group(1) if match else "N/A"

        print(f"👤 Name: {student_name}")
        print(f"📊 Attendance: {attendance}")

        return [roll, student_name, attendance]

    except Exception as e:
        print(f"❌ Error scraping {roll}: {e}")
        return [roll, 'Error Occurred']

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
            return "⚠️ Start roll number must be less than end roll number.", 400

        # Use StringIO for in-memory CSV file
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)

        # CSV header
        writer.writerow(['Roll Number', 'Student Name', 'Attendance'])

        # Loop through students in batches of 10
        batch_size = 10
        for i in range(start_roll, end_roll + 1, batch_size):
            batch_end = min(i + batch_size - 1, end_roll)
            print(f"Scraping batch: {i} to {batch_end}")
            for j in range(i, batch_end + 1):
                student_data = scrape_student(j)
                writer.writerow(student_data)

        # Reset buffer pointer to beginning
        csv_file.seek(0)

        return send_file(
            io.BytesIO(csv_file.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='attendance_report.csv'
        )

    except Exception as e:
        print(f"Error: {e}")
        return f"❌ An error occurred: {str(e)}", 500


if __name__ == '__main__':
    app.run(debug=True)
