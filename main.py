from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date, datetime
from fastapi.staticfiles import StaticFiles
from datetime import date
from blob_service import read_students, write_students
from collections import defaultdict
from datetime import datetime, timedelta

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


def compute(s):
    total_sessions = s["payment_count"] * 3
    remaining = total_sessions - s["sessions_done"]
    total_received = total_sessions * s["fee"]

    # Payment status
    # Payment status (CORRECT)
    if s["payment_count"] == 0:
        payment_status = "Unpaid"
    elif remaining <= 0:
        payment_status = "Pending"
    else:
        payment_status = "Paid"

    # Session status
    if remaining > 0:
        session_status = "Active"
    elif remaining == 0:
        session_status = "Completed"
    else:
        session_status = "Overdue"

    return remaining, total_received, payment_status, session_status

def compute_dashboard(students):
    revenue = defaultdict(int)
    sessions = defaultdict(int)

    for s in students:
        fee = s["fee"]

        for d in s.get("payment_logs", []):
            revenue[month_key(d)] += fee * 3

        for d in s.get("session_logs", []):
            sessions[month_key(d)] += 1

    return revenue, sessions
def build_dashboard(students):
    revenue_by_month = defaultdict(int)
    sessions_by_month = defaultdict(int)

    # Aggregate logs
    for s in students:
        fee = s["fee"]

        for d in s.get("payment_logs", []):
            revenue_by_month[month_key(d)] += fee * 3

        for d in s.get("session_logs", []):
            sessions_by_month[month_key(d)] += 1

    # Current & previous month
    today = datetime.today()
    this_month = today.strftime("%Y-%m")

    first_day_this_month = today.replace(day=1)
    last_month_date = first_day_this_month - timedelta(days=1)
    last_month = last_month_date.strftime("%Y-%m")

    this_revenue = revenue_by_month.get(this_month, 0)
    last_revenue = revenue_by_month.get(last_month, 0)

    this_sessions = sessions_by_month.get(this_month, 0)
    last_sessions = sessions_by_month.get(last_month, 0)

    # Percentage change helper
    def percent_change(current, previous):
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)

    return {
        "this_revenue": this_revenue,
        "this_sessions": this_sessions,
        "rev_diff": percent_change(this_revenue, last_revenue),
        "sess_diff": percent_change(this_sessions, last_sessions),
        "rev_trend": "ok" if this_revenue >= last_revenue else "danger",
        "sess_trend": "ok" if this_sessions >= last_sessions else "danger"
    }

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    students = read_students()

    total_sessions_done = 0
    total_sessions_sold = 0
    total_amount = 0

    for s in students:
        remaining, total, pay_status, sess_status = compute(s)

        s["remaining"] = remaining
        s["total_received"] = total
        s["payment_status"] = pay_status
        s["session_status"] = sess_status
        s["sessions"] = s["sessions_done"]

        total_sessions_done += s["sessions_done"]
        total_sessions_sold += s["payment_count"] * 3
        total_amount += total

    summary = {
        "total_sessions_done": total_sessions_done,
        "total_sessions_sold": total_sessions_sold,
        "total_amount_received": total_amount
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "students": students,
            "summary": summary
        }
    )


@app.post("/pay/{student_id}")
def add_payment(student_id: int):
    students = read_students()

    for s in students:
        if s["id"] == student_id:
            s["payment_count"] += 1

            if "payment_logs" not in s:
                s["payment_logs"] = []

            s["payment_logs"].append(str(date.today()))
            s["last_action"] = "payment"
            break

    write_students(students)
    return {"success": True}

def month_key(date_str):
    return datetime.fromisoformat(date_str).strftime("%Y-%m")
@app.post("/session/{student_id}")
def add_session(student_id: int):
    students = read_students()

    for s in students:
        if s["id"] == student_id:
            s["sessions_done"] += 1

            if "session_logs" not in s:
                s["session_logs"] = []

            s["session_logs"].append(str(date.today()))
            s["last_action"] = "session"
            break

    write_students(students)
    return {"success": True}
@app.post("/student")
def add_student(data: dict = Body(...)):
    students = read_students()

    new_id = max([s["id"] for s in students], default=0) + 1

    students.append({
        "id": new_id,
        "name": data["name"],
        "phone": data["phone"],
        "fee": int(data["fee"]),
        "sessions_done": 0,
        "payment_count": 0,
        "date_received": None
    })

    write_students(students)
    return {"success": True}
@app.post("/undo/{student_id}")
def undo(student_id: int):
    students = read_students()

    for s in students:
        if s["id"] == student_id:
            if s["last_action"] == "payment" and s["payment_count"] > 0:
                s["payment_count"] -= 1
            elif s["last_action"] == "session" and s["sessions_done"] > 0:
                s["sessions_done"] -= 1

            s["last_action"] = None
            break

    write_students(students)
    return {"success": True}
@app.get("/summary")
def get_summary():
    students = read_students()

    total_sessions_done = sum(s["sessions_done"] for s in students)
    total_sessions_sold = sum(s["payment_count"] * 3 for s in students)
    total_amount = sum(s["payment_count"] * 3 * s["fee"] for s in students)

    return {
        "total_sessions_done": total_sessions_done,
        "total_sessions_sold": total_sessions_sold,
        "total_amount_received": total_amount
    }
@app.get("/dashboard")
def dashboard():
    students = read_students()
    revenue, sessions = compute_dashboard(students)

    return {
        "revenue": revenue,
        "sessions": sessions
    }
@app.get("/dashboard-view", response_class=HTMLResponse)
def dashboard_view(request: Request):
    students = read_students()

    dashboard = build_dashboard(students)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "dashboard": dashboard
        }
    )
