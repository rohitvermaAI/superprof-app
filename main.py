from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date
from fastapi.staticfiles import StaticFiles

from blob_service import read_students, write_students

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
            s["date_received"] = str(date.today())
            break
    
    s["last_action"] = "payment"
    write_students(students)
    return {"success": True}


@app.post("/session/{student_id}")
def add_session(student_id: int):
    students = read_students()

    for s in students:
        if s["id"] == student_id:
            s["sessions_done"] += 1
            break
    
    s["last_action"] = "session"
    write_students(students)
    return {"success": True}
@app.post("/student")
def add_student(data: dict = Body(...)):
    students = read_students()

    new_id = max([s["id"] for s in students], default=0) + 1

    students.append({
        "id": new_id,
        "name": data["name"],
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
