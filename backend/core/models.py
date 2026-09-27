from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
import datetime
from .database import Base
from .engine import TaskStatus

class TaskSequence(Base):
    __tablename__ = "task_sequence"
    id = Column(Integer, primary_key=True, autoincrement=True)

class DBTask(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    status = Column(String, default=TaskStatus.BACKLOG.value)
    position = Column(Integer, default=0)
    duration_days = Column(Integer, default=1)
    planned_start = Column(Date)
    start_date = Column(Date)
    end_date = Column(Date)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    blocked = Column(Boolean, default=False)
    is_critical = Column(Boolean, default=False)
    version = Column(Integer, default=1)

class DBDependency(Base):
    __tablename__ = "dependencies"

    prerequisite_id = Column(String, ForeignKey("tasks.id"), primary_key=True)
    dependent_id = Column(String, ForeignKey("tasks.id"), primary_key=True)

    __table_args__ = (
        UniqueConstraint('prerequisite_id', 'dependent_id', name='uix_1'),
    )

class DBDependencySuggestion(Base):
    __tablename__ = "dependency_suggestions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    prerequisite_id = Column(String, ForeignKey("tasks.id"))
    dependent_id = Column(String, ForeignKey("tasks.id"))
    confidence = Column(String)
    rationale = Column(String)
    status = Column(String, default="pending") # pending, accepted, dismissed
