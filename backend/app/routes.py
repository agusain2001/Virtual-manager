from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from backend.app.core.database import get_db
from backend.app.task_service import TaskService
from backend.app.models import TaskStatus, TaskPriority, ProjectHealth

router = APIRouter(prefix="/api/v1", tags=["VAM"])

# Pydantic Models for Request/Response
class TaskCreate(BaseModel):
    name: str
    project_id: str
    owner: str
    description: Optional[str] = None
    priority: str = "medium"
    deadline: Optional[datetime] = None

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[datetime] = None

class ProjectCreate(BaseModel):
    name: str
    owner: str
    objective: Optional[str] = None
    priority: str = "medium"
    end_date: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: str
    name: str
    project_id: str
    owner: str
    priority: str
    status: str
    deadline: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProjectResponse(BaseModel):
    id: str
    name: str
    owner: str
    objective: Optional[str]
    priority: str
    health: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class AgentActivityResponse(BaseModel):
    id: str
    timestamp: datetime
    agent_name: str
    activity_type: str
    message: str
    
    class Config:
        from_attributes = True

# Project Endpoints
@router.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    from backend.app.models import Project
    import uuid
    
    project_id = str(uuid.uuid4())
    db_project = Project(
        id=project_id,
        name=project.name,
        owner=project.owner,
        objective=project.objective,
        priority=TaskPriority[project.priority.upper()],
        end_date=project.end_date
    )
    
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    return db_project

@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(db: Session = Depends(get_db)):
    """List all projects"""
    from backend.app.models import Project
    
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return projects

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get project by ID"""
    from backend.app.models import Project
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project

# Task Endpoints
@router.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task"""
    service = TaskService(db)
    
    try:
        priority = TaskPriority[task.priority.upper()]
        db_task = service.create_task(
            name=task.name,
            project_id=task.project_id,
            owner=task.owner,
            description=task.description,
            priority=priority,
            deadline=task.deadline,
            trigger="user"
        )
        return db_task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List tasks with optional filters"""
    from backend.app.models import Task
    
    query = db.query(Task)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    if status:
        try:
            status_enum = TaskStatus[status.upper()]
            query = query.filter(Task.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail="Invalid status")
    
    tasks = query.order_by(Task.created_at.desc()).all()
    return tasks

@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get task by ID"""
    from backend.app.models import Task
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db)
):
    """Update a task"""
    from backend.app.models import Task
    
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    service = TaskService(db)
    
    if task_update.name:
        task.name = task_update.name
    
    if task_update.description:
        task.description = task_update.description
    
    if task_update.owner:
        task.owner = task_update.owner
    
    if task_update.priority:
        task.priority = TaskPriority[task_update.priority.upper()]
    
    if task_update.deadline:
        task.deadline = task_update.deadline
    
    if task_update.status:
        status_enum = TaskStatus[task_update.status.upper()]
        service.update_task_status(task_id, status_enum, trigger="user")
    else:
        task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
    
    return task

@router.post("/tasks/{task_id}/dependencies/{depends_on_id}")
async def add_task_dependency(
    task_id: str,
    depends_on_id: str,
    db: Session = Depends(get_db)
):
    """Add a dependency between tasks"""
    service = TaskService(db)
    
    try:
        dependency = service.add_dependency(task_id, depends_on_id)
        return {"message": "Dependency added successfully", "id": dependency.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tasks/overdue", response_model=List[TaskResponse])
async def get_overdue_tasks(db: Session = Depends(get_db)):
    """Get all overdue tasks"""
    service = TaskService(db)
    tasks = service.get_overdue_tasks()
    return tasks

@router.get("/tasks/blocked", response_model=List[TaskResponse])
async def get_blocked_tasks(db: Session = Depends(get_db)):
    """Get all blocked tasks"""
    service = TaskService(db)
    tasks = service.get_blocked_tasks()
    return tasks

@router.get("/projects/{project_id}/tasks/prioritized", response_model=List[TaskResponse])
async def get_prioritized_tasks(project_id: str, db: Session = Depends(get_db)):
    """Get prioritized task list for a project"""
    service = TaskService(db)
    tasks = service.prioritize_tasks(project_id)
    return tasks

# Activity Feed
@router.get("/activities", response_model=List[AgentActivityResponse])
async def get_activities(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent agent activities"""
    from backend.app.models import AgentActivity
    
    activities = db.query(AgentActivity).order_by(
        AgentActivity.timestamp.desc()
    ).limit(limit).all()
    
    return activities

# Dashboard Stats
@router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    from backend.app.models import Task, Project, TaskStatus
    
    total_projects = db.query(Project).count()
    
    total_tasks = db.query(Task).count()
    
    pending_tasks = db.query(Task).filter(
        Task.status.in_([TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS])
    ).count()
    
    blocked_tasks = db.query(Task).filter(
        Task.status == TaskStatus.BLOCKED
    ).count()
    
    completed_tasks = db.query(Task).filter(
        Task.status == TaskStatus.COMPLETED
    ).count()
    
    service = TaskService(db)
    overdue_tasks = len(service.get_overdue_tasks())
    
    return {
        "total_projects": total_projects,
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "blocked_tasks": blocked_tasks,
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "completion_rate": round(completed_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0
    }