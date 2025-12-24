from fastapi import APIRouter, HTTPException
from app.schemas.managerial import (
    RiskAnalysisRequest, RiskAnalysisResponse,
    StandupRequest, StandupResponse,
    ReportRequest, ReportResponse,
    GoalInput, StructuredGoal,
    ConversationInput, ConversationSummary,
    StakeholderQueryRequest, StakeholderQueryResponse,
    ReminderRequest, ReminderResponse
)
from app.agents.managerial import managerial_agent

router = APIRouter(prefix="/managerial", tags=["managerial-intelligence"])

# --- STRATEGY ---
@router.post("/analyze-risks", response_model=RiskAnalysisResponse)
async def analyze_risks(request: RiskAnalysisRequest):
    return managerial_agent.analyze_risks(request.tasks, request.goals)

@router.post("/refine-goal", response_model=StructuredGoal)
async def refine_goal(request: GoalInput):
    return managerial_agent.refine_goal(request.raw_text)

# --- COMMUNICATION ---
@router.post("/generate-standup", response_model=StandupResponse)
async def generate_standup(request: StandupRequest):
    return managerial_agent.generate_standup_summary(request.completed_work, request.planned_work, request.blockers)

@router.post("/generate-report", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    return managerial_agent.generate_report(
        request.report_type, request.goals_progress, request.key_achievements,
        request.risks_mitigations, request.upcoming_priorities, request.audience
    )

@router.post("/generate-reminder", response_model=ReminderResponse)
async def generate_reminder(request: ReminderRequest):
    return managerial_agent.generate_reminder(request.recipient, request.topic, request.context, request.tone)

# --- INTELLIGENCE ---
@router.post("/summarize-conversation", response_model=ConversationSummary)
async def summarize_conversation(request: ConversationInput):
    return managerial_agent.summarize_conversation(request.transcript)

@router.post("/ask-stakeholder", response_model=StakeholderQueryResponse)
async def ask_stakeholder(request: StakeholderQueryRequest):
    return managerial_agent.answer_stakeholder_query(request.query, request.project_context)