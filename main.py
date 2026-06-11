from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import secrets
import io
from fpdf import FPDF

from backend.database import engine, Base, get_db
from backend.models import Workout
from backend.schemas import WorkoutCreate, WorkoutResponse

# Inicjalizacja bazy danych
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RunFasta API")

# CORS - Pozwala na łączenie się z API z innych źródeł (np. przeglądarki)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware - Odpowiednik filtrów Jersey (Wymóg projektu)
@app.middleware("http")
async def custom_filter_middleware(request: Request, call_next):
    # Logika filtra: dodajemy customowy nagłówek do każdej odpowiedzi
    response = await call_next(request)
    response.headers["X-Project-Author"] = "Tomek"
    return response


security = HTTPBasic()


# Prosta autoryzacja BasicAuth (Wymóg projektu)
def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = b"admin"
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = b"password123"

    is_correct_username = secrets.compare_digest(current_username_bytes, correct_username_bytes)
    is_correct_password = secrets.compare_digest(current_password_bytes, correct_password_bytes)

    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Błędny login lub hasło",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# Helper HATEOAS (Wymóg projektu)
def create_links(workout_id: int):
    return [
        {"rel": "self", "href": f"https://127.0.0.1:8000/workouts/{workout_id}"},
        {"rel": "delete", "href": f"https://127.0.0.1:8000/workouts/{workout_id}"},
        {"rel": "pdf", "href": f"https://127.0.0.1:8000/workouts/{workout_id}/pdf"}
    ]


# --- ENDPOINTY ---

@app.get("/workouts", response_model=List[WorkoutResponse])
def get_workouts(min_dist: Optional[float] = None, db: Session = Depends(get_db), user: str = Depends(authenticate)):
    query = db.query(Workout)
    # Filtrowanie (Wymóg projektu)
    if min_dist:
        query = query.filter(Workout.distance >= min_dist)

    workouts = query.all()
    results = []
    for w in workouts:
        w_data = WorkoutResponse.model_validate(w)
        w_data.links = create_links(w.id)
        results.append(w_data)
    return results


@app.post("/workouts", response_model=WorkoutResponse)
def create_workout(workout: WorkoutCreate, db: Session = Depends(get_db), user: str = Depends(authenticate)):
    db_workout = Workout(**workout.model_dump())
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)

    res = WorkoutResponse.model_validate(db_workout)
    res.links = create_links(db_workout.id)
    return res


@app.get("/workouts/{workout_id}", response_model=WorkoutResponse)
def get_workout(workout_id: int, db: Session = Depends(get_db), user: str = Depends(authenticate)):
    w = db.query(Workout).filter(Workout.id == workout_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workout nie istnieje")

    res = WorkoutResponse.model_validate(w)
    res.links = create_links(w.id)
    return res


@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: int, db: Session = Depends(get_db), user: str = Depends(authenticate)):
    w = db.query(Workout).filter(Workout.id == workout_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workout nie istnieje")
    db.delete(w)
    db.commit()
    return {"message": "Usunięto pomyślnie"}


@app.get("/workouts/{workout_id}/pdf")
def get_workout_pdf(workout_id: int, db: Session = Depends(get_db), user: str = Depends(authenticate)):
    w = db.query(Workout).filter(Workout.id == workout_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workout nie istnieje")

    # Inicjalizacja FPDF2
    pdf = FPDF()
    pdf.add_page()

    # fpdf2 używa małych liter w nazwach standardowych czcionek
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, txt=f"RAPORT TRENINGOWY #{w.id}", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 10, txt=f"Dystans: {w.distance} km", ln=True)
    pdf.cell(0, 10, txt=f"Czas: {w.time_minutes} min", ln=True)
    pdf.cell(0, 10, txt=f"Notatka: {w.note if w.note else 'Brak'}", ln=True)

    # W fpdf2 .output() bez parametrów zwraca obiekt bytes (idealne dla FastAPI)
    pdf_output = pdf.output()
    pdf_bytes = bytes(pdf_output)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            # "attachment" wymusza pobranie pliku zamiast otwierania w przeglądarce
            "Content-Disposition": f"attachment; filename=trening_{workout_id}.pdf"
        }
    )