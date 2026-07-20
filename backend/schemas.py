from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional
from datetime import date, datetime


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    coach_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class UserRegister(BaseModel):
    username: str
    password: str
    role: str


class WorkoutResponse(BaseModel):
    id: int
    runner_id: int
    distance: float
    time_minutes: int
    note: Optional[str]
    is_planned: bool
    workout_date: date
    completed: bool

    target_pace: Optional[str] = None
    is_interval: bool = False
    interval_repeats: Optional[int] = None
    interval_distance_meters: Optional[int] = None
    interval_recovery: Optional[str] = None

    links: List[Dict[str, str]] = []
    model_config = ConfigDict(from_attributes=True)


class WorkoutPlanCreate(BaseModel):
    runner_id: int
    distance: float
    time_minutes: int
    note: Optional[str] = None
    workout_date: Optional[date] = None

    target_pace: Optional[str] = None
    is_interval: Optional[bool] = False
    interval_repeats: Optional[int] = None
    interval_distance_meters: Optional[int] = None
    interval_recovery: Optional[str] = None


class WorkoutCreate(BaseModel):
    distance: float
    time_minutes: int
    note: Optional[str] = None
    workout_date: Optional[date] = None
    target_pace: Optional[str] = None


class MessageCreate(BaseModel):
    receiver_id: int
    text: str


class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    text: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)