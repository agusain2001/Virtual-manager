"""
Advanced Capabilities API Routes.

Provides REST API endpoints for:
- Organization rules engine
- Custom workflows
- Plugin system
- Voice intent processing
- Predictive staffing
- Feature flags

All endpoints are sandboxed - no direct action execution.
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from backend.app.core.database import get_db
from backend.app.agents.advanced_capabilities import AdvancedCapabilitiesAgent


router = APIRouter(prefix="/api/v1/advanced", tags=["Advanced Capabilities"])


# ==================== PYDANTIC SCHEMAS ====================

class RuleCreate(BaseModel):
    name: str
    condition: Dict[str, Any]
    action: str
    scope: str = "all"
    priority: int = 50
    description: Optional[str] = None


class RuleEvaluate(BaseModel):
    event_type: str
    event_data: Dict[str, Any]
    scope: Optional[str] = None


class WorkflowCreate(BaseModel):
    name: str
    steps: List[Dict[str, Any]]
    trigger: Optional[str] = None
    description: Optional[str] = None


class PluginRegister(BaseModel):
    name: str
    version: str
    required_permissions: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    entry_point: str
    description: Optional[str] = None
    author: Optional[str] = None
    timeout_seconds: int = 30
    memory_limit_mb: int = 128


class PluginExecute(BaseModel):
    input_data: Dict[str, Any]


class VoiceProcess(BaseModel):
    transcription: str
    confidence: float = 1.0


class VoiceConfirm(BaseModel):
    confirmed: bool


class StaffingRequest(BaseModel):
    department: Optional[str] = None
    role_type: Optional[str] = None
    time_horizon: str = "next_quarter"


class FinancialAnalysis(BaseModel):
    resource_changes: List[Dict[str, Any]]
    time_period: str = "annual"


class FeedbackCreate(BaseModel):
    feedback_type: str
    content: str
    context: Optional[str] = None


class FeatureFlagUpdate(BaseModel):
    flag_value: bool
    reason: Optional[str] = None


# ==================== RULES ENDPOINTS ====================

@router.post("/rules")
def create_rule(
    rule: RuleCreate,
    x_org_id: str = Header("default"),
    x_user_id: str = Header("system"),
    db: Session = Depends(get_db)
):
    """Create an organization-specific rule."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    result = agent.create_rule(
        name=rule.name,
        condition=rule.condition,
        action=rule.action,
        scope=rule.scope,
        priority=rule.priority,
        description=rule.description,
        created_by=x_user_id
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/rules")
def list_rules(
    scope: Optional[str] = None,
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """List all rules for the organization."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.get_rules(scope)


@router.post("/rules/evaluate")
def evaluate_rules(
    request: RuleEvaluate,
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """Evaluate rules against an event."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.evaluate_rules(
        event_type=request.event_type,
        event_data=request.event_data,
        scope=request.scope
    )


# ==================== WORKFLOW ENDPOINTS ====================

@router.post("/workflows")
def create_workflow(
    workflow: WorkflowCreate,
    x_org_id: str = Header("default"),
    x_user_id: str = Header("system"),
    db: Session = Depends(get_db)
):
    """Create a custom DAG workflow."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.create_workflow(
        name=workflow.name,
        steps=workflow.steps,
        trigger=workflow.trigger,
        description=workflow.description,
        created_by=x_user_id
    )


@router.post("/workflows/{workflow_id}/validate")
def validate_workflow(
    workflow_id: str,
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """Validate workflow for cycles and permissions."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    result = agent.validate_workflow(workflow_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/workflows/{workflow_id}/activate")
def activate_workflow(
    workflow_id: str,
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """Activate a validated workflow."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    result = agent.activate_workflow(workflow_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==================== PLUGIN ENDPOINTS ====================

@router.post("/plugins")
def register_plugin(
    plugin: PluginRegister,
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """Register a new plugin."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.register_plugin(
        name=plugin.name,
        version=plugin.version,
        required_permissions=plugin.required_permissions,
        input_schema=plugin.input_schema,
        output_schema=plugin.output_schema,
        entry_point=plugin.entry_point,
        description=plugin.description,
        author=plugin.author,
        timeout_seconds=plugin.timeout_seconds,
        memory_limit_mb=plugin.memory_limit_mb
    )


@router.get("/plugins")
def list_plugins(
    status: Optional[str] = None,
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """List all plugins."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.get_plugins(status)


@router.post("/plugins/{plugin_id}/approve")
def approve_plugin(
    plugin_id: str,
    x_org_id: str = Header("default"),
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """Approve a plugin."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    result = agent.approve_plugin(plugin_id, x_user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/plugins/{plugin_id}/execute")
def execute_plugin(
    plugin_id: str,
    request: PluginExecute,
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """Execute a plugin in sandbox."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    result = agent.execute_plugin(plugin_id, request.input_data)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ==================== VOICE ENDPOINTS ====================

@router.post("/voice/process")
def process_voice(
    request: VoiceProcess,
    x_org_id: str = Header("default"),
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """Process voice transcription into intent."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.process_voice_intent(
        transcription=request.transcription,
        user_id=x_user_id,
        confidence=request.confidence
    )


@router.post("/voice/{intent_id}/confirm")
def confirm_voice_action(
    intent_id: str,
    request: VoiceConfirm,
    x_org_id: str = Header("default"),
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """Confirm or reject a voice intent."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    result = agent.confirm_voice_action(intent_id, request.confirmed, x_user_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ==================== PREDICTION ENDPOINTS ====================

@router.post("/predictions/staffing")
def predict_staffing(
    request: StaffingRequest,
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """Generate staffing predictions. RECOMMENDATION ONLY."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.predict_staffing(
        department=request.department,
        role_type=request.role_type,
        time_horizon=request.time_horizon
    )


@router.post("/predictions/financial-impact")
def analyze_financial_impact(
    request: FinancialAnalysis,
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """Analyze financial impact. READ-ONLY."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.analyze_financial_impact(
        resource_changes=request.resource_changes,
        time_period=request.time_period
    )


# ==================== FEEDBACK ENDPOINTS ====================

@router.post("/feedback")
def create_feedback(
    request: FeedbackCreate,
    x_org_id: str = Header("default"),
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """Generate private performance feedback."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.generate_feedback(
        user_id=x_user_id,
        feedback_type=request.feedback_type,
        content=request.content,
        context=request.context
    )


@router.get("/feedback/me")
def get_my_feedback(
    x_org_id: str = Header("default"),
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """Get user's own feedback."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.get_personal_feedback(x_user_id)


# ==================== FEATURE FLAG ENDPOINTS ====================

@router.get("/feature-flags")
def get_feature_flags(
    x_org_id: str = Header("default"),
    db: Session = Depends(get_db)
):
    """Get all feature flags."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.get_feature_flags()


@router.put("/feature-flags/{flag_key}")
def set_feature_flag(
    flag_key: str,
    request: FeatureFlagUpdate,
    x_org_id: str = Header("default"),
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """Set a feature flag."""
    agent = AdvancedCapabilitiesAgent(db, x_org_id)
    return agent.set_feature_flag(
        flag_key=flag_key,
        flag_value=request.flag_value,
        changed_by=x_user_id,
        reason=request.reason
    )
