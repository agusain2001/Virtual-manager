from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, Integer, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from backend.app.core.database import Base

# ==================== ENUMS ====================

class TaskStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ProjectHealth(enum.Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    DELAYED = "delayed"

class GoalStatus(enum.Enum):
    ACTIVE = "active"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EscalationStatus(enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class LeaveStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class SkillProficiency(enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"

class MeetingStatus(enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ParticipantStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"

class CandidateStage(enum.Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"

class InterviewStatus(enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class JobRoleStatus(enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    FILLED = "filled"

class ArticleStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class OnboardingStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class UserRole(enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"

class ApprovalStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ActionSensitivity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class OperationStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class RuleAction(enum.Enum):
    RECOMMEND = "recommend"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"

class RuleScope(enum.Enum):
    TASKS = "tasks"
    PEOPLE = "people"
    FINANCE = "finance"
    HIRING = "hiring"
    ALL = "all"

class WorkflowStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"

class PluginStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    ACTIVE = "active"
    DISABLED = "disabled"

# ==================== ASSOCIATION TABLES ====================

# Milestone-Task many-to-many relationship
milestone_tasks = Table(
    'milestone_tasks',
    Base.metadata,
    Column('milestone_id', String, ForeignKey('milestones.id'), primary_key=True),
    Column('task_id', String, ForeignKey('tasks.id'), primary_key=True)
)

# Meeting-Participant many-to-many relationship
meeting_participants = Table(
    'meeting_participants',
    Base.metadata,
    Column('meeting_id', String, ForeignKey('meetings.id'), primary_key=True),
    Column('employee_id', String, ForeignKey('employees.id'), primary_key=True)
)

# Task Dependencies - DAG relationships (blocker -> blocked)
task_dependencies = Table(
    'task_dependencies',
    Base.metadata,
    Column('blocker_id', String, ForeignKey('tasks.id'), primary_key=True),
    Column('blocked_id', String, ForeignKey('tasks.id'), primary_key=True)
)

# ==================== MODELS ====================

class Goal(Base):
    """
    Strategic goals for alignment tracking.
    Maps to: Strategy & Business Planning requirements.
    """
    __tablename__ = "goals"
    
    id = Column(String, primary_key=True)
    objective = Column(Text, nullable=False)
    kpis = Column(Text)  # JSON array of KPIs/success metrics
    owner = Column(String)
    time_horizon = Column(String)  # quarterly, monthly, yearly
    is_measurable = Column(Boolean, default=False)
    missing_criteria = Column(Text)  # What's missing if not measurable
    progress_percentage = Column(Integer, default=0)
    status = Column(Enum(GoalStatus), default=GoalStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    linked_tasks = relationship("GoalTaskLink", back_populates="goal", cascade="all, delete-orphan")


class GoalTaskLink(Base):
    """
    Links goals to tasks for alignment tracking.
    Enables scope creep detection.
    """
    __tablename__ = "goal_task_links"
    
    id = Column(String, primary_key=True)
    goal_id = Column(String, ForeignKey("goals.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    goal = relationship("Goal", back_populates="linked_tasks")
    task = relationship("Task", back_populates="goal_links")


class Project(Base):
    """Project entity with health tracking."""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    objective = Column(Text)
    owner = Column(String, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    health = Column(Enum(ProjectHealth), default=ProjectHealth.ON_TRACK)
    health_reason = Column(Text)  # Explanation for health status
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    escalations = relationship("Escalation", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    """Task entity with full tracking capabilities."""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    milestone_id = Column(String, ForeignKey("milestones.id"), nullable=True)
    owner = Column(String, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(Enum(TaskStatus), default=TaskStatus.NOT_STARTED)
    deadline = Column(DateTime)
    estimated_hours = Column(Integer)
    actual_hours = Column(Integer)
    is_escalated = Column(Boolean, default=False)
    escalation_count = Column(Integer, default=0)
    last_update_at = Column(DateTime, default=datetime.utcnow)  # For tracking staleness
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    project = relationship("Project", back_populates="tasks")
    milestone = relationship("Milestone", back_populates="linked_tasks")
    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan"
    )
    history = relationship("TaskHistory", back_populates="task", cascade="all, delete-orphan")
    goal_links = relationship("GoalTaskLink", back_populates="task", cascade="all, delete-orphan")
    escalations = relationship("Escalation", back_populates="task", cascade="all, delete-orphan")


class TaskDependency(Base):
    """Task dependency for DAG management."""
    __tablename__ = "task_dependencies"
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    depends_on_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on = relationship("Task", foreign_keys=[depends_on_id])


class TaskHistory(Base):
    """Audit trail for all task changes."""
    __tablename__ = "task_history"
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action = Column(String, nullable=False)  # created, updated, status_changed, reassigned, escalated
    field_changed = Column(String)
    old_value = Column(Text)
    new_value = Column(Text)
    trigger = Column(String)  # user, system, agent
    reason = Column(Text)
    
    task = relationship("Task", back_populates="history")


class Milestone(Base):
    """Project milestones with task linkage."""
    __tablename__ = "milestones"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    target_date = Column(DateTime)
    completion_percentage = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship("Project", back_populates="milestones")
    linked_tasks = relationship("Task", back_populates="milestone")


class Escalation(Base):
    """Escalation records for overdue/blocked tasks."""
    __tablename__ = "escalations"
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    reason = Column(Text, nullable=False)
    escalated_to = Column(String, nullable=False)  # manager, project_owner, etc.
    escalation_type = Column(String)  # overdue, blocked, no_update
    status = Column(Enum(EscalationStatus), default=EscalationStatus.OPEN)
    suggested_action = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    task = relationship("Task", back_populates="escalations")
    project = relationship("Project", back_populates="escalations")


class AgentActivity(Base):
    """Log of all agent decisions and actions."""
    __tablename__ = "agent_activities"
    
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    agent_name = Column(String, nullable=False)
    activity_type = Column(String, nullable=False)  # decision, action, notification, escalation
    message = Column(Text, nullable=False)
    related_task_id = Column(String, ForeignKey("tasks.id"))
    related_project_id = Column(String, ForeignKey("projects.id"))
    metadata = Column(Text)  # JSON string for additional context


class Holiday(Base):
    """Holiday/Leave calendar for deadline validation."""
    __tablename__ = "holidays"
    
    id = Column(String, primary_key=True)
    date = Column(DateTime, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String)  # public_holiday, company_holiday
    applies_to = Column(String)  # all, or specific user
    created_at = Column(DateTime, default=datetime.utcnow)


class UserLeave(Base):
    """User leave records for workload planning."""
    __tablename__ = "user_leaves"
    
    id = Column(String, primary_key=True)
    user = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    leave_type = Column(String)  # vacation, sick, personal
    status = Column(String, default="approved")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyUpdate(Base):
    """Daily progress updates from task owners."""
    __tablename__ = "daily_updates"
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    user = Column(String, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    progress_notes = Column(Text)
    hours_worked = Column(Integer, default=0)
    blockers = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== PEOPLE & OPERATIONS MODELS ====================

class Employee(Base):
    """
    Employee profile for People & Operations management.
    Maps to: Team & People Management requirements.
    """
    __tablename__ = "employees"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String)
    timezone = Column(String, default="UTC")  # e.g., "America/New_York"
    working_hours_start = Column(String, default="09:00")  # 24h format
    working_hours_end = Column(String, default="17:00")    # 24h format
    leave_balance = Column(Integer, default=20)  # Days remaining
    current_workload_hours = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    skills = relationship("EmployeeSkill", back_populates="employee", cascade="all, delete-orphan")
    meetings = relationship("Meeting", secondary="meeting_participants", back_populates="participants")


class EmployeeSkill(Base):
    """
    Employee skills for skill matrix tracking.
    Maps to: Track Skills and Expertise requirements.
    """
    __tablename__ = "employee_skills"
    
    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    skill_name = Column(String, nullable=False)
    proficiency = Column(Enum(SkillProficiency), default=SkillProficiency.BEGINNER)
    years_experience = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False)  # Primary skill
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee = relationship("Employee", back_populates="skills")


class Meeting(Base):
    """
    Meeting model for calendar management.
    Maps to: Meeting & Calendar Management requirements.
    """
    __tablename__ = "meetings"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    organizer = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    timezone = Column(String, default="UTC")
    location = Column(String)  # Room or virtual link
    status = Column(Enum(MeetingStatus), default=MeetingStatus.SCHEDULED)
    agenda = Column(Text)  # Meeting agenda
    action_items = Column(Text)  # JSON array of action items
    meeting_notes = Column(Text)  # Post-meeting notes
    related_project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    participants = relationship("Employee", secondary="meeting_participants", back_populates="meetings")


class LeaveRequest(Base):
    """
    Leave request with approval workflow.
    Maps to: Leave, Holiday & Attendance Management requirements.
    """
    __tablename__ = "leave_requests"
    
    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    leave_type = Column(String, nullable=False)  # vacation, sick, personal, emergency
    days_requested = Column(Integer, nullable=False)
    reason = Column(Text)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING)
    
    # Approval workflow
    reviewed_by = Column(String)
    reviewed_at = Column(DateTime)
    approval_rationale = Column(Text)  # Required for all decisions
    rejection_alternative = Column(Text)  # Suggested alternative dates if rejected
    
    # Impact tracking
    has_delivery_impact = Column(Boolean, default=False)
    impact_description = Column(Text)
    coverage_plan = Column(Text)  # Who covers during absence
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BurnoutIndicator(Base):
    """
    Burnout risk tracking for team members.
    Maps to: Monitor Workload and Burnout Risk requirements.
    """
    __tablename__ = "burnout_indicators"
    
    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    assessment_date = Column(DateTime, default=datetime.utcnow)
    
    # Risk indicators
    sustained_overload_weeks = Column(Integer, default=0)  # Weeks > 40h
    consecutive_deadline_pressure = Column(Integer, default=0)  # Count
    days_since_last_break = Column(Integer, default=0)
    overtime_hours_this_month = Column(Integer, default=0)
    
    # Calculated risk
    risk_level = Column(String)  # low, medium, high, critical
    risk_score = Column(Integer, default=0)  # 0-100
    
    # Recommendations
    recommendation = Column(Text)
    is_flagged = Column(Boolean, default=False)
    acknowledged_by = Column(String)
    acknowledged_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== GROWTH & SCALING MODELS ====================

class JobRole(Base):
    """
    Job role definition for recruitment.
    Maps to: Hiring & Recruitment requirements.
    """
    __tablename__ = "job_roles"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    team = Column(String, nullable=False)
    department = Column(String)
    responsibilities = Column(Text)  # JSON array
    required_skills = Column(Text)  # JSON array - must-have
    nice_to_have_skills = Column(Text)  # JSON array
    experience_years = Column(Integer, default=0)
    seniority_level = Column(String)  # junior, mid, senior, lead
    location = Column(String)
    work_mode = Column(String)  # remote, hybrid, onsite
    reports_to = Column(String)
    salary_range = Column(String)
    success_criteria = Column(Text)
    job_description = Column(Text)
    status = Column(Enum(JobRoleStatus), default=JobRoleStatus.DRAFT)
    is_approved = Column(Boolean, default=False)  # Human approval required
    approved_by = Column(String)
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidates = relationship("Candidate", back_populates="job_role", cascade="all, delete-orphan")


class Candidate(Base):
    """
    Candidate tracking for recruitment pipeline.
    Maps to: Track Candidates and Stages requirements.
    """
    __tablename__ = "candidates"
    
    id = Column(String, primary_key=True)
    job_role_id = Column(String, ForeignKey("job_roles.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String)
    resume_url = Column(String)
    linkedin_url = Column(String)
    stage = Column(Enum(CandidateStage), default=CandidateStage.APPLIED)
    source = Column(String)  # linkedin, referral, website, etc.
    notes = Column(Text)
    skills_match_score = Column(Integer)  # 0-100
    rejection_reason = Column(Text)
    rejection_approved_by = Column(String)  # Human approval for rejection
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job_role = relationship("JobRole", back_populates="candidates")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")


class Interview(Base):
    """
    Interview scheduling and feedback.
    Maps to: Schedule Interviews and Summarize Feedback requirements.
    """
    __tablename__ = "interviews"
    
    id = Column(String, primary_key=True)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    round_number = Column(Integer, default=1)  # Interview round (1, 2, 3...)
    interview_type = Column(String)  # phone_screen, technical, behavioral, culture
    interviewers = Column(Text)  # JSON array of interviewer names
    scheduled_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    location = Column(String)  # Room or video link
    agenda = Column(Text)
    status = Column(Enum(InterviewStatus), default=InterviewStatus.SCHEDULED)
    
    # Feedback (collected post-interview)
    feedback = Column(Text)  # JSON array of feedback from each interviewer
    strengths = Column(Text)
    concerns = Column(Text)
    recommendation = Column(String)  # strong_hire, hire, no_hire, strong_no_hire
    feedback_summary = Column(Text)  # AI-generated summary
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="interviews")


class OnboardingPlan(Base):
    """
    Onboarding plan for new hires.
    Maps to: Generate Onboarding Plans requirements.
    """
    __tablename__ = "onboarding_plans"
    
    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    role = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    
    # 30-60-90 day goals
    goals_30_days = Column(Text)  # JSON array
    goals_60_days = Column(Text)  # JSON array
    goals_90_days = Column(Text)  # JSON array
    
    # Buddy/mentor assignment
    buddy_name = Column(String)
    mentor_name = Column(String)
    
    status = Column(Enum(OnboardingStatus), default=OnboardingStatus.NOT_STARTED)
    completion_percentage = Column(Integer, default=0)
    feedback = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = relationship("OnboardingTask", back_populates="plan", cascade="all, delete-orphan")


class OnboardingTask(Base):
    """
    Individual onboarding tasks.
    Maps to: Assign Onboarding Tasks requirements.
    """
    __tablename__ = "onboarding_tasks"
    
    id = Column(String, primary_key=True)
    plan_id = Column(String, ForeignKey("onboarding_plans.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)  # account_setup, tool_access, documentation, assignment
    day_due = Column(Integer)  # Day number (1-90)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    documentation_url = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    plan = relationship("OnboardingPlan", back_populates="tasks")


class KnowledgeArticle(Base):
    """
    Internal knowledge base articles.
    Maps to: Maintain Internal Knowledge Base requirements.
    """
    __tablename__ = "knowledge_articles"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    category = Column(String)  # onboarding, faq, best_practices, process
    tags = Column(Text)  # JSON array
    status = Column(Enum(ArticleStatus), default=ArticleStatus.DRAFT)
    
    # Metadata
    author = Column(String)
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    is_outdated = Column(Boolean, default=False)
    outdated_reason = Column(Text)
    last_reviewed_at = Column(DateTime)
    
    # Role-specific targeting
    target_roles = Column(Text)  # JSON array of roles this applies to
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== PLATFORM & ENTERPRISE MODELS ====================

class User(Base):
    """
    User account for authentication and authorization.
    Maps to: Role-Based Access Control requirements.
    """
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String)  # Hashed password
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    permissions = Column(Text)  # JSON array of specific permissions
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    last_login = Column(DateTime)
    last_password_change = Column(DateTime)
    
    # Multi-tenant support
    tenant_id = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """
    Immutable audit trail for all system actions.
    Maps to: Audit Trails requirements - who, what, when, why.
    """
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Who
    actor_id = Column(String)  # User ID or 'system'
    actor_name = Column(String)
    actor_role = Column(String)
    
    # What
    action = Column(String, nullable=False)  # create, update, delete, approve, reject
    resource_type = Column(String, nullable=False)  # task, project, user, etc.
    resource_id = Column(String)
    resource_name = Column(String)
    
    # Details
    changes = Column(Text)  # JSON of before/after values
    metadata = Column(Text)  # Additional context
    
    # Why
    reason = Column(Text)
    
    # Outcome
    outcome = Column(String)  # success, failure, denied
    error_message = Column(Text)
    
    # Security context
    ip_address = Column(String)
    user_agent = Column(String)
    tenant_id = Column(String)


class ApprovalRequest(Base):
    """
    Approval workflow for sensitive actions.
    Maps to: Approval Workflows requirements.
    """
    __tablename__ = "approval_requests"
    
    id = Column(String, primary_key=True)
    
    # What needs approval
    action_type = Column(String, nullable=False)  # delete_data, send_external, hire_decision
    sensitivity = Column(Enum(ActionSensitivity), default=ActionSensitivity.HIGH)
    resource_type = Column(String)
    resource_id = Column(String)
    action_summary = Column(Text, nullable=False)
    action_details = Column(Text)  # JSON with full action context
    
    # Impact assessment
    impact_summary = Column(Text)
    is_reversible = Column(Boolean, default=True)
    
    # Request info
    requester_id = Column(String, nullable=False)
    requester_name = Column(String)
    requested_at = Column(DateTime, default=datetime.utcnow)
    
    # Approval chain
    required_approvers = Column(Text)  # JSON array of user IDs
    current_approvers = Column(Text)  # JSON array of users who approved
    
    # Status
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    expires_at = Column(DateTime)
    
    # Resolution
    resolved_by = Column(String)
    resolved_at = Column(DateTime)
    resolution_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemState(Base):
    """
    Versioned system state for rollback support.
    Maps to: State Management and Rollback requirements.
    """
    __tablename__ = "system_states"
    
    id = Column(String, primary_key=True)
    key = Column(String, nullable=False, index=True)  # config.feature_x, state.workflow_y
    value = Column(Text, nullable=False)  # JSON value
    value_type = Column(String)  # string, number, boolean, json
    
    # Versioning
    version = Column(Integer, default=1)
    previous_value = Column(Text)
    
    # Metadata
    description = Column(Text)
    changed_by = Column(String)
    change_reason = Column(Text)
    
    # Rollback info
    is_rollback = Column(Boolean, default=False)
    rolled_back_from_version = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OperationLock(Base):
    """
    Idempotency tracking for operations.
    Maps to: Idempotent Operations requirements.
    """
    __tablename__ = "operation_locks"
    
    id = Column(String, primary_key=True)
    operation_id = Column(String, unique=True, nullable=False)  # Client-provided idempotency key
    operation_type = Column(String, nullable=False)
    resource_type = Column(String)
    resource_id = Column(String)
    
    # Status
    status = Column(Enum(OperationStatus), default=OperationStatus.PENDING)
    result = Column(Text)  # JSON result if completed
    error = Column(Text)
    
    # Locking
    locked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Lock expiration for cleanup
    completed_at = Column(DateTime)
    
    # Context
    actor_id = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ==================== FUTURE & ADVANCED CAPABILITIES MODELS ====================

class OrganizationRule(Base):
    """
    Organization-specific rules for customization.
    Maps to: Rules Engine requirements.
    
    CONSTRAINT: Rules cannot override security policies or platform safety gates.
    """
    __tablename__ = "organization_rules"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Condition and action
    condition = Column(Text, nullable=False)  # JSON structured expression
    action = Column(Enum(RuleAction), nullable=False)
    scope = Column(Enum(RuleScope), default=RuleScope.ALL)
    
    # Priority for conflict resolution (higher = more priority)
    priority = Column(Integer, default=50)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomWorkflow(Base):
    """
    DAG-based custom workflow definitions.
    Maps to: Custom Workflows requirements.
    
    CONSTRAINT: No direct data mutation, no bypassing approval steps.
    """
    __tablename__ = "custom_workflows"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # DAG definition
    trigger = Column(String)  # Event that triggers workflow
    steps = Column(Text, nullable=False)  # JSON array of WorkflowStep
    
    # Status
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.DRAFT)
    
    # Validation
    is_validated = Column(Boolean, default=False)
    validation_errors = Column(Text)  # JSON array of errors
    last_validated_at = Column(DateTime)
    
    # Dry run
    last_dry_run_at = Column(DateTime)
    dry_run_result = Column(Text)  # JSON result
    
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Plugin(Base):
    """
    Plugin-style extension registry.
    Maps to: Plugin System requirements.
    
    CONSTRAINT: Runs in sandbox with timeout/memory limits.
    Plugin crash must not affect core system.
    """
    __tablename__ = "plugins"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, index=True)  # null = global plugin
    
    # Metadata
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    description = Column(Text)
    author = Column(String)
    
    # Permissions and schemas
    required_permissions = Column(Text)  # JSON array
    input_schema = Column(Text)  # JSON schema
    output_schema = Column(Text)  # JSON schema
    
    # Execution config
    entry_point = Column(String)  # Function to call
    timeout_seconds = Column(Integer, default=30)
    memory_limit_mb = Column(Integer, default=128)
    
    # Status
    status = Column(Enum(PluginStatus), default=PluginStatus.PENDING)
    
    # Usage stats
    execution_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime)
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VoiceIntent(Base):
    """
    Parsed voice command intents.
    Maps to: Voice-Based Management requirements.
    
    CONSTRAINT: Voice produces intent only, never action.
    Sensitive intents always require confirmation.
    """
    __tablename__ = "voice_intents"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, index=True)
    user_id = Column(String, nullable=False)
    
    # Voice data
    transcription = Column(Text, nullable=False)
    confidence = Column(Float)  # Transcription confidence
    
    # Parsed intent
    intent_type = Column(String)  # The detected intent
    intent_params = Column(Text)  # JSON parameters
    is_sensitive = Column(Boolean, default=False)
    
    # Confirmation
    requires_confirmation = Column(Boolean, default=True)
    confirmed = Column(Boolean, default=False)
    confirmed_at = Column(DateTime)
    
    # Execution
    executed = Column(Boolean, default=False)
    execution_result = Column(Text)  # JSON result
    
    created_at = Column(DateTime, default=datetime.utcnow)


class StaffingPrediction(Base):
    """
    Predictive staffing recommendations.
    Maps to: Predictive Staffing requirements.
    
    CONSTRAINT: Cannot trigger hiring. Recommendation only.
    """
    __tablename__ = "staffing_predictions"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, nullable=False, index=True)
    
    # Prediction context
    department = Column(String)
    role_type = Column(String)
    time_horizon = Column(String)  # e.g., "Q1 2025", "next_6_months"
    
    # Recommendation
    recommended_headcount = Column(Integer)
    confidence_lower = Column(Integer)  # Lower bound
    confidence_upper = Column(Integer)  # Upper bound
    confidence_level = Column(Float)  # 0-1
    
    # Assumptions
    assumptions = Column(Text)  # JSON array of assumptions
    data_sources = Column(Text)  # JSON array of sources used
    
    # Signals used
    historical_workload = Column(Text)  # JSON summary
    task_velocity = Column(Text)  # JSON summary
    growth_signals = Column(Text)  # JSON summary
    
    generated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Prediction validity


class PerformanceFeedback(Base):
    """
    Private AI-assisted performance coaching.
    Maps to: AI-Assisted Performance Coaching requirements.
    
    CONSTRAINT: Private, optional, supportive.
    No ranking employees. No sharing without consent.
    """
    __tablename__ = "performance_feedback"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)  # Owner of feedback
    
    # Feedback content
    feedback_type = Column(String)  # strength, growth_area, suggestion
    content = Column(Text, nullable=False)
    context = Column(Text)  # What prompted this feedback
    
    # Privacy
    is_private = Column(Boolean, default=True)
    consent_to_share = Column(Boolean, default=False)
    shared_with = Column(Text)  # JSON array of user IDs if shared
    
    # User response
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    is_helpful = Column(Boolean)
    user_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class FeatureFlag(Base):
    """
    Per-organization feature toggles.
    Maps to: Configuration & State Management requirements.
    """
    __tablename__ = "feature_flags"
    
    id = Column(String, primary_key=True)
    organization_id = Column(String, nullable=False, index=True)
    
    # Flag definition
    flag_key = Column(String, nullable=False)
    flag_value = Column(Boolean, default=False)
    
    # Rollout
    rollout_percentage = Column(Integer, default=100)  # 0-100
    
    # Versioning
    version = Column(Integer, default=1)
    previous_value = Column(Boolean)
    
    # Metadata
    description = Column(Text)
    changed_by = Column(String)
    change_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)