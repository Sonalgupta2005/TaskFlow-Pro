from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey, UniqueConstraint, DateTime, ForeignKeyConstraint
from sqlalchemy.orm import relationship
import datetime
from .database import Base
from .engine import TaskStatus

class DBUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class TaskSequence(Base):
    __tablename__ = "task_sequence"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    last_value = Column(Integer, default=0)

class DBTask(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
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

    prerequisite_id = Column(String, primary_key=True)
    dependent_id = Column(String, primary_key=True)
    user_id = Column(Integer, primary_key=True)

    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'prerequisite_id'], ['tasks.user_id', 'tasks.id']),
        ForeignKeyConstraint(['user_id', 'dependent_id'], ['tasks.user_id', 'tasks.id']),
        UniqueConstraint('prerequisite_id', 'dependent_id', 'user_id', name='uix_1'),
    )

class DBDependencySuggestion(Base):
    __tablename__ = "dependency_suggestions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    prerequisite_id = Column(String)
    dependent_id = Column(String)
    confidence = Column(String)
    rationale = Column(String)
    status = Column(String, default="pending") # pending, accepted, dismissed

    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'prerequisite_id'], ['tasks.user_id', 'tasks.id']),
        ForeignKeyConstraint(['user_id', 'dependent_id'], ['tasks.user_id', 'tasks.id']),
    )
