from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base
from .engine import TaskStatus

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
    task_id = Column(String, ForeignKey("tasks.id"))
    suggested_prereq_id = Column(String, ForeignKey("tasks.id"))
    confidence = Column(String)
    rationale = Column(String)
    status = Column(String, default="pending") # pending, accepted, dismissed
