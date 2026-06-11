from fastapi import FastAPI, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .database import engine, Base, get_db
from .models import User, Workout
from .schemas import UserResponse, WorkoutResponse, WorkoutPlanCreate, WorkoutCreate
from .auth import get_current_user
from fpdf import FPDF
from pydantic import BaseModel
import platform
import os
import urllib.request

# --- Obsługa fontów z polskimi znakami (cross-platform) ---
_HERE = os.path.dirname(os.path.abspath(__file__))

_SYSTEM_FONTS = {
    "Linux": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ],
    "Darwin": [
        "/Library/Fonts/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/DejaVuSans.ttf",
    ],
    "Windows": [
        r"C:\Windows\Fonts\DejaVuSans.ttf",
    ],
}

_FONT_URLS = {
    "regular": "https://github.com/py-pdf/fpdf2/raw/master/test/fonts/DejaVuSans.ttf",
    "bold":    "https://github.com/py-pdf/fpdf2/raw/master/test/fonts/DejaVuSans-Bold.ttf",
}


def _find_or_download_font(filename: str, url: str) -> str:
    local_path = os.path.join(_HERE, filename)
    if os.path.exists(local_path):
        return local_path
    for sys_path in _SYSTEM_FONTS.get(platform.system(), []):
        if os.path.basename(sys_path) == filename and os.path.exists(sys_path):
            return sys_path
    print(f"[PDF] Pobieranie fontu {filename} z internetu...")
    urllib.request.urlretrieve(url, local_path)
    print(f"[PDF] Zapisano: {local_path}")
    return local_path


DEJAVU_SANS      = _find_or_download_font("DejaVuSans.ttf",      _FONT_URLS["regular"])
DEJAVU_SANS_BOLD = _find_or_download_font("DejaVuSans-Bold.ttf", _FONT_URLS["bold"])

Base.metadata.create_all(bind=engine)
app = FastAPI()


# --- Pomocnicza funkcja budująca PDF ---
def _make_pdf() -> FPDF:
    pdf = FPDF()
    pdf.add_font("DejaVu",  style="",  fname=DEJAVU_SANS)
    pdf.add_font("DejaVu",  style="B", fname=DEJAVU_SANS_BOLD)
    return pdf


def _pdf_table_header(pdf: FPDF, cols: list[tuple[int, str]]):
    """cols = [(szerokość, nagłówek), ...]"""
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("DejaVu", style="B", size=11)
    for width, label in cols[:-1]:
        pdf.cell(width, 10, text=label, border=1, align="C", fill=True)
    w, l = cols[-1]
    pdf.cell(w, 10, text=l, border=1, align="C", fill=True,
             new_x="LMARGIN", new_y="NEXT")


def _pdf_table_row(pdf: FPDF, cols: list[tuple[int, str]]):
    pdf.set_font("DejaVu", size=10)
    for width, value in cols[:-1]:
        pdf.cell(width, 9, text=str(value), border=1)
    w, v = cols[-1]
    pdf.cell(w, 9, text=str(v), border=1, new_x="LMARGIN", new_y="NEXT")


# --- Inicjalizacja testowych danych ---
@app.on_event("startup")
def startup_populate(db: Session = next(get_db())):
    if not db.query(User).first():
        coach = User(username="trener1", password="123", role="COACH")
        db.add(coach)
        db.commit()
        db.refresh(coach)
        db.add(User(username="biegacz1", password="123", role="RUNNER", coach_id=coach.id))
        db.commit()


# ==================== ENDPOINTY ====================

@app.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user


# --- Biegacze ---

