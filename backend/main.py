from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import JWTError, jwt

from core import models, schemas, engine, ai_pipeline, auth
from core.database import SessionLocal, engine as db_engine, get_db
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
from fastapi.security import OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.DBUser).filter(models.DBUser.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@app.post("/auth/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.DBUser).filter(models.DBUser.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.DBUser(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/auth/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.DBUser).filter(models.DBUser.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

def _recompute_graph(db: Session, user_id: int):
    db_tasks = db.query(models.DBTask).filter(models.DBTask.user_id == user_id).all()
    db_edges = db.query(models.DBDependency).filter(models.DBDependency.user_id == user_id).all()
    
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
            actual_start_date=dt.actual_start_date,
            actual_end_date=dt.actual_end_date,
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
def read_tasks(db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    tasks = db.query(models.DBTask).filter(models.DBTask.user_id == current_user.id).order_by(
        models.DBTask.start_date,
        models.DBTask.end_date,
        models.DBTask.created_at
    ).all()
    return tasks

@app.post("/tasks", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    seq = db.query(models.TaskSequence).filter(models.TaskSequence.user_id == current_user.id).first()
    if not seq:
        seq = models.TaskSequence(user_id=current_user.id, last_value=0)
        db.add(seq)
    
    seq.last_value += 1
    db.commit()
    db.refresh(seq)
    
    new_id = f"TASK-{seq.last_value}"
    db_task = models.DBTask(id=new_id, user_id=current_user.id, **task.model_dump(), start_date=task.planned_start, end_date=task.planned_start)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    _recompute_graph(db, current_user.id)
    db.refresh(db_task)
    return db_task

@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: str, task: schemas.TaskUpdate, db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    db_task = db.query(models.DBTask).filter(models.DBTask.id == task_id, models.DBTask.user_id == current_user.id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    old_status = db_task.status
    
    update_data = task.model_dump(exclude_unset=True)
    
    # If core task details change, invalidate any pending suggestions involving this task
    if "title" in update_data or "description" in update_data:
        db.query(models.DBDependencySuggestion).filter(
            (models.DBDependencySuggestion.prerequisite_id == task_id) | 
            (models.DBDependencySuggestion.dependent_id == task_id),
            models.DBDependencySuggestion.user_id == current_user.id,
            models.DBDependencySuggestion.status == "pending"
        ).delete()
        
    for key, value in update_data.items():
        if key == "status" and value:
            new_status = value.value
            
            if old_status in ["in_progress", "review", "done"] and new_status == "backlog":
                raise HTTPException(status_code=400, detail="Cannot move an active or completed task back to backlog.")
                
            setattr(db_task, key, new_status)
            
            from datetime import date
            today = date.today()
            
            if new_status in ["in_progress", "review", "done"] and not db_task.actual_start_date:
                db_task.actual_start_date = today
                
            if new_status == "done":
                db_task.actual_end_date = today
                
            if old_status == "done" and new_status in ["in_progress", "review"]:
                db_task.actual_end_date = None
        else:
            setattr(db_task, key, value)
            
    db_task.version += 1
    db.commit()
    _recompute_graph(db, current_user.id)
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    db_task = db.query(models.DBTask).filter(models.DBTask.id == task_id, models.DBTask.user_id == current_user.id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    db.query(models.DBDependency).filter(
        (models.DBDependency.prerequisite_id == task_id) | 
        (models.DBDependency.dependent_id == task_id),
        models.DBDependency.user_id == current_user.id
    ).delete()
    
    db.query(models.DBDependencySuggestion).filter(
        (models.DBDependencySuggestion.prerequisite_id == task_id) | 
        (models.DBDependencySuggestion.dependent_id == task_id),
        models.DBDependencySuggestion.user_id == current_user.id,
        models.DBDependencySuggestion.status == "pending"
    ).delete()
    
    db.delete(db_task)
    db.commit()
    
    _recompute_graph(db, current_user.id)
    return {"ok": True}

@app.get("/dependencies", response_model=List[schemas.Dependency])
def read_dependencies(db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    return db.query(models.DBDependency).filter(models.DBDependency.user_id == current_user.id).all()

@app.post("/dependencies", response_model=schemas.Dependency)
def create_dependency(dep: schemas.Dependency, db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    prereq = db.query(models.DBTask).filter(models.DBTask.id == dep.prerequisite_id, models.DBTask.user_id == current_user.id).first()
    dependent = db.query(models.DBTask).filter(models.DBTask.id == dep.dependent_id, models.DBTask.user_id == current_user.id).first()
    
    if not prereq or not dependent:
        raise HTTPException(status_code=404, detail="One or both tasks not found")
        

    db_edges = db.query(models.DBDependency).filter(models.DBDependency.user_id == current_user.id).all()
    edges_list = [(e.prerequisite_id, e.dependent_id) for e in db_edges]
    
    try:
        engine.check_cycles(edges_list, (dep.prerequisite_id, dep.dependent_id))
    except engine.CycleDetectedError as e:
        raise HTTPException(status_code=409, detail=str(e))
        
    db_dep = models.DBDependency(prerequisite_id=dep.prerequisite_id, dependent_id=dep.dependent_id, user_id=current_user.id)
    db.add(db_dep)
    
    db.query(models.DBDependencySuggestion).filter_by(
        prerequisite_id=dep.prerequisite_id, 
        dependent_id=dep.dependent_id, 
        user_id=current_user.id,
        status="pending"
    ).delete()
    
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Dependency already exists or invalid task IDs")
        
    _recompute_graph(db, current_user.id)
    return db_dep

@app.delete("/dependencies")
def delete_dependency(prerequisite_id: str, dependent_id: str, db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    db_dep = db.query(models.DBDependency).filter_by(prerequisite_id=prerequisite_id, dependent_id=dependent_id, user_id=current_user.id).first()
    if not db_dep:
        raise HTTPException(status_code=404, detail="Dependency not found")
        
    db.delete(db_dep)
    db.commit()
    _recompute_graph(db, current_user.id)
    return {"ok": True}

@app.post("/suggestions", response_model=List[schemas.DependencySuggestion])
def generate_suggestions(db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    db_tasks = db.query(models.DBTask).filter(models.DBTask.user_id == current_user.id).all()
    tasks = [schemas.Task(
        id=t.id, title=t.title, description=t.description, 
        status=engine.TaskStatus(t.status), position=t.position, 
        duration_days=t.duration_days, planned_start=t.planned_start, 
        start_date=t.start_date or t.planned_start, end_date=t.end_date or t.planned_start, 
        blocked=t.blocked, is_critical=t.is_critical, version=t.version, created_at=t.created_at
    ) for t in db_tasks]
    
    db_edges = db.query(models.DBDependency).filter(models.DBDependency.user_id == current_user.id).all()
    edges = [(e.prerequisite_id, e.dependent_id) for e in db_edges]
    
    suggestions = ai_pipeline.get_suggestions(tasks, edges)
    
    # Save to DB
    result = []
    for s in suggestions:
        existing = db.query(models.DBDependencySuggestion).filter_by(
            prerequisite_id=s['prerequisite_id'], dependent_id=s['dependent_id'], user_id=current_user.id
        ).first()
        
        if not existing:
            new_sugg = models.DBDependencySuggestion(
                user_id=current_user.id,
                dependent_id=s['dependent_id'],
                prerequisite_id=s['prerequisite_id'],
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
                
    # Return all pending suggestions, ensuring uniqueness and validity
    all_pending = db.query(models.DBDependencySuggestion).filter_by(status="pending", user_id=current_user.id).all()
    task_ids = {t.id for t in db_tasks}
    
    seen_pairs = set()
    distinct_pending = []
    for s in all_pending:
        pair = (s.prerequisite_id, s.dependent_id)
        
        if s.prerequisite_id not in task_ids or s.dependent_id not in task_ids:
            db.delete(s)
            continue
            
        if s.prerequisite_id == s.dependent_id:
            db.delete(s)
            continue
            
        if pair in edges:
            db.delete(s)
            continue
            
        try:
            engine.check_cycles(edges, pair)
        except engine.CycleDetectedError:
            db.delete(s)
            continue
            
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            distinct_pending.append(s)
        else:
            db.delete(s)
            
    db.commit()
    return distinct_pending

@app.post("/suggestions/{sugg_id}/accept")
def accept_suggestion(sugg_id: int, db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    sugg = db.query(models.DBDependencySuggestion).filter_by(id=sugg_id, user_id=current_user.id).first()
    if not sugg:
        raise HTTPException(404, "Suggestion not found")
        
    sugg.status = "accepted"
    db.commit()
    
    # Create the actual dependency
    try:
        dep = schemas.Dependency(prerequisite_id=sugg.prerequisite_id, dependent_id=sugg.dependent_id)
        return create_dependency(dep, db, current_user)
    except Exception as e:
        raise e

@app.post("/suggestions/{sugg_id}/dismiss")
def dismiss_suggestion(sugg_id: int, db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    sugg = db.query(models.DBDependencySuggestion).filter_by(id=sugg_id, user_id=current_user.id).first()
    if sugg:
        sugg.status = "dismissed"
        db.commit()
    return {"ok": True}

class TaskDraft(BaseModel):
    title: str
    description: str
    id: str

@app.post("/auto-suggest-draft", response_model=List[schemas.DependencySuggestion])
def auto_suggest_draft(draft: TaskDraft, db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    db_tasks = db.query(models.DBTask).filter(models.DBTask.user_id == current_user.id).all()
    tasks = [schemas.Task(
        id=t.id, title=t.title, description=t.description, 
        status=engine.TaskStatus(t.status), position=t.position, 
        duration_days=t.duration_days, planned_start=t.planned_start, 
        start_date=t.start_date or t.planned_start, end_date=t.end_date or t.planned_start, 
        blocked=t.blocked, is_critical=t.is_critical, version=t.version, created_at=t.created_at
    ) for t in db_tasks]
    
    suggestions = ai_pipeline.get_suggestions_for_draft(draft.title, draft.description, draft.id, tasks)
    
    db_edges = db.query(models.DBDependency).filter(models.DBDependency.user_id == current_user.id).all()
    edges = [(e.prerequisite_id, e.dependent_id) for e in db_edges]
    task_ids = {t.id for t in db_tasks}
    task_ids.add(draft.id)
    
    # Return mock DependencySuggestion objects (not saved to DB)
    result = []
    seen_pairs = set()
    for i, s in enumerate(suggestions):
        p = s.get('prerequisite_id')
        d = s.get('dependent_id')
        
        if not p or not d or p not in task_ids or d not in task_ids:
            continue
            
        if p == d:
            continue
            
        pair = (p, d)
        if pair in edges or pair in seen_pairs:
            continue
            
        try:
            engine.check_cycles(edges, pair)
        except engine.CycleDetectedError:
            continue
            
        seen_pairs.add(pair)
        edges.append(pair)
        
        result.append(schemas.DependencySuggestion(
            id=-i-1, # negative id for draft suggestions
            prerequisite_id=p,
            dependent_id=d,
            confidence=s.get('confidence', 'medium'),
            rationale=s.get('rationale', ''),
            status="pending"
        ))
    return result

from datetime import date, timedelta
@app.post("/seed")
def seed_data_for_user(db: Session = Depends(get_db), current_user: models.DBUser = Depends(get_current_user)):
    # Clear existing data for user
    db.query(models.DBDependencySuggestion).filter(models.DBDependencySuggestion.user_id == current_user.id).delete()
    db.query(models.DBDependency).filter(models.DBDependency.user_id == current_user.id).delete()
    db.query(models.DBTask).filter(models.DBTask.user_id == current_user.id).delete()
    
    seq = db.query(models.TaskSequence).filter(models.TaskSequence.user_id == current_user.id).first()
    if not seq:
        seq = models.TaskSequence(user_id=current_user.id, last_value=8)
        db.add(seq)
    else:
        seq.last_value = 8
    
    db.commit()

    base_date = date.today()
    
    tasks = [
        models.DBTask(id="TASK-1", user_id=current_user.id, title="Define API Contract", description="Define the OpenAPI spec for the backend", status=engine.TaskStatus.DONE.value, duration_days=2, planned_start=base_date - timedelta(days=5), position=0),
        models.DBTask(id="TASK-2", user_id=current_user.id, title="Implement Backend API", description="Build the FastAPI backend endpoints", status=engine.TaskStatus.IN_PROGRESS.value, duration_days=3, planned_start=base_date, position=1),
        models.DBTask(id="TASK-3", user_id=current_user.id, title="Implement Frontend Client", description="Build the React query hooks and services", status=engine.TaskStatus.BACKLOG.value, duration_days=3, planned_start=base_date, position=2),
        models.DBTask(id="TASK-4", user_id=current_user.id, title="Integration Testing", description="End-to-end tests for the new feature", status=engine.TaskStatus.BACKLOG.value, duration_days=2, planned_start=base_date, position=3),
        models.DBTask(id="TASK-5", user_id=current_user.id, title="Design Logo", description="Create a vector logo for the app", status=engine.TaskStatus.DONE.value, duration_days=1, planned_start=base_date - timedelta(days=2), position=4),
        models.DBTask(id="TASK-6", user_id=current_user.id, title="Update Marketing Website", description="Update the main site with the new logo", status=engine.TaskStatus.BACKLOG.value, duration_days=2, planned_start=base_date, position=5),
        models.DBTask(id="TASK-7", user_id=current_user.id, title="Deploy to Staging", description="Deploy the application to the staging environment", status=engine.TaskStatus.BACKLOG.value, duration_days=1, planned_start=base_date, position=6),
        models.DBTask(id="TASK-8", user_id=current_user.id, title="User Acceptance Testing", description="Get feedback from stakeholders", status=engine.TaskStatus.BACKLOG.value, duration_days=4, planned_start=base_date, position=7),
    ]
    
    db.add_all(tasks)
    db.commit()
    
    dependencies = [
        models.DBDependency(prerequisite_id="TASK-1", dependent_id="TASK-2", user_id=current_user.id),
        models.DBDependency(prerequisite_id="TASK-1", dependent_id="TASK-3", user_id=current_user.id),
        models.DBDependency(prerequisite_id="TASK-2", dependent_id="TASK-4", user_id=current_user.id),
        models.DBDependency(prerequisite_id="TASK-3", dependent_id="TASK-4", user_id=current_user.id),
        models.DBDependency(prerequisite_id="TASK-5", dependent_id="TASK-6", user_id=current_user.id),
        models.DBDependency(prerequisite_id="TASK-4", dependent_id="TASK-7", user_id=current_user.id),
        models.DBDependency(prerequisite_id="TASK-7", dependent_id="TASK-8", user_id=current_user.id),
    ]
    
    db.add_all(dependencies)
    db.commit()
    
    _recompute_graph(db, current_user.id)
    
    return {"ok": True}
