from fastapi import FastAPI, Depends, Response, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import date
from .database import engine, Base, get_db
from .models import User, Workout, Message
from .schemas import UserResponse, WorkoutResponse, WorkoutPlanCreate, WorkoutCreate, UserRegister, MessageCreate, \
    MessageResponse
from .auth import get_current_user
from fpdf import FPDF
from pydantic import BaseModel
import platform
import os
import urllib.request
import textwrap
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_SYSTEM_FONTS = {
    "Windows": [r"C:\Windows\Fonts\DejaVuSans.ttf"],
}
_FONT_URLS = {
    "regular": "https://github.com/py-pdf/fpdf2/raw/master/test/fonts/DejaVuSans.ttf",
    "bold": "https://github.com/py-pdf/fpdf2/raw/master/test/fonts/DejaVuSans-Bold.ttf",
}


def _find_or_download_font(filename, url):
    local = os.path.join(_HERE, filename)
    if os.path.exists(local):
        return local
    for p in _SYSTEM_FONTS.get(platform.system(), []):
        if os.path.exists(p):
            return p
    try:
        urllib.request.urlretrieve(url, local)
        return local
    except Exception:
        return None


DEJAVU_SANS = _find_or_download_font("DejaVuSans.ttf", _FONT_URLS["regular"])
DEJAVU_SANS_BOLD = _find_or_download_font("DejaVuSans-Bold.ttf", _FONT_URLS["bold"])

Base.metadata.create_all(bind=engine)
app = FastAPI()


@app.middleware("http")
async def log_requests_filter(request: Request, call_next):
    start_time = time.time()
    method = request.method
    path = request.url.path
    client_ip = request.client.host if request.client else "unknown"

    # Logowanie odebrania żądania (Request)
    print(f"Otrzymano żądanie: {method} {path} od IP: {client_ip}")

    response = await call_next(request)

    process_time_ms = round((time.time() - start_time) * 1000, 2)
    # Logowanie wysłania odpowiedzi (Response)
    print(
        f"Wysłano odpowiedź: {response.status_code} dla {method} {path} (Czas operacji: {process_time_ms} ms)")

    return response


def _make_pdf():
    pdf = FPDF()
    if DEJAVU_SANS and DEJAVU_SANS_BOLD:
        pdf.add_font("DejaVu", style="", fname=DEJAVU_SANS)
        pdf.add_font("DejaVu", style="B", fname=DEJAVU_SANS_BOLD)
    else:
        pdf.add_font("DejaVu", style="", fname="")
        pdf.add_font("DejaVu", style="B", fname="")
    return pdf


