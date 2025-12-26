from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from backend.app.core.database import get_db
from backend.app.agents.strategy import StrategyAgent
from backend.app.agents.risk import RiskAgent

router = APIRouter(prefix="/managerial", tags=["managerial-intelligence"])


# ==================== SCHEMAS ====================

class GoalCreateRequest(BaseModel):
    text: str
    owner: Optional[str] = None


class AlignProjectRequest(BaseModel):
    project_id: str
    goal_id: str


class AskRequest(BaseModel):
    question: str
    project_id: Optional[str] = None


# ==================== STRATEGY ENDPOINTS ====================

@router.post("/goals")
async def create_goal(
    request: GoalCreateRequest,
    db: Session = Depends(get_db)
):
    """Create structured goal from text using AI."""
    agent = StrategyAgent(db)
    result = agent.create_goal_from_text(request.text, request.owner)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/goals/{goal_id}/alignment")
async def get_goal_alignment(
    goal_id: str,
    db: Session = Depends(get_db)
):
    """Get projects aligned to a goal and identify unaligned projects."""
    agent = StrategyAgent(db)
    result = agent.get_goal_alignment(goal_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/projects/{project_id}/align")
async def align_project_to_goal(
    project_id: str,
    request: AlignProjectRequest,
    db: Session = Depends(get_db)
):
    """Link a project to a strategic goal."""
    agent = StrategyAgent(db)
    result = agent.align_project_to_goal(project_id, request.goal_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/projects/{project_id}/scope-creep")
async def detect_scope_creep(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Detect if project is not aligned to any active goal (scope creep)."""
    agent = StrategyAgent(db)
    result = agent.detect_scope_creep(project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ==================== RISK ENDPOINTS ====================

@router.post("/analyze/risk/{project_id}")
async def analyze_project_risk(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Force a risk assessment run on a project."""
    agent = RiskAgent(db)
    result = agent.assess_project_risk(project_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/risks/{project_id}")
async def get_project_risks(
    project_id: str,
    db: Session = Depends(get_db)
):
    """Get active risks for a project."""
    agent = RiskAgent(db)
    return agent.get_project_risks(project_id)


@router.post("/risks/{risk_id}/mitigate")
async def mitigate_risk(
    risk_id: str,
    resolution_notes: str,
    db: Session = Depends(get_db)
):
    """Mark a risk as mitigated."""
    agent = RiskAgent(db)
    result = agent.mitigate_risk(risk_id, resolution_notes)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ==================== COMMUNICATION ENDPOINTS ====================

@router.get("/standup")
async def get_daily_standup(
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generate daily standup summary from database activity."""
    from datetime import datetime, timedelta
    from backend.app.models import Task, TaskStatus
    from backend.app.agents.communication import CommunicationAgent
    
    # Calculate yesterday and today
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    
    # Build query
    query = db.query(Task)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    if user_id:
        query = query.filter(Task.owner == user_id)
    
    tasks = query.all()
    
    # Categorize tasks
    completed = [
        t.name for t in tasks 
        if t.status == TaskStatus.COMPLETED 
        and t.completed_at 
        and t.completed_at.date() >= yesterday
    ]
    
    planned = [
        t.name for t in tasks 
        if t.status == TaskStatus.IN_PROGRESS 
        or (t.deadline and t.deadline.date() == today and t.status == TaskStatus.NOT_STARTED)
    ]
    
    blockers = [
        f"{t.name} (since {t.updated_at.date()})" for t in tasks 
        if t.status == TaskStatus.BLOCKED
    ]
    
    # Try LLM-generated standup
    agent = CommunicationAgent()
    try:
        result = agent.generate_standup(
            user=user_id or "Team",
            completed=completed,
            planned=planned,
            blockers=blockers
        )
        return {
            "project_id": project_id,
            "user_id": user_id,
            "date": today.isoformat(),
            **result
        }
    except Exception as e:
        # Fallback to simple text format
        return {
            "project_id": project_id,
            "user_id": user_id,
            "date": today.isoformat(),
            "summary": f"✅ Done: {len(completed)} | 🚧 Doing: {len(planned)} | 🚫 Blocked: {len(blockers)}",
            "formatted_message": f"""**Daily Standup - {today}**

✅ **Completed ({len(completed)}):**
{chr(10).join(['- ' + c for c in completed]) or '- No tasks completed yesterday'}

🚧 **In Progress ({len(planned)}):**
{chr(10).join(['- ' + p for p in planned]) or '- No tasks in progress'}

🚫 **Blockers ({len(blockers)}):**
{chr(10).join(['- ' + b for b in blockers]) or '- No blockers'}
""",
            "needs_follow_up": len(blockers) > 0
        }


@router.post("/ask")
async def ask_question(
    request: AskRequest,
    db: Session = Depends(get_db)
):
    """General Q&A endpoint - answer questions about projects."""
    from backend.app.agents.communication import CommunicationAgent
    agent = CommunicationAgent()
    
    # Gather context from DB
    context = {}
    if request.project_id:
        from backend.app.models import Project, Task
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if project:
            context["project"] = project.name
            tasks = db.query(Task).filter(Task.project_id == request.project_id).limit(10).all()
            context["tasks"] = [{"name": t.name, "status": t.status.value} for t in tasks]
    
    # Use existing communication agent
    return agent.answer_stakeholder_query(request.question, context) if hasattr(agent, 'answer_stakeholder_query') else {
        "question": request.question,
        "answer": "Q&A functionality requires LLM configuration"
    }


# ==================== APPROVAL ENDPOINTS (Phase 4: Safety & Governance) ====================

class SubmitActionRequest(BaseModel):
    """Request to submit an action for approval."""
    action_type: str
    action_summary: str
    payload: Dict[str, Any] = {}
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    agent_name: str = "api"


class DecisionRequest(BaseModel):
    """Request to approve or reject an action."""
    decision: str  # "approved" or "rejected"
    reason: Optional[str] = None


@router.get("/approvals/pending")
async def get_pending_approvals(
    db: Session = Depends(get_db)
):
    """
    List all pending approval requests.
    
    Returns approvals sorted by risk score (highest first).
    """
    from backend.app.models import ApprovalRequest, ApprovalStatus
    
    approvals = db.query(ApprovalRequest).filter(
        ApprovalRequest.status == ApprovalStatus.PENDING
    ).order_by(ApprovalRequest.risk_score.desc()).all()
    
    return {
        "count": len(approvals),
        "approvals": [
            {
                "id": a.id,
                "agent_name": a.agent_name,
                "action_type": a.action_type,
                "action_summary": a.action_summary,
                "risk_score": a.risk_score,
                "sensitivity": a.sensitivity.value if a.sensitivity else None,
                "resource_type": a.resource_type,
                "resource_id": a.resource_id,
                "requester_name": a.requester_name,
                "requested_at": a.requested_at.isoformat() if a.requested_at else None,
                "impact_summary": a.impact_summary,
                "is_reversible": a.is_reversible
            }
            for a in approvals
        ]
    }


@router.get("/approvals/count")
async def get_pending_count(
    db: Session = Depends(get_db)
):
    """Get count of pending approvals for notification badge."""
    from backend.app.agents.risk import RiskGateService
    
    risk_gate = RiskGateService(db)
    count = risk_gate.get_pending_count()
    
    return {
        "pending_count": count,
        "has_pending": count > 0
    }


@router.post("/approvals/{approval_id}/decide")
async def decide_approval(
    approval_id: str,
    request: DecisionRequest,
    db: Session = Depends(get_db)
):
    """
    Approve or reject a pending action.
    
    On approval, the action will be executed automatically.
    """
    from backend.app.models import ApprovalRequest, ApprovalStatus
    from backend.app.agents.risk import RiskGateService
    from datetime import datetime
    
    approval = db.query(ApprovalRequest).filter(
        ApprovalRequest.id == approval_id
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Approval already resolved with status: {approval.status.value}"
        )
    
    if request.decision not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'approved' or 'rejected'"
        )
    
    # Update approval status
    approval.status = ApprovalStatus.APPROVED if request.decision == "approved" else ApprovalStatus.REJECTED
    approval.resolved_at = datetime.utcnow()
    approval.resolution_reason = request.reason
    # Note: resolved_by should come from auth context in production
    
    db.commit()
    
    result = {
        "approval_id": approval_id,
        "decision": request.decision,
        "status": approval.status.value
    }
    
    # If approved, execute the action
    if request.decision == "approved":
        risk_gate = RiskGateService(db)
        execution_result = await risk_gate.execute_approved_action(approval_id)
        result["execution"] = execution_result
    
    return result


@router.get("/approvals/{approval_id}")
async def get_approval_details(
    approval_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific approval request."""
    from backend.app.models import ApprovalRequest
    import json
    
    approval = db.query(ApprovalRequest).filter(
        ApprovalRequest.id == approval_id
    ).first()
    
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    # Parse payload JSON
    try:
        payload = json.loads(approval.payload) if approval.payload else {}
    except json.JSONDecodeError:
        payload = {}
    
    return {
        "id": approval.id,
        "agent_name": approval.agent_name,
        "action_type": approval.action_type,
        "action_summary": approval.action_summary,
        "payload": payload,
        "risk_score": approval.risk_score,
        "sensitivity": approval.sensitivity.value if approval.sensitivity else None,
        "resource_type": approval.resource_type,
        "resource_id": approval.resource_id,
        "requester_id": approval.requester_id,
        "requester_name": approval.requester_name,
        "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
        "status": approval.status.value if approval.status else None,
        "resolved_by": approval.resolved_by,
        "resolved_at": approval.resolved_at.isoformat() if approval.resolved_at else None,
        "resolution_reason": approval.resolution_reason,
        "impact_summary": approval.impact_summary,
        "is_reversible": approval.is_reversible
    }


@router.post("/submit-action")
async def submit_action_for_approval(
    request: SubmitActionRequest,
    db: Session = Depends(get_db)
):
    """
    Submit an action for risk assessment and potential approval.
    
    If risk score is below threshold, action proceeds immediately.
    If above threshold, creates pending approval request.
    """
    from backend.app.agents.risk import RiskGateService
    
    risk_gate = RiskGateService(db)
    
    # Assess risk first
    assessment = risk_gate.assess_risk(request.action_type, request.payload)
    
    if not assessment["requires_approval"]:
        # Low risk - could execute immediately
        # For now, just return the assessment
        return {
            "status": "auto_approved",
            "risk_assessment": assessment,
            "message": "Action approved automatically (low risk)"
        }
    
    # High risk - submit for approval
    # Using a placeholder user_id - in production, get from auth
    result = await risk_gate.submit_for_approval(
        user_id="system",  # Would come from auth context
        agent_name=request.agent_name,
        action_type=request.action_type,
        action_summary=request.action_summary,
        payload=request.payload,
        resource_type=request.resource_type,
        resource_id=request.resource_id
    )
    
    return {
        "status": "pending_approval",
        "risk_assessment": assessment,
        **result
    }


@router.post("/assess-risk")
async def assess_action_risk(
    action_type: str,
    payload: Dict[str, Any] = {},
    db: Session = Depends(get_db)
):
    """
    Assess risk for an action without submitting for approval.
    Useful for previewing risk level before committing.
    """
    from backend.app.agents.risk import RiskGateService
    
    risk_gate = RiskGateService(db)
    return risk_gate.assess_risk(action_type, payload)