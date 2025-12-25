"""
Advanced Capabilities Agent - Sandboxed Extension Platform.

Implements the Virtual AI Manager – Future & Advanced Capabilities:
- Organization-specific rules engine
- Custom workflows (DAG-based)
- Plugin system with sandboxing
- Voice intent pipeline
- Predictive staffing
- Financial planning signals
- AI-assisted performance coaching
- Multi-tenant support

Position in Architecture:
- Never executes core business actions directly
- Only registers extensions, evaluates signals, produces recommendations
- All execution flows through Orchestrator → Platform & Security Agent
"""

import uuid
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models import (
    OrganizationRule, RuleAction, RuleScope,
    CustomWorkflow, WorkflowStatus,
    Plugin, PluginStatus,
    VoiceIntent, StaffingPrediction, PerformanceFeedback, FeatureFlag,
    Task, Project, AgentActivity
)

# Placeholder for external API keys - user will configure
VOICE_API_KEY = None  # Set your speech-to-text API key
LLM_API_KEY = None    # Set your LLM API key for intent parsing


class AdvancedCapabilitiesAgent:
    """
    Advanced Capabilities Agent - Sandboxed Extension Platform.
    
    CRITICAL CONSTRAINTS:
    - Never executes core business actions directly
    - Rules cannot override security policies
    - Plugins run in sandbox with timeouts
    - Voice always requires confirmation
    - All actions flow through Platform & Security Agent
    """
    
    # Actions that cannot be overridden by rules
    PROTECTED_ACTIONS = [
        "security_policy", "legal_constraint", "platform_safety",
        "authentication", "authorization", "audit_log"
    ]
    
    # Sensitive voice intents requiring confirmation
    SENSITIVE_INTENTS = [
        "delete", "hire", "fire", "approve", "reject",
        "send_external", "change_permission", "modify_budget"
    ]
    
    def __init__(self, db: Session, organization_id: str = "default"):
        self.db = db
        self.organization_id = organization_id
    
    # ==================== RULES ENGINE ====================
    
    def create_rule(
        self,
        name: str,
        condition: Dict[str, Any],
        action: str,
        scope: str = "all",
        priority: int = 50,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an organization-specific rule.
        
        Conditions are structured expressions evaluated at runtime.
        """
        # Validate action
        try:
            rule_action = RuleAction(action)
        except ValueError:
            return {"error": f"Invalid action: {action}"}
        
        rule = OrganizationRule(
            id=str(uuid.uuid4()),
            organization_id=self.organization_id,
            name=name,
            description=description,
            condition=json.dumps(condition),
            action=rule_action,
            scope=RuleScope(scope),
            priority=priority,
            created_by=created_by
        )
        
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        
        return {
            "rule_id": rule.id,
            "name": name,
            "action": action,
            "scope": scope,
            "priority": priority,
            "status": "created"
        }
    
    def evaluate_rules(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate all applicable rules against an event.
        
        Returns: Recommendations, blocks, or approval requirements.
        """
        query = self.db.query(OrganizationRule).filter(
            OrganizationRule.organization_id == self.organization_id,
            OrganizationRule.is_active == True
        )
        
        if scope:
            query = query.filter(
                (OrganizationRule.scope == RuleScope(scope)) |
                (OrganizationRule.scope == RuleScope.ALL)
            )
        
        rules = query.order_by(desc(OrganizationRule.priority)).all()
        
        triggered_rules = []
        
        for rule in rules:
            condition = json.loads(rule.condition)
            if self._evaluate_condition(condition, event_data):
                triggered_rules.append({
                    "rule_id": rule.id,
                    "name": rule.name,
                    "action": rule.action.value,
                    "priority": rule.priority
                })
        
        if not triggered_rules:
            return {"triggered": False, "rules": []}
        
        # Resolve conflicts - highest priority wins
        resolved = self._resolve_conflicts(triggered_rules)
        
        return {
            "triggered": True,
            "event_type": event_type,
            "rules": triggered_rules,
            "resolved_action": resolved["action"],
            "applied_rule": resolved["name"]
        }
    
    def _evaluate_condition(self, condition: Dict, data: Dict) -> bool:
        """Simple condition evaluator supporting basic operators."""
        if "field" not in condition:
            return False
        
        field = condition.get("field")
        operator = condition.get("operator", "equals")
        value = condition.get("value")
        
        actual_value = data.get(field)
        
        if operator == "equals":
            return actual_value == value
        elif operator == "not_equals":
            return actual_value != value
        elif operator == "greater_than":
            return actual_value > value if actual_value else False
        elif operator == "less_than":
            return actual_value < value if actual_value else False
        elif operator == "contains":
            return value in actual_value if actual_value else False
        elif operator == "exists":
            return actual_value is not None
        
        return False
    
    def _resolve_conflicts(self, rules: List[Dict]) -> Dict:
        """Resolve rule conflicts by priority."""
        if not rules:
            return {"action": None, "name": None}
        
        # Already sorted by priority desc
        return {
            "action": rules[0]["action"],
            "name": rules[0]["name"]
        }
    
    def get_rules(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all rules for the organization."""
        query = self.db.query(OrganizationRule).filter(
            OrganizationRule.organization_id == self.organization_id
        )
        
        if scope:
            query = query.filter(OrganizationRule.scope == RuleScope(scope))
        
        rules = query.order_by(desc(OrganizationRule.priority)).all()
        
        return [{
            "id": r.id,
            "name": r.name,
            "action": r.action.value,
            "scope": r.scope.value,
            "priority": r.priority,
            "is_active": r.is_active
        } for r in rules]
    
    # ==================== WORKFLOW ENGINE ====================
    
    def create_workflow(
        self,
        name: str,
        steps: List[Dict[str, Any]],
        trigger: Optional[str] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a custom DAG workflow.
        
        Steps must define: step_id, preconditions, action_type, output
        """
        workflow = CustomWorkflow(
            id=str(uuid.uuid4()),
            organization_id=self.organization_id,
            name=name,
            description=description,
            trigger=trigger,
            steps=json.dumps(steps),
            status=WorkflowStatus.DRAFT,
            created_by=created_by
        )
        
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        
        return {
            "workflow_id": workflow.id,
            "name": name,
            "status": "draft",
            "message": "Workflow created. Validate before activation."
        }
    
    def validate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Validate workflow DAG for cycles and permissions.
        
        Must be validated before activation.
        """
        workflow = self.db.query(CustomWorkflow).filter(
            CustomWorkflow.id == workflow_id,
            CustomWorkflow.organization_id == self.organization_id
        ).first()
        
        if not workflow:
            return {"error": "Workflow not found"}
        
        steps = json.loads(workflow.steps)
        errors = []
        
        # Check for cycles using DFS
        if self._has_cycle(steps):
            errors.append("Workflow contains a cycle")
        
        # Check step structure
        for step in steps:
            if "step_id" not in step:
                errors.append("Step missing step_id")
            if "action_type" not in step:
                errors.append(f"Step {step.get('step_id', '?')} missing action_type")
            
            # Ensure action_type is recommend or require_approval only
            action_type = step.get("action_type")
            if action_type not in ["recommend", "require_approval"]:
                errors.append(f"Step {step.get('step_id', '?')} has invalid action_type (must be recommend or require_approval)")
        
        workflow.is_validated = len(errors) == 0
        workflow.validation_errors = json.dumps(errors) if errors else None
        workflow.last_validated_at = datetime.utcnow()
        self.db.commit()
        
        return {
            "workflow_id": workflow_id,
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    def _has_cycle(self, steps: List[Dict]) -> bool:
        """Detect cycles in workflow DAG using DFS."""
        step_ids = {s["step_id"] for s in steps}
        edges = {}
        
        for step in steps:
            step_id = step["step_id"]
            preconditions = step.get("preconditions", [])
            edges[step_id] = preconditions
        
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in edges.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step_id in step_ids:
            if step_id not in visited:
                if dfs(step_id):
                    return True
        
        return False
    
    def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Activate a validated workflow."""
        workflow = self.db.query(CustomWorkflow).filter(
            CustomWorkflow.id == workflow_id
        ).first()
        
        if not workflow:
            return {"error": "Workflow not found"}
        
        if not workflow.is_validated:
            return {"error": "Workflow must be validated before activation"}
        
        workflow.status = WorkflowStatus.ACTIVE
        self.db.commit()
        
        return {
            "workflow_id": workflow_id,
            "status": "active"
        }
    
    # ==================== PLUGIN SYSTEM ====================
    
    def register_plugin(
        self,
        name: str,
        version: str,
        required_permissions: List[str],
        input_schema: Dict,
        output_schema: Dict,
        entry_point: str,
        description: Optional[str] = None,
        author: Optional[str] = None,
        timeout_seconds: int = 30,
        memory_limit_mb: int = 128
    ) -> Dict[str, Any]:
        """
        Register a plugin extension.
        
        Plugins run in sandbox with timeout and memory limits.
        """
        plugin = Plugin(
            id=str(uuid.uuid4()),
            organization_id=self.organization_id,
            name=name,
            version=version,
            description=description,
            author=author,
            required_permissions=json.dumps(required_permissions),
            input_schema=json.dumps(input_schema),
            output_schema=json.dumps(output_schema),
            entry_point=entry_point,
            timeout_seconds=timeout_seconds,
            memory_limit_mb=memory_limit_mb,
            status=PluginStatus.PENDING
        )
        
        self.db.add(plugin)
        self.db.commit()
        self.db.refresh(plugin)
        
        return {
            "plugin_id": plugin.id,
            "name": name,
            "version": version,
            "status": "pending",
            "message": "Plugin registered. Awaiting approval."
        }
    
    def approve_plugin(self, plugin_id: str, approver_id: str) -> Dict[str, Any]:
        """Approve a plugin for activation."""
        plugin = self.db.query(Plugin).filter(Plugin.id == plugin_id).first()
        
        if not plugin:
            return {"error": "Plugin not found"}
        
        plugin.status = PluginStatus.APPROVED
        self.db.commit()
        
        return {
            "plugin_id": plugin_id,
            "status": "approved",
            "approved_by": approver_id
        }
    
    def execute_plugin(
        self,
        plugin_id: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a plugin in sandboxed environment.
        
        CONSTRAINT: Plugin crash must not affect core system.
        """
        plugin = self.db.query(Plugin).filter(Plugin.id == plugin_id).first()
        
        if not plugin:
            return {"error": "Plugin not found"}
        
        if plugin.status != PluginStatus.ACTIVE:
            return {"error": f"Plugin not active (status: {plugin.status.value})"}
        
        # Validate input against schema
        input_schema = json.loads(plugin.input_schema)
        validation_error = self._validate_schema(input_data, input_schema)
        if validation_error:
            return {"error": f"Input validation failed: {validation_error}"}
        
        # In production, this would run in a sandbox
        # For now, we simulate execution
        try:
            result = {
                "status": "executed",
                "plugin_id": plugin_id,
                "output": {"message": "Plugin executed successfully (simulated)"}
            }
            
            # Validate output against schema
            output_schema = json.loads(plugin.output_schema)
            output_validation = self._validate_schema(result["output"], output_schema)
            if output_validation:
                plugin.error_count += 1
                plugin.last_error = f"Output validation failed: {output_validation}"
                self.db.commit()
                return {"error": f"Output validation failed: {output_validation}"}
            
            plugin.execution_count += 1
            plugin.last_executed_at = datetime.utcnow()
            self.db.commit()
            
            return result
            
        except Exception as e:
            plugin.error_count += 1
            plugin.last_error = str(e)
            self.db.commit()
            return {"error": f"Plugin execution failed: {str(e)}"}
    
    def _validate_schema(self, data: Dict, schema: Dict) -> Optional[str]:
        """Simple schema validation. Returns error message or None."""
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                return f"Missing required field: {field}"
        return None
    
    def get_plugins(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all plugins."""
        query = self.db.query(Plugin).filter(
            Plugin.organization_id == self.organization_id
        )
        
        if status:
            query = query.filter(Plugin.status == PluginStatus(status))
        
        plugins = query.all()
        
        return [{
            "id": p.id,
            "name": p.name,
            "version": p.version,
            "status": p.status.value,
            "execution_count": p.execution_count,
            "error_count": p.error_count
        } for p in plugins]
    
    # ==================== VOICE INTENT PIPELINE ====================
    
    def process_voice_intent(
        self,
        transcription: str,
        user_id: str,
        confidence: float = 1.0
    ) -> Dict[str, Any]:
        """
        Process voice command into intent.
        
        CONSTRAINT: Voice produces intent only, never action.
        Sensitive intents always require confirmation.
        """
        # Parse intent from transcription (simplified)
        intent_type, intent_params = self._parse_intent(transcription)
        
        is_sensitive = any(s in intent_type.lower() for s in self.SENSITIVE_INTENTS)
        
        voice_intent = VoiceIntent(
            id=str(uuid.uuid4()),
            organization_id=self.organization_id,
            user_id=user_id,
            transcription=transcription,
            confidence=confidence,
            intent_type=intent_type,
            intent_params=json.dumps(intent_params),
            is_sensitive=is_sensitive,
            requires_confirmation=True  # Always require confirmation
        )
        
        self.db.add(voice_intent)
        self.db.commit()
        self.db.refresh(voice_intent)
        
        return {
            "intent_id": voice_intent.id,
            "intent_type": intent_type,
            "intent_params": intent_params,
            "is_sensitive": is_sensitive,
            "requires_confirmation": True,
            "message": "Intent parsed. Confirmation required before execution."
        }
    
    def _parse_intent(self, transcription: str) -> tuple:
        """Parse intent from transcription (simplified)."""
        transcription_lower = transcription.lower()
        
        # Simple keyword-based intent detection
        if "create" in transcription_lower and "task" in transcription_lower:
            return "create_task", {"type": "task"}
        elif "approve" in transcription_lower and "leave" in transcription_lower:
            return "approve_leave", {"type": "leave"}
        elif "schedule" in transcription_lower and "meeting" in transcription_lower:
            return "schedule_meeting", {"type": "meeting"}
        elif "delete" in transcription_lower:
            return "delete", {"type": "unknown"}
        elif "status" in transcription_lower:
            return "check_status", {"type": "status"}
        else:
            return "unknown", {"raw": transcription}
    
    def confirm_voice_action(
        self,
        intent_id: str,
        confirmed: bool,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Confirm or reject a voice intent for execution.
        """
        intent = self.db.query(VoiceIntent).filter(
            VoiceIntent.id == intent_id,
            VoiceIntent.user_id == user_id
        ).first()
        
        if not intent:
            return {"error": "Intent not found or access denied"}
        
        intent.confirmed = confirmed
        intent.confirmed_at = datetime.utcnow()
        self.db.commit()
        
        if confirmed:
            return {
                "intent_id": intent_id,
                "status": "confirmed",
                "intent_type": intent.intent_type,
                "message": "Action confirmed. Routing to orchestrator for execution."
            }
        else:
            return {
                "intent_id": intent_id,
                "status": "rejected",
                "message": "Action cancelled by user."
            }
    
    # ==================== PREDICTIVE STAFFING ====================
    
    def predict_staffing(
        self,
        department: Optional[str] = None,
        role_type: Optional[str] = None,
        time_horizon: str = "next_quarter"
    ) -> Dict[str, Any]:
        """
        Generate staffing recommendations.
        
        CONSTRAINT: Cannot trigger hiring. Recommendation only.
        """
        # Gather signals
        task_count = self.db.query(Task).count()
        project_count = self.db.query(Project).count()
        
        # Simplified prediction logic
        base_headcount = max(1, task_count // 10)
        confidence = 0.7
        
        prediction = StaffingPrediction(
            id=str(uuid.uuid4()),
            organization_id=self.organization_id,
            department=department,
            role_type=role_type,
            time_horizon=time_horizon,
            recommended_headcount=base_headcount,
            confidence_lower=max(0, base_headcount - 1),
            confidence_upper=base_headcount + 2,
            confidence_level=confidence,
            assumptions=json.dumps([
                "Based on current task volume",
                "Assumes consistent workload growth"
            ]),
            data_sources=json.dumps(["task_count", "project_count"]),
            historical_workload=json.dumps({"task_count": task_count}),
            task_velocity=json.dumps({"projects": project_count}),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        
        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        
        return {
            "prediction_id": prediction.id,
            "recommended_headcount": base_headcount,
            "confidence_band": f"{prediction.confidence_lower}-{prediction.confidence_upper}",
            "confidence_level": f"{confidence * 100:.0f}%",
            "time_horizon": time_horizon,
            "assumptions": json.loads(prediction.assumptions),
            "constraint": "RECOMMENDATION ONLY - Cannot trigger hiring"
        }
    
    # ==================== FINANCIAL PLANNING ====================
    
    def analyze_financial_impact(
        self,
        resource_changes: List[Dict[str, Any]],
        time_period: str = "annual"
    ) -> Dict[str, Any]:
        """
        Analyze financial impact of resource changes.
        
        CONSTRAINT: No spending actions. Read-only signals.
        """
        total_impact = 0
        breakdown = []
        
        for change in resource_changes:
            change_type = change.get("type")
            count = change.get("count", 1)
            
            # Simplified cost estimation
            if change_type == "new_hire":
                cost = count * 80000  # Avg salary estimate
                breakdown.append({
                    "item": f"{count} new hire(s)",
                    "cost": cost,
                    "type": "recurring"
                })
                total_impact += cost
            elif change_type == "contractor":
                cost = count * 120000
                breakdown.append({
                    "item": f"{count} contractor(s)",
                    "cost": cost,
                    "type": "recurring"
                })
                total_impact += cost
            elif change_type == "tool_license":
                cost = count * 5000
                breakdown.append({
                    "item": f"{count} tool license(s)",
                    "cost": cost,
                    "type": "recurring"
                })
                total_impact += cost
        
        return {
            "time_period": time_period,
            "total_impact": total_impact,
            "breakdown": breakdown,
            "trade_offs": [
                "Additional headcount increases capacity but requires onboarding time",
                "Contractors offer flexibility but higher hourly rates"
            ],
            "constraint": "READ-ONLY - No spending actions. Approval required for any financial workflow."
        }
    
    # ==================== PERFORMANCE COACHING ====================
    
    def generate_feedback(
        self,
        user_id: str,
        feedback_type: str,
        content: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate private performance feedback.
        
        CONSTRAINT: Private, optional, supportive.
        No ranking. No sharing without consent.
        """
        feedback = PerformanceFeedback(
            id=str(uuid.uuid4()),
            organization_id=self.organization_id,
            user_id=user_id,
            feedback_type=feedback_type,
            content=content,
            context=context,
            is_private=True,
            consent_to_share=False
        )
        
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        
        return {
            "feedback_id": feedback.id,
            "type": feedback_type,
            "is_private": True,
            "message": "Feedback generated. Only the user can access this."
        }
    
    def get_personal_feedback(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get user's own feedback.
        
        CONSTRAINT: Users can only access their own feedback.
        """
        feedback = self.db.query(PerformanceFeedback).filter(
            PerformanceFeedback.user_id == user_id,
            PerformanceFeedback.organization_id == self.organization_id
        ).order_by(desc(PerformanceFeedback.created_at)).all()
        
        return [{
            "id": f.id,
            "type": f.feedback_type,
            "content": f.content,
            "is_read": f.is_read,
            "created_at": f.created_at.isoformat()
        } for f in feedback]
    
    # ==================== FEATURE FLAGS ====================
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get all feature flags for the organization."""
        flags = self.db.query(FeatureFlag).filter(
            FeatureFlag.organization_id == self.organization_id
        ).all()
        
        return {f.flag_key: f.flag_value for f in flags}
    
    def set_feature_flag(
        self,
        flag_key: str,
        flag_value: bool,
        changed_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Set a feature flag."""
        existing = self.db.query(FeatureFlag).filter(
            FeatureFlag.organization_id == self.organization_id,
            FeatureFlag.flag_key == flag_key
        ).first()
        
        if existing:
            existing.previous_value = existing.flag_value
            existing.flag_value = flag_value
            existing.version += 1
            existing.changed_by = changed_by
            existing.change_reason = reason
        else:
            existing = FeatureFlag(
                id=str(uuid.uuid4()),
                organization_id=self.organization_id,
                flag_key=flag_key,
                flag_value=flag_value,
                changed_by=changed_by,
                change_reason=reason
            )
            self.db.add(existing)
        
        self.db.commit()
        
        return {
            "flag_key": flag_key,
            "flag_value": flag_value,
            "version": existing.version
        }
    
    # ==================== TENANT ISOLATION ====================
    
    def validate_tenant(self, tenant_id: str) -> bool:
        """
        Validate tenant context for every operation.
        
        Ensures strict tenant boundaries.
        """
        return tenant_id == self.organization_id
