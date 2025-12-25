"""
People Operations API Routes.

Provides REST API endpoints for:
- Employee profile management
- Skill matrix tracking
- Leave management with approval workflow
- Meeting scheduling and calendar management
- Workload balance and burnout detection
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.agents.people_ops import PeopleOpsAgent


router = APIRouter(prefix="/api/v1/people", tags=["People & Operations"])


# ==================== PYDANTIC SCHEMAS ====================

class EmployeeCreate(BaseModel):
    name: str
    email: str
    role: str
    department: Optional[str] = None
    timezone: str = "UTC"
    working_hours_start: str = "09:00"
    working_hours_end: str = "17:00"
    leave_balance: int = 20


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    timezone: Optional[str] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    is_active: Optional[bool] = None


class SkillUpdate(BaseModel):
    name: str
    proficiency: str = "beginner"  # beginner, intermediate, expert
    years_experience: int = 0
    is_primary: bool = False


class SkillsUpdateRequest(BaseModel):
    skills: List[SkillUpdate]


class SkillGapRequest(BaseModel):
    required_skills: List[str]


class LeaveRequestCreate(BaseModel):
    employee_id: str
    start_date: datetime
    end_date: datetime
    leave_type: str  # vacation, sick, personal, emergency
    reason: Optional[str] = None


class LeaveApproval(BaseModel):
    reviewed_by: str
    rationale: str
    coverage_plan: Optional[str] = None


class LeaveRejection(BaseModel):
    reviewed_by: str
    rationale: str
    suggested_alternative: Optional[str] = None


class MeetingCreate(BaseModel):
    title: str
    organizer: str
    participant_ids: List[str]
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    location: Optional[str] = None


class MeetingTimeRequest(BaseModel):
    participant_ids: List[str]
    duration_minutes: int
    search_days: int = 5


class AgendaRequest(BaseModel):
    related_task_ids: Optional[List[str]] = None


class ActionItemsRequest(BaseModel):
    meeting_notes: str


class AvailabilityCheck(BaseModel):
    user: str
    start_date: datetime
    end_date: datetime


class PlanAdjustment(BaseModel):
    user: str
    unavailable_start: datetime
    unavailable_end: datetime
    reason: str


# ==================== EMPLOYEE ENDPOINTS ====================

@router.post("/employees")
def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db)
):
    """Create a new employee profile."""
    agent = PeopleOpsAgent(db)
    result = agent.create_employee_profile(
        name=employee.name,
        email=employee.email,
        role=employee.role,
        department=employee.department,
        timezone=employee.timezone,
        working_hours_start=employee.working_hours_start,
        working_hours_end=employee.working_hours_end,
        leave_balance=employee.leave_balance
    )
    return {
        "id": result.id,
        "name": result.name,
        "email": result.email,
        "role": result.role
    }


@router.get("/employees")
def list_employees(
    department: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all employees with optional department filter."""
    agent = PeopleOpsAgent(db)
    return agent.get_all_employees(department=department)


@router.get("/employees/{employee_id}")
def get_employee(
    employee_id: str,
    db: Session = Depends(get_db)
):
    """Get employee profile by ID."""
    agent = PeopleOpsAgent(db)
    result = agent.get_employee_profile(employee_id)
    if not result:
        raise HTTPException(status_code=404, detail="Employee not found")
    return result


