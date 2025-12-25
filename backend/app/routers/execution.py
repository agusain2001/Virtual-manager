from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from backend.app.core.database import get_db
from backend.app.monitoring_service import ExecutionMonitor

router = APIRouter(prefix="/execution", tags=["execution-monitoring"])


# ==================== SCHEMAS ====================

class DailyUpdateRequest(BaseModel):
    task_id: str
    user: str
    progress_notes: str
    hours_worked: int = 0
    blockers: Optional[str] = None


class EscalateRequest(BaseModel):
    reason: str
    escalate_to: str = "project_owner"
    suggested_action: Optional[str] = None


class ResolveEscalationRequest(BaseModel):
    resolution_notes: str


class BlockerInfo(BaseModel):
    id: str
    name: str
    owner: str
    project_id: str
    priority: str
    hours_blocked: float
    blocked_since: str
    blocking_tasks: List[dict]
    needs_escalation: bool


class EscalationInfo(BaseModel):
    id: str
    task_id: Optional[str]
    project_id: Optional[str]
    reason: str
    escalated_to: str
    type: Optional[str]
    status: str
    suggested_action: Optional[str]
    created_at: str
    acknowledged_at: Optional[str]


# ==================== ENDPOINTS ====================

@router.get("/daily-summary")
async def get_daily_summary(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get daily summary of all active tasks."""
    monitor = ExecutionMonitor(db)
    return monitor.collect_daily_summary(project_id)


@router.get("/projects/{project_id}/health")
async def get_project_health(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Get project health based on task status.
    
    Health calculation:
    - DELAYED: >20% tasks overdue
    - AT_RISK: >0 tasks overdue OR >50% tasks blocked
    - ON_TRACK: Everything else
    """
    from backend.app.models import Task, TaskStatus
    
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    
    if not tasks:
        raise HTTPException(status_code=404, detail="Project not found or has no tasks")
    
    total = len(tasks)
    completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    blocked = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)
    cancelled = sum(1 for t in tasks if t.status == TaskStatus.CANCELLED)
    
    now = datetime.utcnow()
    overdue = sum(
        1 for t in tasks 
        if t.deadline and t.deadline < now and t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
    )
    
    active_tasks = total - cancelled
    overdue_percentage = (overdue / active_tasks * 100) if active_tasks > 0 else 0
    blocked_percentage = (blocked / active_tasks * 100) if active_tasks > 0 else 0
    completion_percentage = (completed / active_tasks * 100) if active_tasks > 0 else 0
    
    # Determine health status
    if overdue_percentage > 20:
        status = "DELAYED"
    elif overdue > 0 or blocked_percentage > 50:
        status = "AT_RISK"
    else:
        status = "ON_TRACK"
    
    return {
        "project_id": project_id,
        "status": status,
        "completion_percentage": round(completion_percentage, 1),
        "total_tasks": total,
        "completed_tasks": completed,
        "blocked_tasks": blocked,
        "overdue_tasks": overdue,
        "cancelled_tasks": cancelled
    }


@router.get("/weekly-report")
async def get_weekly_report(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generate weekly progress report."""
    monitor = ExecutionMonitor(db)
    return monitor.generate_weekly_summary(project_id)


@router.get("/missing-updates")
async def get_missing_updates(
    threshold_hours: int = 48,
    db: Session = Depends(get_db)
):
    """Find tasks with no recent updates."""
    monitor = ExecutionMonitor(db)
    return monitor.detect_missing_updates(threshold_hours)


@router.get("/blockers", response_model=List[BlockerInfo])
async def get_blockers(db: Session = Depends(get_db)):
    """Detect all blocked tasks with analysis."""
    monitor = ExecutionMonitor(db)
    return monitor.detect_blockers()


@router.post("/tasks/{task_id}/update")
async def record_daily_update(
    task_id: str,
    update: DailyUpdateRequest,
    db: Session = Depends(get_db)
):
    """Record a daily progress update for a task."""
    monitor = ExecutionMonitor(db)
    try:
        result = monitor.record_daily_update(
            task_id=task_id,
            user=update.user,
            progress_notes=update.progress_notes,
            hours_worked=update.hours_worked,
            blockers=update.blockers
        )
        return {"message": "Update recorded", "update_id": result.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tasks/{task_id}/escalate", response_model=EscalationInfo)
async def escalate_task(
    task_id: str,
    request: EscalateRequest,
    db: Session = Depends(get_db)
):
    """Escalate a task."""
    monitor = ExecutionMonitor(db)
    try:
        escalation = monitor.escalate_task(
            task_id=task_id,
            reason=request.reason,
            escalate_to=request.escalate_to,
            suggested_action=request.suggested_action
        )
        return {
            "id": escalation.id,
            "task_id": escalation.task_id,
            "project_id": escalation.project_id,
            "reason": escalation.reason,
            "escalated_to": escalation.escalated_to,
            "type": escalation.escalation_type,
            "status": escalation.status.value,
            "suggested_action": escalation.suggested_action,
            "created_at": escalation.created_at.isoformat(),
            "acknowledged_at": None
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/escalations", response_model=List[EscalationInfo])
async def get_open_escalations(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all open escalations."""
    monitor = ExecutionMonitor(db)
    return monitor.get_open_escalations(project_id)


@router.post("/escalations/{escalation_id}/acknowledge")
async def acknowledge_escalation(
    escalation_id: str,
    db: Session = Depends(get_db)
):
    """Acknowledge an escalation."""
    monitor = ExecutionMonitor(db)
    try:
        escalation = monitor.acknowledge_escalation(escalation_id)
        return {"message": "Escalation acknowledged", "id": escalation.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: str,
    request: ResolveEscalationRequest,
    db: Session = Depends(get_db)
):
    """Resolve an escalation."""
    monitor = ExecutionMonitor(db)
    try:
        escalation = monitor.resolve_escalation(escalation_id, request.resolution_notes)
        return {"message": "Escalation resolved", "id": escalation.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
