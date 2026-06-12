from fastapi import FastAPI, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from .database import engine, Base, get_db
from .models import User, Workout
from .schemas import UserResponse, WorkoutResponse, WorkoutPlanCreate, WorkoutCreate, UserRegister
from .auth import get_current_user
from fpdf import FPDF
from pydantic import BaseModel
import platform
import os
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_SYSTEM_FONTS = {
    "Linux": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf"],
    "Darwin": ["/Library/Fonts/DejaVuSans.ttf"],
    "Windows": [r"C:\Windows\Fonts\DejaVuSans.ttf"],
}
_FONT_URLS = {
    "regular": "https://github.com/py-pdf/fpdf2/raw/master/test/fonts/DejaVuSans.ttf",
    "bold":    "https://github.com/py-pdf/fpdf2/raw/master/test/fonts/DejaVuSans-Bold.ttf",
}

def _find_or_download_font(filename, url):
    local = os.path.join(_HERE, filename)
    if os.path.exists(local):
        return local
    for p in _SYSTEM_FONTS.get(platform.system(), []):
        if os.path.basename(p) == filename and os.path.exists(p):
            return p
    print(f"[PDF] Pobieranie {filename}...")
    urllib.request.urlretrieve(url, local)
    return local

DEJAVU_SANS      = _find_or_download_font("DejaVuSans.ttf",      _FONT_URLS["regular"])
DEJAVU_SANS_BOLD = _find_or_download_font("DejaVuSans-Bold.ttf", _FONT_URLS["bold"])

Base.metadata.create_all(bind=engine)
app = FastAPI()


def _make_pdf():
    pdf = FPDF()
    pdf.add_font("DejaVu", style="",  fname=DEJAVU_SANS)
    pdf.add_font("DejaVu", style="B", fname=DEJAVU_SANS_BOLD)
    return pdf