def _pdf_header(pdf, cols):
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("DejaVu", style="B", size=9)
    for w, label in cols[:-1]:
        pdf.cell(w, 10, text=label, border=1, align="C", fill=True)
    w, l = cols[-1]
    pdf.cell(w, 10, text=l, border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")


def _pdf_row_wrapped(pdf, cols):
    pdf.set_font("DejaVu", size=8)
    max_lines = 1
    col_lines = []

    for w, v in cols:
        char_limit = max(1, int(w / 1.5))
        lines = textwrap.wrap(str(v), width=char_limit) or [""]
        col_lines.append(lines)
        max_lines = max(max_lines, len(lines))

    row_height = max_lines * 4.5
    x_start = pdf.get_x()
    y_start = pdf.get_y()

    if y_start + row_height > 270:
        pdf.add_page()
        y_start = pdf.get_y()

    for i, (w, v) in enumerate(cols):
        lines = col_lines[i]
        padded_text = "\n".join(lines + [""] * (max_lines - len(lines)))

        x = pdf.get_x()
        y = pdf.get_y()
        pdf.multi_cell(w, 4.5, padded_text, border=1)
        pdf.set_xy(x + w, y)

    pdf.set_xy(x_start, y_start + row_height)


@app.on_event("startup")
def startup_populate(db: Session = next(get_db())):
    if not db.query(User).first():
        coach = User(username="trener1", password="123", role="COACH")
        db.add(coach)
        db.commit()
        db.refresh(coach)
        db.add(User(username="biegacz1", password="123", role="RUNNER", coach_id=coach.id))
        db.commit()



@app.post("/register", response_model=UserResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=409, detail="Użytkownik już istnieje")
    if data.role not in ["COACH", "RUNNER"]:
        raise HTTPException(status_code=400, detail="Rola musi być COACH lub RUNNER")
    user = User(username=data.username, password=data.password, role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user



@app.get("/runners", response_model=List[UserResponse])
def get_my_runners(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener ma dostęp do listy biegaczy")
    return db.query(User).filter(User.coach_id == user.id).all()


class AddRunnerRequest(BaseModel):
    runner_id: int


@app.post("/runners/add", response_model=UserResponse)
def add_runner(body: AddRunnerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może dodawać biegaczy")
    runner = db.query(User).filter(User.id == body.runner_id, User.role == "RUNNER").first()
    if not runner:
        raise HTTPException(status_code=404, detail="Biegacz nie istnieje")
    if runner.coach_id is not None and runner.coach_id != user.id:
        raise HTTPException(status_code=409, detail="Ten biegacz należy już do innego trenera")
    if runner.coach_id == user.id:
        raise HTTPException(status_code=409, detail="Ten biegacz jest już w Twojej grupie")
    runner.coach_id = user.id
    db.commit()
    db.refresh(runner)
    return runner


@app.get("/runners/unassigned", response_model=List[UserResponse])
def get_unassigned_runners(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może przeglądać biegaczy do dodania")
    return db.query(User).filter(User.role == "RUNNER", User.coach_id == None).all()


@app.delete("/runners/{runner_id}")
def remove_runner(runner_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może usuwać biegaczy z grupy")
    runner = db.query(User).filter(User.id == runner_id, User.coach_id == user.id).first()
    if not runner:
        raise HTTPException(status_code=404, detail="Biegacz nie znaleziony")
    runner.coach_id = None
    db.commit()
    return {"message": f"Biegacz {runner.username} usunięty z grupy"}


@app.get("/workouts", response_model=List[WorkoutResponse])
def get_workouts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "COACH":
        runner_ids = [r.id for r in db.query(User).filter(User.coach_id == user.id).all()]
        workouts = db.query(Workout).filter(Workout.runner_id.in_(runner_ids)).all()
    else:
        workouts = db.query(Workout).filter(Workout.runner_id == user.id).all()
    results = []
    for w in workouts:
        w_data = WorkoutResponse.model_validate(w)
        w_data.is_planned = bool(w_data.is_planned)
        w_data.links = [{"rel": "self", "href": f"/workouts/{w.id}"}]
        results.append(w_data)
    return results


@app.get("/workouts/today", response_model=List[WorkoutResponse])
def get_today_workouts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workouts = db.query(Workout).filter(
        Workout.runner_id == user.id,
        Workout.workout_date == date.today(),
        Workout.is_planned == True,
        Workout.completed == False
    ).all()
    results = []
    for w in workouts:
        w_data = WorkoutResponse.model_validate(w)
        results.append(w_data)
    return results


@app.get("/workouts/runner/{runner_id}/today", response_model=List[WorkoutResponse])
def get_runner_today_workouts(runner_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może podglądać treningi")
    workouts = db.query(Workout).filter(
        Workout.runner_id == runner_id,
        Workout.workout_date == date.today(),
        Workout.is_planned == True
    ).all()
    results = []
    for w in workouts:
        w_data = WorkoutResponse.model_validate(w)
        results.append(w_data)
    return results


@app.patch("/workouts/{workout_id}/complete")
def complete_workout(workout_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Trening nie istnieje")
    if workout.runner_id != user.id:
        raise HTTPException(status_code=403, detail="Możesz oznaczać tylko swoje treningi")
    workout.completed = True
    db.commit()
    return {"message": "Trening ukończony"}


@app.post("/workouts/plan", response_model=WorkoutResponse)
def plan_workout(plan: WorkoutPlanCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może planować")
    db_workout = Workout(
        runner_id=plan.runner_id, distance=plan.distance,
        time_minutes=plan.time_minutes, note=plan.note,
        is_planned=True, workout_date=plan.workout_date or date.today(),
        target_pace=plan.target_pace, is_interval=plan.is_interval,
        interval_repeats=plan.interval_repeats,
        interval_distance_meters=plan.interval_distance_meters,
        interval_recovery=plan.interval_recovery
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return WorkoutResponse.model_validate(db_workout)


@app.post("/workouts", response_model=WorkoutResponse)
def create_workout(workout: WorkoutCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_workout = Workout(
        runner_id=user.id, distance=workout.distance,
        time_minutes=workout.time_minutes, note=workout.note,
        is_planned=False, workout_date=workout.workout_date or date.today(),
        target_pace=workout.target_pace, is_interval=False
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return WorkoutResponse.model_validate(db_workout)


@app.get("/stats")
def get_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workouts = db.query(Workout).filter(Workout.runner_id == user.id, Workout.is_planned == False).all()
    return {"total_distance": round(float(sum(w.distance for w in workouts)), 2),
            "count": len(workouts)}


@app.get("/stats/runner/{runner_id}")
def get_runner_stats(
        runner_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    if user.role == "COACH":
        runner = db.query(User).filter(User.id == runner_id, User.coach_id == user.id).first()
        if not runner:
            raise HTTPException(status_code=403, detail="Ten biegacz nie należy do Ciebie")
    elif user.id != runner_id:
        raise HTTPException(status_code=403, detail="Brak dostępu")

    query = db.query(Workout).filter(Workout.runner_id == runner_id,
                                     or_(Workout.is_planned == False, Workout.completed == True))
    if start_date:
        query = query.filter(Workout.workout_date >= start_date)
    if end_date:
        query = query.filter(Workout.workout_date <= end_date)

    completed_workouts = query.all()
    return {
        "total_distance": round(float(sum(w.distance for w in completed_workouts)), 2),
        "count": len(completed_workouts)
    }


@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Trening nie istnieje")
    if user.role == "RUNNER" and workout.runner_id != user.id:
        raise HTTPException(status_code=403, detail="Brak uprawnień")
    db.delete(workout)
    db.commit()
    return {"message": "Usunięto"}


# CZAT

@app.post("/messages", response_model=MessageResponse)
def send_message(msg: MessageCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_msg = Message(sender_id=user.id, receiver_id=msg.receiver_id, text=msg.text)
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg


@app.get("/messages/thread/{other_id}", response_model=List[MessageResponse])
def get_thread(other_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Message).filter(
        or_(
            and_(Message.sender_id == user.id, Message.receiver_id == other_id),
            and_(Message.sender_id == other_id, Message.receiver_id == user.id)
        )
    ).order_by(Message.created_at.asc()).all()


# PDF

@app.get("/report/pdf/runner/{runner_id}")
def report_runner(runner_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == runner_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Biegacz nie istnieje")

    workouts = db.query(Workout).filter(Workout.runner_id == runner_id).order_by(Workout.workout_date.desc()).all()
    if not workouts:
        raise HTTPException(status_code=400, detail="Brak zrealizowanych treningów")

    pdf = _make_pdf()
    pdf.add_page()
    pdf.set_font("DejaVu", style="B", size=14)
    pdf.cell(0, 10, text=f"RAPORT TRENINGÓW: {target.username.upper()}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    cols = [(10, "Lp."), (12, "ID"), (20, "Dystans"), (18, "Czas"), (22, "Data"), (20, "Typ"), (30, "Tempo"),
            (58, "Zalecenia / Komentarz")]
    _pdf_header(pdf, cols)

    total = 0.0
    for idx, w in enumerate(workouts):
        lp = idx + 1
        w_type = "Zadanie" if w.is_planned else "Własny"
        status = "Zakonczony" if (w.completed or not w.is_planned) else "W planie"

        if w.completed or not w.is_planned:
            total += w.distance

        desc = w.note or "-"
        if w.is_interval:
            desc = f"Interwały {w.interval_repeats}x{w.interval_distance_meters}m (p: {w.interval_recovery or '-'}) | " + desc

        _pdf_row_wrapped(pdf, [
            (10, lp), (12, w.id), (20, f"{w.distance} km"), (18, f"{w.time_minutes} min"),
            (22, str(w.workout_date)), (20, f"{w_type}{status}"), (30, w.target_pace or "-"), (58, desc)
        ])

    pdf.ln(4)
    pdf.set_font("DejaVu", style="B", size=10)
    pdf.cell(0, 10, text=f"Suma przebiegniętego dystansu (ukończone): {round(total, 2)} km", new_x="LMARGIN",
             new_y="NEXT")
    return Response(content=bytes(pdf.output()), media_type="application/pdf")


@app.get("/report/pdf/plan/{runner_id}")
def report_plan_single(runner_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == runner_id).first()
    plans = db.query(Workout).filter(Workout.runner_id == runner_id, Workout.is_planned == True).order_by(
        Workout.workout_date.desc()).all()
    if not plans:
        raise HTTPException(status_code=400, detail="Brak zaplanowanych treningów")

    pdf = _make_pdf()
    pdf.add_page()
    pdf.set_font("DejaVu", style="B", size=14)
    pdf.cell(0, 10, text=f"PLAN TRENINGOWY BIEGACZA: {target.username.upper()}", new_x="LMARGIN", new_y="NEXT",
             align="C")
    pdf.ln(5)

    cols = [(10, "Lp."), (12, "ID"), (20, "Dystans"), (18, "Czas"), (22, "Data"), (30, "Tempo"),
            (78, "Zalecenia / Interwały")]
    _pdf_header(pdf, cols)

    for idx, p in enumerate(plans):
        lp = idx + 1
        desc = p.note or "-"
        if p.is_interval:
            desc = f"[INT] {p.interval_repeats}x{p.interval_distance_meters}m (p: {p.interval_recovery or '-'}) | " + desc

        _pdf_row_wrapped(pdf, [
            (10, lp), (12, p.id), (20, f"{p.distance} km"), (18, f"{p.time_minutes} min"),
            (22, str(p.workout_date)), (30, p.target_pace or "-"), (78, desc)
        ])

    return Response(content=bytes(pdf.output()), media_type="application/pdf")


@app.get("/report/pdf/plan/all")
def report_plan_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    runners = db.query(User).filter(User.coach_id == user.id).all()
    if not runners:
        raise HTTPException(status_code=400, detail="Brak przypisanych biegaczy")

    pdf = _make_pdf()
    pdf.add_page()
    pdf.set_font("DejaVu", style="B", size=16)
    pdf.cell(0, 12, text="GRUPOWE PLANY TRENINGOWE", new_x="LMARGIN", new_y="NEXT", align="C")

    cols = [(10, "Lp."), (12, "ID"), (20, "Dystans"), (18, "Czas"), (22, "Data"), (30, "Tempo"), (78, "Zalecenia")]

    for r in runners:
        plans = db.query(Workout).filter(Workout.runner_id == r.id, Workout.is_planned == True).order_by(
            Workout.workout_date.desc()).all()
        pdf.ln(6)
        pdf.set_font("DejaVu", style="B", size=11)
        pdf.cell(0, 8, text=f"Biegacz: {r.username}", new_x="LMARGIN", new_y="NEXT")
        if not plans:
            pdf.set_font("DejaVu", size=9)
            pdf.cell(0, 6, text=" - brak planów", new_x="LMARGIN", new_y="NEXT")
            continue

        _pdf_header(pdf, cols)
        for idx, p in enumerate(plans):
            lp = idx + 1
            desc = p.note or "-"
            if p.is_interval:
                desc = f"[INT] {p.interval_repeats}x{p.interval_distance_meters}m | " + desc

            _pdf_row_wrapped(pdf, [
                (10, lp), (12, p.id), (20, f"{p.distance} km"), (18, f"{p.time_minutes} min"),
                (22, str(p.workout_date)), (30, p.target_pace or "-"), (78, desc)
            ])

    return Response(content=bytes(pdf.output()), media_type="application/pdf")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        ssl_certfile="cert.pem",
        ssl_keyfile="key.pem",
        reload=True
    )