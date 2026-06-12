from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Optional
from datetime import date

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    model_config = ConfigDict(from_attributes=True)

class UserRegister(BaseModel):
    username: str
    password: str
    role: str  # "COACH" lub "RUNNER"

class WorkoutResponse(BaseModel):
    id: int
    runner_id: int
    distance: float
    time_minutes: int
    note: Optional[str]
    is_planned: bool
    workout_date: date
    completed: bool
    links: List[Dict[str, str]] = []
    model_config = ConfigDict(from_attributes=True)

class WorkoutPlanCreate(BaseModel):
    runner_id: int
    distance: float
    time_minutes: int
    note: Optional[str] = None
    workout_date: Optional[date] = None

class WorkoutCreate(BaseModel):
    distance: float
    time_minutes: int
    note: Optional[str] = None
    workout_date: Optional[date] = None