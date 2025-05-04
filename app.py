from flask import Flask, render_template, request, Response, send_file, stream_with_context
import time, csv, io, re, requests
from bs4 import BeautifulSoup
app = Flask(__name__)

# Constants
login_url = 'https://sgi.accsofterp.com/AccSoft_SGI/StudentLogin.aspx'
attendance_url = 'https://sgi.accsofterp.com/AccSoft_SGI/Parents/StuAttendanceStatus.aspx'

# Roll number formatting
def format_roll_number(i,b,y):
    return f'0133{b}{y}10{i:02d}' if i < 100 else f'0133{b}{y}1{i:02d}'

# Scraping logic for one student that yields logs
def scrape_student(i,b,y):
    roll = format_roll_number(i,b,y)
    yield f"data: 🔍 Checking for: {roll}\n\n"
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0'
    })

    try:
        # Load login page
        response = session.get(login_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        viewstate = soup.find('input', {'id': '__VIEWSTATE'})['value']
        eventvalidation = soup.find('input', {'id': '__EVENTVALIDATION'})['value']
        viewstategen = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})['value']

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

        if "Attendance Status" not in login_response.text:
            yield f"data:  Login failed for {roll}.\n\n"
            return [roll, 'Login Failed', "N/A"]

        attendance_response = session.get(attendance_url)
        attendance_soup = BeautifulSoup(attendance_response.text, 'html.parser')

        name_input = attendance_soup.find('input', {'id': 'ctl00_ContentPlaceHolder1_txtStudentName'})
        attendance_span = attendance_soup.find('span', {'id': 'ctl00_ContentPlaceHolder1_lblPer119'})

        student_name = name_input['value'] if name_input else "Unknown"
        attendance_text = attendance_span.get_text(strip=True) if attendance_span else "N/A"
        match = re.search(r'(\d+(\.\d+)?)', attendance_text)
        attendance = match.group(1) if match else "N/A"

        yield f"data:  {student_name} -  Attendance: {attendance}%\n\n"
        return [roll, student_name, attendance]

    except Exception as e:
        yield f"data:  Error scraping {roll}: {e}\n\n"
        return [roll, 'Error Occurred', "N/A"]

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# SSE scraping route
@app.route('/stream')
def stream():
    try:
        start_roll = int(request.args.get('start_roll'))
        end_roll = int(request.args.get('end_roll'))
        year = int(request.args.get('year'))
        branch = request.args.get("branch").upper()

        def generate():
            csv_file = io.StringIO()
            writer = csv.writer(csv_file)
            writer.writerow(['Roll Number', 'Student Name', 'Attendance'])

            for i in range(start_roll, end_roll + 1):
                logs = scrape_student(i,branch,year)
                result = None
                for log in logs:
                    if isinstance(log, str):
                        yield log
                    elif isinstance(log, list):  # actual data returned
                        result = log

                if result:
                    writer.writerow(result)

                time.sleep(0.5)

            csv_file.seek(0)
            filename = f'attendance_report_{start_roll}_{end_roll}.csv'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(csv_file.getvalue())

            yield f"data: ✅ Scraping completed! Download your report 👉 /download/{filename}\n\n"
            yield "event: done\ndata: DONE\n\n"

        # ✅ Ensure a valid streaming response is returned
        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    except Exception as e:
        return f"Error occurred: {str(e)}", 500

# Download route
@app.route('/download/<filename>')
def download(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    
    # serve(app, host="0.0.0.0", port=8080)
    app.run(debug=True, threaded=True)
