from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from fastapi.middleware.cors import CORSMiddleware

from core import models, schemas, engine, ai_pipeline
from core.database import SessionLocal, engine as db_engine, get_db

models.Base.metadata.create_all(bind=db_engine)

app = FastAPI(title="TaskFlow Pro API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _recompute_graph(db: Session):
    db_tasks = db.query(models.DBTask).all()
    db_edges = db.query(models.DBDependency).all()
    
    tasks_dict = {}
    for dt in db_tasks:
        tasks_dict[dt.id] = engine.Task(
            id=dt.id,
            status=engine.TaskStatus(dt.status),
            duration_days=dt.duration_days,
            planned_start=dt.planned_start,
            start_date=dt.start_date or dt.planned_start,
            end_date=dt.end_date or dt.planned_start,
            blocked=dt.blocked,
            is_critical=dt.is_critical
        )
        
    edges_list = [(e.prerequisite_id, e.dependent_id) for e in db_edges]
    
    # This modifies tasks_dict in place
    engine.compute_schedule(tasks_dict, edges_list)
    
    # Save back to DB
    for dt in db_tasks:
        t = tasks_dict[dt.id]
        dt.start_date = t.start_date
        dt.end_date = t.end_date
        dt.blocked = t.blocked
        dt.is_critical = t.is_critical
        
    db.commit()

@app.get("/tasks", response_model=List[schemas.Task])
def read_tasks(db: Session = Depends(get_db)):
    tasks = db.query(models.DBTask).order_by(models.DBTask.position).all()
    return tasks

@app.post("/tasks", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = models.DBTask(**task.model_dump(), start_date=task.planned_start, end_date=task.planned_start)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    _recompute_graph(db)
    db.refresh(db_task)
    return db_task

@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: str, task: schemas.TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(models.DBTask).filter(models.DBTask.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    update_data = task.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "status" and value:
            setattr(db_task, key, value.value)
        else:
            setattr(db_task, key, value)
            
    db_task.version += 1
    db.commit()
    _recompute_graph(db)
    db.refresh(db_task)
    return db_task

@app.get("/dependencies", response_model=List[schemas.Dependency])
def read_dependencies(db: Session = Depends(get_db)):
    return db.query(models.DBDependency).all()

@app.post("/dependencies", response_model=schemas.Dependency)
def create_dependency(dep: schemas.Dependency, db: Session = Depends(get_db)):
    db_edges = db.query(models.DBDependency).all()
    edges_list = [(e.prerequisite_id, e.dependent_id) for e in db_edges]
    
    try:
        engine.check_cycles(edges_list, (dep.prerequisite_id, dep.dependent_id))
    except engine.CycleDetectedError as e:
        raise HTTPException(status_code=409, detail=str(e))
        
    db_dep = models.DBDependency(prerequisite_id=dep.prerequisite_id, dependent_id=dep.dependent_id)
    db.add(db_dep)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Dependency already exists or invalid task IDs")
        
    _recompute_graph(db)
    return db_dep

@app.delete("/dependencies")
def delete_dependency(prerequisite_id: str, dependent_id: str, db: Session = Depends(get_db)):
    db_dep = db.query(models.DBDependency).filter_by(prerequisite_id=prerequisite_id, dependent_id=dependent_id).first()
    if not db_dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
        
    db.delete(db_dep)
    db.commit()
    _recompute_graph(db)
    return {"ok": True}

@app.post("/suggestions", response_model=List[schemas.DependencySuggestion])
def generate_suggestions(db: Session = Depends(get_db)):
    db_tasks = db.query(models.DBTask).all()
    tasks = [schemas.Task(
        id=t.id, title=t.title, description=t.description, 
        status=engine.TaskStatus(t.status), position=t.position, 
        duration_days=t.duration_days, planned_start=t.planned_start, 
        start_date=t.start_date or t.planned_start, end_date=t.end_date or t.planned_start, 
        blocked=t.blocked, is_critical=t.is_critical, version=t.version
    ) for t in db_tasks]
    
    db_edges = db.query(models.DBDependency).all()
    edges = [(e.prerequisite_id, e.dependent_id) for e in db_edges]
    
    suggestions = ai_pipeline.get_suggestions(tasks, edges)
    
    # Save to DB
    result = []
    for s in suggestions:
        existing = db.query(models.DBDependencySuggestion).filter_by(
            prerequisite_id=s['prerequisite_id'], dependent_id=s['dependent_id']
        ).first() # wait, schema has suggested_prereq_id and task_id
        
        existing = db.query(models.DBDependencySuggestion).filter_by(
            suggested_prereq_id=s['prerequisite_id'], task_id=s['dependent_id']
        ).first()
        
        if not existing:
            new_sugg = models.DBDependencySuggestion(
                task_id=s['dependent_id'],
                suggested_prereq_id=s['prerequisite_id'],
                confidence=s['confidence'],
                rationale=s['rationale'],
                status="pending"
            )
            db.add(new_sugg)
            db.commit()
            db.refresh(new_sugg)
            result.append(new_sugg)
        else:
            if existing.status == "pending":
                result.append(existing)
                
    # Return all pending suggestions
    all_pending = db.query(models.DBDependencySuggestion).filter_by(status="pending").all()
    return all_pending

@app.post("/suggestions/{sugg_id}/accept")
def accept_suggestion(sugg_id: int, db: Session = Depends(get_db)):
    sugg = db.query(models.DBDependencySuggestion).filter_by(id=sugg_id).first()
    if not sugg:
        raise HTTPException(404, "Suggestion not found")
        
    sugg.status = "accepted"
    db.commit()
    
    # Create the actual dependency
    try:
        dep = schemas.Dependency(prerequisite_id=sugg.suggested_prereq_id, dependent_id=sugg.task_id)
        return create_dependency(dep, db)
    except Exception as e:
        raise e

@app.post("/suggestions/{sugg_id}/dismiss")
def dismiss_suggestion(sugg_id: int, db: Session = Depends(get_db)):
    sugg = db.query(models.DBDependencySuggestion).filter_by(id=sugg_id).first()
    if sugg:
        sugg.status = "dismissed"
        db.commit()
    return {"ok": True}