@app.get("/runners", response_model=List[UserResponse])
def get_my_runners(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener ma dostęp do listy biegaczy")
    return db.query(User).filter(User.coach_id == user.id).all()


class AddRunnerRequest(BaseModel):
    username: str


@app.post("/runners/add", response_model=UserResponse)
def add_runner(body: AddRunnerRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Trener przypisuje istniejącego biegacza do swojej grupy po username."""
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
    """Trener usuwa biegacza ze swojej grupy (nie kasuje konta)."""
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może usuwać biegaczy z grupy")

    runner = db.query(User).filter(User.id == runner_id, User.coach_id == user.id).first()
    if not runner:
        raise HTTPException(status_code=404, detail="Biegacz nie znaleziony lub nie należy do Ciebie")

    runner.coach_id = None
    db.commit()
    return {"message": f"Biegacz {runner.username} usunięty z grupy",
            "hateoas": [{"rel": "runners", "href": "/runners"}]}


# --- Treningi ---

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


@app.post("/workouts/plan", response_model=WorkoutResponse)
def plan_workout(plan: WorkoutPlanCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "COACH":
        raise HTTPException(status_code=403, detail="Tylko trener może planować treningi")

    runner = db.query(User).filter(User.id == plan.runner_id, User.coach_id == user.id).first()
    if not runner:
        raise HTTPException(status_code=404, detail="Biegacz nie znaleziony lub nie przypisany do Ciebie")

    db_workout = Workout(runner_id=plan.runner_id, distance=plan.distance,
                         time_minutes=plan.time_minutes, note=plan.note, is_planned=True)
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    res = WorkoutResponse.model_validate(db_workout)
    res.links = [{"rel": "cancel_plan", "href": f"/workouts/{res.id}"}]
    return res


@app.post("/workouts", response_model=WorkoutResponse)
def create_workout(workout: WorkoutCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_workout = Workout(runner_id=user.id, distance=workout.distance,
                         time_minutes=workout.time_minutes, note=workout.note, is_planned=False)
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return WorkoutResponse.model_validate(db_workout)


@app.get("/stats")
def get_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workouts = db.query(Workout).filter(Workout.runner_id == user.id).all()
    completed = [w for w in workouts if not w.is_planned]
    return {
        "total_distance": round(float(sum(w.distance for w in completed)), 2),
        "count": len(completed)
    }


@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workout = db.query(Workout).filter(Workout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Trening nie istnieje")

    if user.role == "RUNNER":
        if workout.runner_id != user.id:
            raise HTTPException(status_code=403, detail="Nie możesz usuwać cudzych treningów")
    elif user.role == "COACH":
        runner = db.query(User).filter(User.id == workout.runner_id).first()
        if not runner or runner.coach_id != user.id:
            raise HTTPException(status_code=403, detail="Ten biegacz nie należy do Ciebie")

    db.delete(workout)
    db.commit()
    return {"message": f"Trening {workout_id} usunięty",
            "hateoas": [{"rel": "list", "href": "/workouts"}]}


# --- Raporty PDF ---

@app.get("/report/pdf/runner/{runner_id}")
def report_runner(runner_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """PDF zrealizowanych treningów danego biegacza (biegacz swój, trener swojego biegacza)."""
    target = db.query(User).filter(User.id == runner_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje")
    if user.role == "RUNNER" and user.id != runner_id:
        raise HTTPException(status_code=403, detail="Biegacz może pobrać tylko swój raport")
    if user.role == "COACH" and target.coach_id != user.id:
        raise HTTPException(status_code=403, detail="To nie jest Twój biegacz")

    workouts = db.query(Workout).filter(
        Workout.runner_id == runner_id, Workout.is_planned == False
    ).all()
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

    cols = [(15, "ID"), (40, "Dystans (km)"), (35, "Czas (min)"), (100, "Notatki")]
    _pdf_table_header(pdf, cols)
    total = 0.0
    for w in workouts:
        note = (str(w.note)[:55] + "…") if w.note and len(str(w.note)) > 55 else (w.note or "-")
        _pdf_table_row(pdf, [(15, w.id), (40, w.distance), (35, w.time_minutes), (100, note)])
        total += w.distance

    pdf.ln(4)
    pdf.set_font("DejaVu", style="B", size=12)
    pdf.cell(0, 10, text=f"ŁĄCZNY DYSTANS: {round(total, 2)} km", new_x="LMARGIN", new_y="NEXT")

    return Response(content=bytes(pdf.output()), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=raport_{target.username}.pdf"})


@app.get("/report/pdf/plan/{runner_id}")
def report_plan_single(runner_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """PDF planów treningowych dla jednego biegacza (tylko trener)."""
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

    cols = [(15, "ID"), (40, "Dystans (km)"), (35, "Czas (min)"), (100, "Zalecenia")]
    _pdf_table_header(pdf, cols)
    for p in plans:
        note = (str(p.note)[:55] + "…") if p.note and len(str(p.note)) > 55 else (p.note or "-")
        _pdf_table_row(pdf, [(15, p.id), (40, p.distance), (35, p.time_minutes), (100, note)])

    return Response(content=bytes(pdf.output()), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=plan_{target.username}.pdf"})


@app.get("/report/pdf/plan/all")
def report_plan_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """PDF planów treningowych dla wszystkich biegaczy trenera."""
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

    cols = [(15, "ID"), (40, "Dystans (km)"), (35, "Czas (min)"), (100, "Zalecenia")]
    has_any = False

    for runner in runners:
        plans = db.query(Workout).filter(
            Workout.runner_id == runner.id, Workout.is_planned == True
        ).all()

        pdf.ln(4)
        pdf.set_font("DejaVu", style="B", size=13)
        pdf.cell(0, 10, text=f"Biegacz: {runner.username}",
                 new_x="LMARGIN", new_y="NEXT")

        if not plans:
            pdf.set_font("DejaVu", size=10)
            pdf.cell(0, 8, text="  — brak planów —", new_x="LMARGIN", new_y="NEXT")
            continue

        has_any = True
        _pdf_table_header(pdf, cols)
        for p in plans:
            note = (str(p.note)[:55] + "…") if p.note and len(str(p.note)) > 55 else (p.note or "-")
            _pdf_table_row(pdf, [(15, p.id), (40, p.distance), (35, p.time_minutes), (100, note)])

    return Response(content=bytes(pdf.output()), media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=plany_wszystkich.pdf"})