def _pdf_header(pdf, cols):
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("DejaVu", style="B", size=11)
    for w, label in cols[:-1]:
        pdf.cell(w, 10, text=label, border=1, align="C", fill=True)
    w, l = cols[-1]
    pdf.cell(w, 10, text=l, border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")

def _pdf_row(pdf, cols):
    pdf.set_font("DejaVu", size=10)
    for w, v in cols[:-1]:
        pdf.cell(w, 9, text=str(v), border=1)
    w, v = cols[-1]
    pdf.cell(w, 9, text=str(v), border=1, new_x="LMARGIN", new_y="NEXT")


@app.on_event("startup")
def startup_populate(db: Session = next(get_db())):
    if not db.query(User).first():
        coach = User(username="trener1", password="123", role="COACH")
        db.add(coach)
        db.commit()
        db.refresh(coach)
        db.add(User(username="biegacz1", password="123", role="RUNNER", coach_id=coach.id))
        db.commit()


# ==================== AUTH ====================

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


# ==================== BIEGACZE ====================

@app.get("/runners", response_model=List[UserResponse])
def get_my_runners(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener ma dostęp do listy biegaczy")
    return db.query(User).filter(User.coach_id == user.id).all()


class AddRunnerRequest(BaseModel):
    username: str


@app.post("/runners/add", response_model=UserResponse)
def add_runner(body: AddRunnerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może dodawać biegaczy")
    runner = db.query(User).filter(User.username == body.username, User.role == "RUNNER").first()
    if not runner:
        raise HTTPException(status_code=404, detail=f"Biegacz '{body.username}' nie istnieje")
    if runner.coach_id is not None and runner.coach_id != user.id:
        raise HTTPException(status_code=409, detail="Ten biegacz należy już do innego trenera")
    if runner.coach_id == user.id:
        raise HTTPException(status_code=409, detail="Ten biegacz jest już w Twojej grupie")
    runner.coach_id = user.id
    db.commit()
    db.refresh(runner)
    return runner


@app.delete("/runners/{runner_id}")
def remove_runner(runner_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może usuwać biegaczy z grupy")
    runner = db.query(User).filter(User.id == runner_id, User.coach_id == user.id).first()
    if not runner:
        raise HTTPException(status_code=404, detail="Biegacz nie znaleziony lub nie należy do Ciebie")
    runner.coach_id = None
    db.commit()
    return {"message": f"Biegacz {runner.username} usunięty z grupy",
            "hateoas": [{"rel": "runners", "href": "/runners"}]}


# ==================== TRENINGI ====================

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
        if user.role == "COACH":
            w_data.links.append({"rel": "delete", "href": f"/workouts/{w.id}"})
        results.append(w_data)
    return results


@app.get("/workouts/today", response_model=List[WorkoutResponse])
def get_today_workouts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Dzisiejsze nieukończone plany biegacza."""
    workouts = db.query(Workout).filter(
        Workout.runner_id == user.id,
        Workout.workout_date == date.today(),
        Workout.is_planned == True,
        Workout.completed == False
    ).all()
    results = []
    for w in workouts:
        w_data = WorkoutResponse.model_validate(w)
        w_data.links = [
            {"rel": "self", "href": f"/workouts/{w.id}"},
            {"rel": "complete", "href": f"/workouts/{w.id}/complete"}
        ]
        results.append(w_data)
    return results


@app.get("/workouts/runner/{runner_id}/today", response_model=List[WorkoutResponse])
def get_runner_today_workouts(runner_id: int, user: User = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """Dzisiejsze plany wybranego biegacza (widok trenera)."""
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może przeglądać treningi swoich biegaczy")
    runner = db.query(User).filter(User.id == runner_id, User.coach_id == user.id).first()
    if not runner:
        raise HTTPException(status_code=404, detail="Biegacz nie znaleziony lub nie należy do Ciebie")
    workouts = db.query(Workout).filter(
        Workout.runner_id == runner_id,
        Workout.workout_date == date.today(),
        Workout.is_planned == True
    ).all()
    results = []
    for w in workouts:
        w_data = WorkoutResponse.model_validate(w)
        w_data.links = [{"rel": "self", "href": f"/workouts/{w.id}"}]
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
    db.refresh(workout)
    return {"message": f"Trening {workout_id} ukończony",
            "hateoas": [{"rel": "list", "href": "/workouts"}]}


@app.post("/workouts/plan", response_model=WorkoutResponse)
def plan_workout(plan: WorkoutPlanCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może planować treningi")
    runner = db.query(User).filter(User.id == plan.runner_id, User.coach_id == user.id).first()
    if not runner:
        raise HTTPException(status_code=404, detail="Biegacz nie znaleziony lub nie przypisany do Ciebie")
    db_workout = Workout(runner_id=plan.runner_id, distance=plan.distance,
                         time_minutes=plan.time_minutes, note=plan.note,
                         is_planned=True, workout_date=plan.workout_date or date.today())
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    res = WorkoutResponse.model_validate(db_workout)
    res.links = [{"rel": "cancel_plan", "href": f"/workouts/{res.id}"}]
    return res


@app.post("/workouts", response_model=WorkoutResponse)
def create_workout(workout: WorkoutCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_workout = Workout(runner_id=user.id, distance=workout.distance,
                         time_minutes=workout.time_minutes, note=workout.note,
                         is_planned=False, workout_date=workout.workout_date or date.today())
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return WorkoutResponse.model_validate(db_workout)


@app.get("/stats")
def get_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workouts = db.query(Workout).filter(Workout.runner_id == user.id).all()
    completed = [w for w in workouts if not w.is_planned]
    return {"total_distance": round(float(sum(w.distance for w in completed)), 2),
            "count": len(completed)}


@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Trening nie istnieje")
    if user.role == "RUNNER" and workout.runner_id != user.id:
        raise HTTPException(status_code=403, detail="Nie możesz usuwać cudzych treningów")
    if user.role == "COACH":
        runner = db.query(User).filter(User.id == workout.runner_id).first()
        if not runner or runner.coach_id != user.id:
            raise HTTPException(status_code=403, detail="Ten biegacz nie należy do Ciebie")
    db.delete(workout)
    db.commit()
    return {"message": f"Trening {workout_id} usunięty",
            "hateoas": [{"rel": "list", "href": "/workouts"}]}


# ==================== PDF ====================

@app.get("/report/pdf/runner/{runner_id}")
def report_runner(runner_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.query(User).filter(User.id == runner_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    if user.role == "RUNNER" and user.id != runner_id:
        raise HTTPException(status_code=403, detail="Biegacz może pobrać tylko swój raport")
    if user.role == "COACH" and target.coach_id != user.id:
        raise HTTPException(status_code=403, detail="To nie jest Twój biegacz")

    workouts = db.query(Workout).filter(Workout.runner_id == runner_id,
                                         Workout.is_planned == False).all()
    if not workouts:
        raise HTTPException(status_code=400, detail="Brak zrealizowanych treningów")

    pdf = _make_pdf()
    pdf.add_page()
    pdf.set_font("DejaVu", style="B", size=16)
    pdf.cell(0, 12, text=f"RAPORT TRENINGOWY: {target.username}",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", size=9)
    pdf.cell(0, 8, text=f"Wygenerowano przez: {user.username}",
             new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(6)
    cols = [(15, "ID"), (35, "Dystans (km)"), (30, "Czas (min)"), (35, "Data"), (75, "Notatki")]
    _pdf_header(pdf, cols)
    total = 0.0
    for w in workouts:
        note = (str(w.note)[:40] + "…") if w.note and len(str(w.note)) > 40 else (w.note or "-")
        _pdf_row(pdf, [(15, w.id), (35, w.distance), (30, w.time_minutes),
                       (35, str(w.workout_date or "-")), (75, note)])
        total += w.distance
    pdf.ln(4)
    pdf.set_font("DejaVu", style="B", size=12)
    pdf.cell(0, 10, text=f"ŁĄCZNY DYSTANS: {round(total, 2)} km", new_x="LMARGIN", new_y="NEXT")
    return Response(content=bytes(pdf.output()), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=raport_{target.username}.pdf"})


@app.get("/report/pdf/plan/{runner_id}")
def report_plan_single(runner_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może pobierać plany")
    target = db.query(User).filter(User.id == runner_id, User.coach_id == user.id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Biegacz nie znaleziony lub nie należy do Ciebie")
    plans = db.query(Workout).filter(Workout.runner_id == runner_id, Workout.is_planned == True).all()
    if not plans:
        raise HTTPException(status_code=400, detail="Brak planów treningowych dla tego biegacza")

    pdf = _make_pdf()
    pdf.add_page()
    pdf.set_font("DejaVu", style="B", size=16)
    pdf.cell(0, 12, text=f"PLAN TRENINGOWY: {target.username}",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", size=9)
    pdf.cell(0, 8, text=f"Trener: {user.username}", new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(6)
    cols = [(15, "ID"), (35, "Dystans (km)"), (30, "Czas (min)"), (35, "Data"), (75, "Zalecenia")]
    _pdf_header(pdf, cols)
    for p in plans:
        note = (str(p.note)[:40] + "…") if p.note and len(str(p.note)) > 40 else (p.note or "-")
        _pdf_row(pdf, [(15, p.id), (35, p.distance), (30, p.time_minutes),
                       (35, str(p.workout_date or "-")), (75, note)])
    return Response(content=bytes(pdf.output()), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=plan_{target.username}.pdf"})


@app.get("/report/pdf/plan/all")
def report_plan_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może pobierać plany")
    runners = db.query(User).filter(User.coach_id == user.id).all()
    if not runners:
        raise HTTPException(status_code=400, detail="Nie masz żadnych biegaczy w grupie")

    pdf = _make_pdf()
    pdf.add_page()
    pdf.set_font("DejaVu", style="B", size=18)
    pdf.cell(0, 14, text="PLANY TRENINGOWE — WSZYSCY BIEGACZE",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", size=9)
    pdf.cell(0, 8, text=f"Trener: {user.username}", new_x="LMARGIN", new_y="NEXT", align="R")
    pdf.ln(4)
    cols = [(15, "ID"), (35, "Dystans (km)"), (30, "Czas (min)"), (35, "Data"), (75, "Zalecenia")]

    for runner in runners:
        plans = db.query(Workout).filter(Workout.runner_id == runner.id,
                                          Workout.is_planned == True).all()
        pdf.ln(4)
        pdf.set_font("DejaVu", style="B", size=13)
        pdf.cell(0, 10, text=f"Biegacz: {runner.username}", new_x="LMARGIN", new_y="NEXT")
        if not plans:
            pdf.set_font("DejaVu", size=10)
            pdf.cell(0, 8, text="  — brak planów —", new_x="LMARGIN", new_y="NEXT")
            continue
        _pdf_header(pdf, cols)
        for p in plans:
            note = (str(p.note)[:40] + "…") if p.note and len(str(p.note)) > 40 else (p.note or "-")
            _pdf_row(pdf, [(15, p.id), (35, p.distance), (30, p.time_minutes),
                           (35, str(p.workout_date or "-")), (75, note)])

    return Response(content=bytes(pdf.output()), media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=plany_wszystkich.pdf"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, ssl_certfile="cert.pem", ssl_keyfile="key.pem")