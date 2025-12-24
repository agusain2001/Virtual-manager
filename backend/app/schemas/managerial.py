from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# --- RISK & STRATEGY ---
class Mitigation(BaseModel):
    strategy: str = Field(..., description="The proposed mitigation strategy")
    cost_vs_benefit: str = Field(..., description="Explanation of cost versus benefit")
    required_approvals: List[str] = Field(default_factory=list, description="List of required approvals")

class Risk(BaseModel):
    description: str = Field(..., description="Description of the risk (delayed tasks, overload, etc.)")
    likelihood: Literal["Low", "Medium", "High"]
    impact: Literal["Low", "Medium", "High"]
    affected_goals: List[str] = Field(..., description="List of goals affected by this risk")
    mitigations: List[Mitigation] = Field(..., description="List of mitigation strategies")

class RiskAnalysisRequest(BaseModel):
    tasks: List[dict] = Field(..., description="List of current tasks with status and due dates")
    goals: List[dict] = Field(..., description="List of active organizational goals")

class RiskAnalysisResponse(BaseModel):
    risks: List[Risk]
    overall_assessment: str

# --- GOAL PLANNING ---
class GoalInput(BaseModel):
    raw_text: str = Field(..., description="Raw goal text, e.g., 'Increase customer retention'")

class StructuredGoal(BaseModel):
    objective: str
    kpis: List[str] = Field(..., description="Measurable success metrics")
    time_horizon: str
    owner: Optional[str]
    is_measurable: bool
    missing_criteria: Optional[str] = Field(None, description="What is missing to make this measurable")

# --- COMMUNICATION (Standups, Reports, Reminders) ---
class StandupRequest(BaseModel):
    completed_work: List[str]
    planned_work: List[str]
    blockers: List[str]

class StandupResponse(BaseModel):
    summary: str
    action_items: List[str]

class ReportRequest(BaseModel):
    report_type: Literal["Weekly", "Monthly"]
    goals_progress: List[str]
    key_achievements: List[str]
    risks_mitigations: List[str]
    upcoming_priorities: List[str]
    audience: Literal["Executive", "Team"]

class ReportResponse(BaseModel):
    report_content: str
    key_takeaways: List[str]

class ReminderRequest(BaseModel):
    recipient: str
    topic: str
    context: str = Field(..., description="Why is this reminder being sent? e.g. 'Task overdue by 2 days'")
    tone: Literal["Respectful", "Urgent", "Neutral"]

class ReminderResponse(BaseModel):
    message: str

# --- INTELLIGENCE (Meetings, Q&A) ---
class ConversationInput(BaseModel):
    transcript: str

class ConversationSummary(BaseModel):
    decisions: List[str]
    action_items: List[str]
    unresolved_questions: List[str]

class StakeholderQueryRequest(BaseModel):
    query: str
    project_context: str

class StakeholderQueryResponse(BaseModel):
    answer: str
    reasoning: str