from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, Date, DateTime
from sqlalchemy.orm import relationship
from datetime import date, datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String)
    coach_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    runner_id = Column(Integer, ForeignKey("users.id"))
    distance = Column(Float)
    time_minutes = Column(Integer)
    note = Column(String, nullable=True)
    is_planned = Column(Boolean, default=False)
    workout_date = Column(Date, default=date.today)
    completed = Column(Boolean, default=False)
    target_pace = Column(String, nullable=True)  # np. "5:15 min/km"
    is_interval = Column(Boolean, default=False)
    interval_repeats = Column(Integer, nullable=True)  # np. 5
    interval_distance_meters = Column(Integer, nullable=True)  # np. 400 (metrów)
    interval_recovery = Column(String, nullable=True)  # np. "2 min marszu"


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    text = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)