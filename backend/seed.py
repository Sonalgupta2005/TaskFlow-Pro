import os
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import SQLALCHEMY_DATABASE_URL
from core import models
from core.engine import TaskStatus

def seed_data():
    if os.path.exists("./taskflow.db"):
        os.remove("./taskflow.db")
        
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    base_date = date.today()
    
    tasks = [
        # Diamond Path
        models.DBTask(id="TASK-1", title="Define API Contract", description="Define the OpenAPI spec for the backend", status=TaskStatus.DONE.value, duration_days=2, planned_start=base_date - timedelta(days=5), position=0),
        models.DBTask(id="TASK-2", title="Implement Backend API", description="Build the FastAPI backend endpoints", status=TaskStatus.IN_PROGRESS.value, duration_days=3, planned_start=base_date, position=1),
        models.DBTask(id="TASK-3", title="Implement Frontend Client", description="Build the React query hooks and services", status=TaskStatus.BACKLOG.value, duration_days=3, planned_start=base_date, position=2),
        models.DBTask(id="TASK-4", title="Integration Testing", description="End-to-end tests for the new feature", status=TaskStatus.BACKLOG.value, duration_days=2, planned_start=base_date, position=3),
        
        # Unaffected Branch
        models.DBTask(id="TASK-5", title="Design Logo", description="Create a vector logo for the app", status=TaskStatus.DONE.value, duration_days=1, planned_start=base_date - timedelta(days=2), position=4),
        models.DBTask(id="TASK-6", title="Update Marketing Website", description="Update the main site with the new logo", status=TaskStatus.BACKLOG.value, duration_days=2, planned_start=base_date, position=5),
        
        # Additional Tasks
        models.DBTask(id="TASK-7", title="Deploy to Staging", description="Deploy the application to the staging environment", status=TaskStatus.BACKLOG.value, duration_days=1, planned_start=base_date, position=6),
        models.DBTask(id="TASK-8", title="User Acceptance Testing", description="Get feedback from stakeholders", status=TaskStatus.BACKLOG.value, duration_days=4, planned_start=base_date, position=7),
    ]
    
    db.add_all(tasks)
    db.commit()
    
    # Dependencies
    dependencies = [
        # Diamond: 1 -> 2, 1 -> 3, 2 -> 4, 3 -> 4
        models.DBDependency(prerequisite_id="TASK-1", dependent_id="TASK-2"),
        models.DBDependency(prerequisite_id="TASK-1", dependent_id="TASK-3"),
        models.DBDependency(prerequisite_id="TASK-2", dependent_id="TASK-4"),
        models.DBDependency(prerequisite_id="TASK-3", dependent_id="TASK-4"),
        
        # Branch: 5 -> 6
        models.DBDependency(prerequisite_id="TASK-5", dependent_id="TASK-6"),
        
        # Further down: 4 -> 7, 7 -> 8
        models.DBDependency(prerequisite_id="TASK-4", dependent_id="TASK-7"),
        models.DBDependency(prerequisite_id="TASK-7", dependent_id="TASK-8"),
    ]
    
    db.add_all(dependencies)
    db.commit()
    
    # Recompute to set initial dates
    from main import _recompute_graph
    _recompute_graph(db)
    
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed_data()