@router.put("/employees/{employee_id}")
def update_employee(
    employee_id: str,
    updates: EmployeeUpdate,
    db: Session = Depends(get_db)
):
    """Update employee profile."""
    agent = PeopleOpsAgent(db)
    result = agent.update_employee_profile(
        employee_id,
        updates.model_dump(exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Employee not found")
    return result


@router.get("/employees/{employee_id}/workload")
def get_employee_workload(
    employee_id: str,
    db: Session = Depends(get_db)
):
    """Get workload analysis for an employee."""
    agent = PeopleOpsAgent(db)
    profile = agent.get_employee_profile(employee_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return agent.analyze_workload(user=profile["name"])


# ==================== SKILL MATRIX ENDPOINTS ====================

@router.get("/skills/matrix")
def get_skill_matrix(db: Session = Depends(get_db)):
    """Get skill matrix for entire team."""
    agent = PeopleOpsAgent(db)
    return agent.get_skill_matrix()


@router.post("/employees/{employee_id}/skills")
def update_employee_skills(
    employee_id: str,
    request: SkillsUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update skills for an employee."""
    agent = PeopleOpsAgent(db)
    skills_data = [s.model_dump() for s in request.skills]
    result = agent.update_employee_skills(employee_id, skills_data)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@router.post("/skills/gaps")
def identify_skill_gaps(
    request: SkillGapRequest,
    db: Session = Depends(get_db)
):
    """Identify skill gaps for required skills."""
    agent = PeopleOpsAgent(db)
    return agent.identify_skill_gaps(request.required_skills)


# ==================== LEAVE MANAGEMENT ENDPOINTS ====================

@router.post("/leaves")
def submit_leave_request(
    request: LeaveRequestCreate,
    db: Session = Depends(get_db)
):
    """Submit a new leave request."""
    agent = PeopleOpsAgent(db)
    result = agent.submit_leave_request(
        employee_id=request.employee_id,
        start_date=request.start_date,
        end_date=request.end_date,
        leave_type=request.leave_type,
        reason=request.reason
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/leaves")
def list_leave_requests(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List leave requests with optional filters."""
    agent = PeopleOpsAgent(db)
    return agent.get_leave_requests(status=status, employee_id=employee_id)


@router.get("/leaves/{leave_id}/impact")
def check_leave_impact(
    leave_id: str,
    db: Session = Depends(get_db)
):
    """Check delivery impact for a leave request."""
    from backend.app.models import LeaveRequest
    
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    agent = PeopleOpsAgent(db)
    # Get employee to find their name
    employee = agent.get_employee_profile(leave.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return agent._check_leave_impact(employee["name"], leave.start_date, leave.end_date)


@router.put("/leaves/{leave_id}/approve")
def approve_leave(
    leave_id: str,
    approval: LeaveApproval,
    db: Session = Depends(get_db)
):
    """Approve a leave request with rationale."""
    agent = PeopleOpsAgent(db)
    result = agent.approve_leave(
        leave_id=leave_id,
        reviewed_by=approval.reviewed_by,
        rationale=approval.rationale,
        coverage_plan=approval.coverage_plan
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.put("/leaves/{leave_id}/reject")
def reject_leave(
    leave_id: str,
    rejection: LeaveRejection,
    db: Session = Depends(get_db)
):
    """Reject a leave request with rationale and alternatives."""
    agent = PeopleOpsAgent(db)
    result = agent.reject_leave(
        leave_id=leave_id,
        reviewed_by=rejection.reviewed_by,
        rationale=rejection.rationale,
        suggested_alternative=rejection.suggested_alternative
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ==================== MEETING ENDPOINTS ====================

@router.post("/meetings")
def schedule_meeting(
    meeting: MeetingCreate,
    db: Session = Depends(get_db)
):
    """Schedule a new meeting with conflict detection."""
    agent = PeopleOpsAgent(db)
    result = agent.schedule_meeting(
        title=meeting.title,
        organizer=meeting.organizer,
        participant_ids=meeting.participant_ids,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        description=meeting.description,
        location=meeting.location
    )
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result)
    return result


@router.get("/meetings")
def list_meetings(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """List meetings within a date range."""
    from backend.app.models import Meeting, MeetingStatus
    from datetime import datetime, timedelta
    
    if not start_date:
        start_date = datetime.utcnow()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    meetings = db.query(Meeting).filter(
        Meeting.status == MeetingStatus.SCHEDULED,
        Meeting.start_time >= start_date,
        Meeting.end_time <= end_date
    ).all()
    
    return [{
        "id": m.id,
        "title": m.title,
        "organizer": m.organizer,
        "start_time": m.start_time.isoformat(),
        "end_time": m.end_time.isoformat(),
        "status": m.status.value
    } for m in meetings]


@router.post("/meetings/suggest-times")
def suggest_meeting_times(
    request: MeetingTimeRequest,
    db: Session = Depends(get_db)
):
    """Get optimal meeting time suggestions."""
    agent = PeopleOpsAgent(db)
    return agent.suggest_meeting_times(
        participant_ids=request.participant_ids,
        duration_minutes=request.duration_minutes,
        search_days=request.search_days
    )


@router.post("/meetings/{meeting_id}/agenda")
def create_meeting_agenda(
    meeting_id: str,
    request: AgendaRequest,
    db: Session = Depends(get_db)
):
    """Generate agenda for a meeting."""
    agent = PeopleOpsAgent(db)
    result = agent.create_agenda(
        meeting_id=meeting_id,
        related_task_ids=request.related_task_ids
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/meetings/{meeting_id}/action-items")
def extract_action_items(
    meeting_id: str,
    request: ActionItemsRequest,
    db: Session = Depends(get_db)
):
    """Extract action items from meeting notes."""
    agent = PeopleOpsAgent(db)
    result = agent.extract_action_items(
        meeting_id=meeting_id,
        meeting_notes=request.meeting_notes
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ==================== WORKLOAD & BURNOUT ENDPOINTS ====================

@router.get("/workload/balance")
def get_workload_balance(db: Session = Depends(get_db)):
    """Get team workload balance analysis."""
    agent = PeopleOpsAgent(db)
    return agent.analyze_workload()


@router.get("/workload/burnout-risk")
def get_burnout_risk_report(db: Session = Depends(get_db)):
    """Get burnout risk report for entire team."""
    agent = PeopleOpsAgent(db)
    return agent.get_team_burnout_report()


@router.get("/employees/{employee_id}/burnout-risk")
def get_employee_burnout_risk(
    employee_id: str,
    db: Session = Depends(get_db)
):
    """Get burnout risk assessment for a specific employee."""
    agent = PeopleOpsAgent(db)
    result = agent.assess_burnout_risk(employee_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ==================== AVAILABILITY & CALENDAR ENDPOINTS ====================

@router.post("/availability/check")
def check_availability(
    request: AvailabilityCheck,
    db: Session = Depends(get_db)
):
    """Check user availability for a date range."""
    agent = PeopleOpsAgent(db)
    return agent.check_availability(
        user=request.user,
        start_date=request.start_date,
        end_date=request.end_date
    )


@router.get("/calendar")
def get_team_calendar(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get team calendar with leaves, holidays, and meetings."""
    from datetime import datetime, timedelta
    
    if not start_date:
        start_date = datetime.utcnow()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    agent = PeopleOpsAgent(db)
    return agent.get_team_calendar(start_date, end_date)


@router.post("/plans/adjust")
def adjust_plans_for_availability(
    request: PlanAdjustment,
    db: Session = Depends(get_db)
):
    """Adjust plans when availability changes."""
    agent = PeopleOpsAgent(db)
    return agent.adjust_plans_for_availability(
        user=request.user,
        unavailable_start=request.unavailable_start,
        unavailable_end=request.unavailable_end,
        reason=request.reason
    )
