"""
Risk Agent - Implements Decision Support & Risk Management.

Capabilities:
- Risk Assessment: Analyze project health and generate risks
- Mitigation Planning: Suggest mitigations for identified risks
- Daily Monitoring: Run risk checks on schedule

Maps to: "Decision Support & Risk Management" prompt requirements.
"""

import uuid
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from openai import OpenAI
import os

from backend.app.models import (
    Project, Task, TaskStatus, Risk, RiskLevel, DecisionLog, ProjectHealth, AgentAuditLog
)
from backend.app.core.logging import logger


class RiskAgent:
    """
    Risk Agent for project risk management.
    
    Monitors project health and generates actionable risk assessments.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._llm_client = None
    
    @property
    def llm_client(self):
        if self._llm_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._llm_client = OpenAI(api_key=api_key)
        return self._llm_client
    
    def assess_project_risk(self, project_id: str) -> Dict[str, Any]:
        """
        Run a full risk assessment on a project.
        
        1. Fetches project health (from Phase 1)
        2. Analyzes blocked tasks and deadlines
        3. Generates risk entries with mitigations
        """
        # Get project
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": "Project not found"}
        
        # Get project health data
        health_data = self._get_project_health(project_id)
        
        # Get blocked and overdue tasks
        tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
        blocked_tasks = [t for t in tasks if t.status == TaskStatus.BLOCKED]
        overdue_tasks = [
            t for t in tasks 
            if t.deadline and t.deadline < datetime.utcnow() 
            and t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        ]
        
        risks = []
        
        # Generate risks based on health status
        if health_data["status"] in ["AT_RISK", "DELAYED"]:
            if self.llm_client:
                risks = self._generate_risks_with_llm(
                    project, health_data, blocked_tasks, overdue_tasks
                )
            else:
                risks = self._generate_risks_simple(
                    project, health_data, blocked_tasks, overdue_tasks
                )
        
        # Save risks to database
        saved_risks = []
        for risk_data in risks:
            risk = Risk(
                id=str(uuid.uuid4()),
                project_id=project_id,
                description=risk_data["description"],
                likelihood=RiskLevel(risk_data.get("likelihood", "medium")),
                impact=RiskLevel(risk_data.get("impact", "medium")),
                mitigation_plan=risk_data.get("mitigation"),
                created_by="system"
            )
            self.db.add(risk)
            saved_risks.append({
                "id": risk.id,
                "description": risk.description,
                "likelihood": risk.likelihood.value,
                "impact": risk.impact.value,
                "mitigation": risk.mitigation_plan
            })
        
        # Log decision
        self._log_decision(
            context=f"Risk assessment for project '{project.name}' (Health: {health_data['status']})",
            decision=f"Identified {len(risks)} risks",
            rationale=f"Project has {len(blocked_tasks)} blocked tasks and {len(overdue_tasks)} overdue tasks",
            project_id=project_id
        )
        
        self.db.commit()
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "health_status": health_data["status"],
            "blocked_count": len(blocked_tasks),
            "overdue_count": len(overdue_tasks),
            "risks_identified": len(saved_risks),
            "risks": saved_risks
        }
    
    def _get_project_health(self, project_id: str) -> Dict[str, Any]:
        """Calculate project health (same logic as Phase 1 health endpoint)."""
        tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
        
        if not tasks:
            return {"status": "NO_TASKS", "completion_percentage": 0}
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        blocked = sum(1 for t in tasks if t.status == TaskStatus.BLOCKED)
        cancelled = sum(1 for t in tasks if t.status == TaskStatus.CANCELLED)
        
        now = datetime.utcnow()
        overdue = sum(
            1 for t in tasks 
            if t.deadline and t.deadline < now 
            and t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]
        )
        
        active_tasks = total - cancelled
        overdue_percentage = (overdue / active_tasks * 100) if active_tasks > 0 else 0
        blocked_percentage = (blocked / active_tasks * 100) if active_tasks > 0 else 0
        completion_percentage = (completed / active_tasks * 100) if active_tasks > 0 else 0
        
        if overdue_percentage > 20:
            status = "DELAYED"
        elif overdue > 0 or blocked_percentage > 50:
            status = "AT_RISK"
        else:
            status = "ON_TRACK"
        
        return {
            "status": status,
            "completion_percentage": round(completion_percentage, 1),
            "blocked_count": blocked,
            "overdue_count": overdue
        }
    
    def _generate_risks_with_llm(
        self,
        project: Project,
        health_data: Dict,
        blocked_tasks: List[Task],
        overdue_tasks: List[Task]
    ) -> List[Dict]:
        """Use LLM to generate detailed risk assessments."""
        blocked_summary = ", ".join([f"'{t.name}'" for t in blocked_tasks[:5]])
        overdue_summary = ", ".join([f"'{t.name}' (due {t.deadline.date()})" for t in overdue_tasks[:5]])
        
        prompt = f"""
        Analyze this project and generate specific risks with mitigations.
        
        Project: {project.name}
        Health Status: {health_data['status']}
        Completion: {health_data['completion_percentage']}%
        Blocked Tasks: {blocked_summary or 'None'}
        Overdue Tasks: {overdue_summary or 'None'}
        Project End Date: {project.end_date.date() if project.end_date else 'Not set'}
        
        Return JSON with array of risks:
        - description: Specific risk description
        - likelihood: low, medium, or high
        - impact: low, medium, or high
        - mitigation: Actionable mitigation plan
        
        Generate 1-3 most important risks.
        """
        
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a project risk analyst. Generate specific, actionable risk assessments."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            data = json.loads(response.choices[0].message.content)
            return data.get("risks", [data]) if isinstance(data, dict) else data
            
        except Exception as e:
            logger.error(f"LLM risk generation failed: {e}")
            return self._generate_risks_simple(project, health_data, blocked_tasks, overdue_tasks)
    
    def _generate_risks_simple(
        self,
        project: Project,
        health_data: Dict,
        blocked_tasks: List[Task],
        overdue_tasks: List[Task]
    ) -> List[Dict]:
        """Generate basic risks without LLM."""
        risks = []
        
        if overdue_tasks:
            risks.append({
                "description": f"Project has {len(overdue_tasks)} overdue task(s), risking overall deadline",
                "likelihood": "high",
                "impact": "high" if len(overdue_tasks) > 2 else "medium",
                "mitigation": "Review overdue tasks and reassign or adjust deadlines"
            })
        
        if blocked_tasks:
            risks.append({
                "description": f"Project has {len(blocked_tasks)} blocked task(s) causing delivery delays",
                "likelihood": "high",
                "impact": "medium",
                "mitigation": "Identify blocking dependencies and prioritize their completion"
            })
        
        if health_data["status"] == "DELAYED":
            risks.append({
                "description": "Project is significantly delayed with more than 20% tasks overdue",
                "likelihood": "high",
                "impact": "high",
                "mitigation": "Escalate to stakeholders and consider scope reduction or deadline extension"
            })
        
        return risks
    
    def get_project_risks(self, project_id: str) -> List[Dict]:
        """Get all active risks for a project."""
        risks = self.db.query(Risk).filter(
            Risk.project_id == project_id,
            Risk.status == "open"
        ).all()
        
        return [{
            "id": r.id,
            "description": r.description,
            "likelihood": r.likelihood.value,
            "impact": r.impact.value,
            "mitigation": r.mitigation_plan,
            "created_at": r.created_at.isoformat()
        } for r in risks]
    
    def mitigate_risk(self, risk_id: str, resolution_notes: str) -> Dict[str, Any]:
        """Mark a risk as mitigated."""
        risk = self.db.query(Risk).filter(Risk.id == risk_id).first()
        if not risk:
            return {"error": "Risk not found"}
        
        risk.status = "mitigated"
        risk.mitigation_plan = f"{risk.mitigation_plan}\n\nResolution: {resolution_notes}"
        self.db.commit()
        
        return {"success": True, "risk_id": risk_id, "status": "mitigated"}
    
    def _log_decision(
        self,
        context: str,
        decision: str,
        rationale: str,
        project_id: str = None
    ):
        """Log agent decision."""
        log = DecisionLog(
            id=str(uuid.uuid4()),
            context=context,
            decision_made=decision,
            rationale=rationale,
            agent_name="RiskAgent",
            project_id=project_id
        )
        self.db.add(log)


# ==================== RISK GATE SERVICE (Phase 4: Safety & Governance) ====================

# Risk scoring dictionary - higher score = more dangerous
RISK_SCORES: Dict[str, int] = {
    # Destructive actions - maximum risk
    "delete_repo": 100,
    "delete_project": 90,
    "delete_all_tasks": 95,
    "fire_employee": 100,
    "terminate_contract": 95,
    
    # External communications - high risk
    "send_external_email": 60,
    "post_to_slack_channel": 50,
    "create_public_issue": 55,
    
    # Data modifications - medium risk
    "bulk_update_tasks": 45,
    "reassign_all_tasks": 50,
    "change_project_deadline": 40,
    "close_all_issues": 70,
    
    # Standard operations - low risk
    "create_meeting": 10,
    "schedule_focus_block": 5,
    "update_task": 5,
    "create_task": 5,
    "add_comment": 5,
    "create_issue": 10,
}

# Default threshold - actions above this require approval
DEFAULT_APPROVAL_THRESHOLD = 50


class RiskGateService:
    """
    Risk Gate Service for intercepting and gating high-risk AI actions.
    
    Every agent should pass through this gate before executing sensitive actions.
    Actions above the risk threshold are queued for human approval.
    
    Phase 4: Safety & Governance implementation.
    """
    
    def __init__(self, db: Session, approval_threshold: int = DEFAULT_APPROVAL_THRESHOLD):
        self.db = db
        self.approval_threshold = approval_threshold
    
    def assess_risk(self, action_type: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Assess the risk level of an action.
        
        Args:
            action_type: The type of action (e.g., "delete_project")
            payload: The action parameters
        
        Returns:
            Risk assessment with score and whether approval is required
        """
        # Get base risk score
        base_score = RISK_SCORES.get(action_type, 25)  # Default to 25 for unknown
        
        # Adjust score based on payload characteristics
        adjusted_score = base_score
        
        if payload:
            # Bulk operations are riskier
            if payload.get("count", 1) > 10:
                adjusted_score = min(100, adjusted_score + 20)
            
            # Operations affecting multiple users are riskier
            if payload.get("affects_users", 0) > 5:
                adjusted_score = min(100, adjusted_score + 15)
            
            # Irreversible operations are riskier
            if payload.get("irreversible", False):
                adjusted_score = min(100, adjusted_score + 25)
        
        requires_approval = adjusted_score >= self.approval_threshold
        
        return {
            "action_type": action_type,
            "base_score": base_score,
            "adjusted_score": adjusted_score,
            "requires_approval": requires_approval,
            "threshold": self.approval_threshold,
            "risk_level": self._get_risk_level(adjusted_score)
        }
    
    def _get_risk_level(self, score: int) -> str:
        """Convert numeric score to risk level string."""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        return "minimal"
    
    async def submit_for_approval(
        self,
        user_id: str,
        agent_name: str,
        action_type: str,
        action_summary: str,
        payload: Dict[str, Any],
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit an action for human approval.
        
        Args:
            user_id: The user requesting the action
            agent_name: Which agent is requesting (e.g., "github", "calendar")
            action_type: Type of action
            action_summary: Human-readable description
            payload: Full action parameters (stored as JSON)
            resource_type: Optional type of resource being acted upon
            resource_id: Optional ID of resource
        
        Returns:
            The created ApprovalRequest
        """
        from backend.app.models import ApprovalRequest, ApprovalStatus, ActionSensitivity, User
        
        # Assess risk
        risk_assessment = self.assess_risk(action_type, payload)
        
        # Get user name
        user = self.db.query(User).filter(User.id == user_id).first()
        requester_name = user.name if user else "Unknown"
        
        # Determine sensitivity from risk level
        risk_level = risk_assessment["risk_level"]
        sensitivity_map = {
            "critical": ActionSensitivity.CRITICAL,
            "high": ActionSensitivity.HIGH,
            "medium": ActionSensitivity.MEDIUM,
            "low": ActionSensitivity.LOW,
        }
        sensitivity = sensitivity_map.get(risk_level, ActionSensitivity.MEDIUM)
        
        # Create approval request
        approval = ApprovalRequest(
            id=str(uuid.uuid4()),
            agent_name=agent_name,
            action_type=action_type,
            action_summary=action_summary,
            payload=json.dumps(payload),
            risk_score=risk_assessment["adjusted_score"],
            sensitivity=sensitivity,
            resource_type=resource_type,
            resource_id=resource_id,
            requester_id=user_id,
            requester_name=requester_name,
            status=ApprovalStatus.PENDING,
            is_reversible=not payload.get("irreversible", False),
            impact_summary=f"Risk Level: {risk_level.upper()} (Score: {risk_assessment['adjusted_score']}/100)"
        )
        
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        
        logger.info(f"Submitted action for approval: {action_type} (risk: {risk_assessment['adjusted_score']})")
        
        return {
            "approval_id": approval.id,
            "status": "pending",
            "risk_score": risk_assessment["adjusted_score"],
            "risk_level": risk_level,
            "message": f"Action requires approval. Risk score: {risk_assessment['adjusted_score']}/100"
        }
    
    async def execute_approved_action(self, approval_id: str) -> Dict[str, Any]:
        """
        Execute an action that has been approved.
        
        This method looks up the approval, validates it's approved,
        then executes the stored action.
        
        Args:
            approval_id: The approval request ID
        
        Returns:
            Execution result
        """
        from backend.app.models import ApprovalRequest, ApprovalStatus, AgentAuditLog
        
        approval = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.id == approval_id
        ).first()
        
        if not approval:
            return {"success": False, "error": "Approval not found"}
        
        if approval.status != ApprovalStatus.APPROVED:
            return {"success": False, "error": f"Approval status is {approval.status.value}, not approved"}
        
        # Parse the stored payload
        try:
            payload = json.loads(approval.payload) if approval.payload else {}
        except json.JSONDecodeError:
            payload = {}
        
        # Execute based on action type
        result = await self._execute_action(
            approval.action_type,
            payload,
            approval.agent_name
        )
        
        # Log the execution
        audit_log = AgentAuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            actor_id=approval.resolved_by or approval.requester_id,
            actor_name="System (Post-Approval)",
            action=approval.action_type,
            resource_type=approval.resource_type or "unknown",
            resource_id=approval.resource_id,
            outcome="success" if result.get("success") else "failure",
            error_message=result.get("error"),
            reason=f"Approved action executed. Approval ID: {approval_id}"
        )
        self.db.add(audit_log)
        self.db.commit()
        
        return result
    
    async def _execute_action(
        self,
        action_type: str,
        payload: Dict[str, Any],
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Execute a specific action type.
        
        This is the dispatch point for actually performing approved actions.
        """
        # Map action types to handlers
        # In a full implementation, each action would have a specific handler
        
        logger.info(f"Executing approved action: {action_type} from {agent_name}")
        
        # For now, return success - actual implementations would go here
        # Example handlers would be:
        # - "delete_project" -> call project service to delete
        # - "create_meeting" -> call calendar service
        # - "send_external_email" -> call email service
        
        return {
            "success": True,
            "action_type": action_type,
            "agent_name": agent_name,
            "message": f"Action '{action_type}' executed successfully",
            "payload": payload
        }
    
    def get_pending_count(self, user_id: Optional[str] = None) -> int:
        """Get count of pending approvals."""
        from backend.app.models import ApprovalRequest, ApprovalStatus
        
        query = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.status == ApprovalStatus.PENDING
        )
        
        if user_id:
            query = query.filter(ApprovalRequest.requester_id == user_id)
        
        return query.count()


# Singleton getter for RiskGateService
def get_risk_gate_service(db: Session) -> RiskGateService:
    """Factory function to create RiskGateService instance."""
    return RiskGateService(db)
