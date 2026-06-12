from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from datetime import date
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)  # W prawdziwej apce byłby hash
    role = Column(String)      # "COACH" lub "RUNNER"
    # Relacja: Biegacz ma trenera
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=True)

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    runner_id = Column(Integer, ForeignKey("users.id"))
    distance = Column(Float)
    time_minutes = Column(Integer)
    note = Column(String, nullable=True)
    is_planned = Column(Boolean, default=False) # True = zadanie od trenera, False = wpis biegacza
    workout_date = Column(Date, default=date.today)  # Data treningu
    completed = Column(Boolean, default=False)  # Czy trening został ukończony