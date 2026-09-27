from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import List, Optional
from .engine import TaskStatus

class TaskBase(BaseModel):
    title: str
    description: str
    status: TaskStatus = TaskStatus.BACKLOG
    position: int = 0
    duration_days: int = 1
    planned_start: date
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    position: Optional[int] = None
    duration_days: Optional[int] = None
    planned_start: Optional[date] = None

class Task(TaskBase):
    id: str
    start_date: date
    end_date: date
    blocked: bool
    is_critical: bool
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Dependency(BaseModel):
    prerequisite_id: str
    dependent_id: str

class DependencySuggestion(BaseModel):
    id: int
    prerequisite_id: str
    dependent_id: str
    confidence: str
    rationale: str
    status: str
