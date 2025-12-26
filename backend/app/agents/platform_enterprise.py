"""
Platform & Enterprise Agent - Security, Access Control, and Reliability.

Implements the Virtual AI Manager – Platform & Enterprise Agent:
- Tool permission validation
- Role-based access control (RBAC)
- Approval workflows for sensitive actions
- Comprehensive audit logging
- State management with rollback
- Idempotent operation handling
- Retry and recovery logic

Operating Principles:
1. No action without authorization
2. No tool call without validation
3. No irreversible action without approval
4. Everything must be observable and auditable
5. Fail safely and recover predictably
"""

import uuid
import json
import hashlib
import time
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy.orm import Session
from sqlalchemy import desc
from backend.app.models import (
    User, UserRole, AgentAuditLog, ApprovalRequest, ApprovalStatus,
    SystemState, OperationLock, OperationStatus, ActionSensitivity,
    AgentActivity
)

# Configuration - API keys placeholder (user will fill these)
EXTERNAL_API_KEY = None  # Set your API key here
WEBHOOK_SECRET = None  # Set your webhook secret here


class PlatformEnterpriseAgent:
    """
    Platform & Enterprise Agent for security, access control, and reliability.
    
    Operates as a platform reliability engineer, security officer, and governance controller.
    Protects system integrity, enforces permissions, validates tool interactions,
    and ensures reliable execution at scale.
    
    CRITICAL: Always prefers safety, auditability, and correctness over speed or autonomy.
    """
    
    # Sensitive action types that require approval
    SENSITIVE_ACTIONS = {
        "delete_data": ActionSensitivity.CRITICAL,
        "send_external_communication": ActionSensitivity.HIGH,
        "hire_decision": ActionSensitivity.CRITICAL,
        "reject_candidate": ActionSensitivity.HIGH,
        "permission_change": ActionSensitivity.CRITICAL,
        "bulk_update": ActionSensitivity.HIGH,
        "export_data": ActionSensitivity.MEDIUM,
        "system_config_change": ActionSensitivity.CRITICAL,
    }
    
    # Role permission matrix
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: ["*"],  # Full access
        UserRole.MANAGER: [
            "read:*", "create:*", "update:*",
            "approve:leave", "approve:assignment",
            "manage:team", "view:reports"
        ],
        UserRole.CONTRIBUTOR: [
            "read:*", "create:task", "update:own_task",
            "create:comment", "update:own_profile"
        ],
        UserRole.VIEWER: [
            "read:project", "read:task", "read:report"
        ]
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.max_retries = 3
        self.retry_backoff_base = 2  # Exponential backoff base
    
    # ==================== RBAC & PERMISSIONS ====================
    
    def check_permission(
        self,
        user_id: str,
        permission: str,
        resource_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if user has required permission.
        
        Enforces least-privilege access and logs unauthorized attempts.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            self._log_audit(
                actor_id=user_id,
                action="permission_check",
                resource_type="permission",
                outcome="denied",
                reason="User not found"
            )
            return {"allowed": False, "reason": "User not found"}
        
        if not user.is_active:
            self._log_audit(
                actor_id=user_id,
                action="permission_check",
                resource_type="permission",
                outcome="denied",
                reason="User account inactive"
            )
            return {"allowed": False, "reason": "Account inactive"}
        
        # Check role permissions
        role_perms = self.ROLE_PERMISSIONS.get(user.role, [])
        
        # Admin has full access
        if "*" in role_perms:
            return {"allowed": True, "role": user.role.value}
        
        # Check specific permission
        if permission in role_perms:
            return {"allowed": True, "role": user.role.value}
        
        # Check wildcard permissions (e.g., "read:*")
        perm_category = permission.split(":")[0] if ":" in permission else permission
        if f"{perm_category}:*" in role_perms:
            return {"allowed": True, "role": user.role.value}
        
        # Check user-specific permissions
        user_perms = json.loads(user.permissions or "[]")
        if permission in user_perms:
            return {"allowed": True, "role": user.role.value, "via": "user_permission"}
        
        # Denied
        self._log_audit(
            actor_id=user_id,
            actor_name=user.name,
            actor_role=user.role.value,
            action="permission_check",
            resource_type="permission",
            resource_id=permission,
            outcome="denied",
            reason=f"Permission '{permission}' not granted to role '{user.role.value}'"
        )
        
        return {
            "allowed": False,
            "reason": f"Permission '{permission}' not granted",
            "user_role": user.role.value
        }
    
    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get all permissions for a user."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        role_perms = self.ROLE_PERMISSIONS.get(user.role, [])
        user_perms = json.loads(user.permissions or "[]")
        
        return {
            "user_id": user_id,
            "role": user.role.value,
            "role_permissions": role_perms,
            "user_permissions": user_perms,
            "is_admin": "*" in role_perms
        }
    
    def update_user_role(
        self,
        user_id: str,
        new_role: str,
        changed_by: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Update user role. Requires approval for privilege escalation.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
        
        old_role = user.role.value
        
        # Check if this is privilege escalation
        role_hierarchy = ["viewer", "contributor", "manager", "admin"]
        old_idx = role_hierarchy.index(old_role)
        new_idx = role_hierarchy.index(new_role)
        
        if new_idx > old_idx:
            # Privilege escalation - create approval request
            return self.create_approval_request(
                action_type="permission_change",
                resource_type="user",
                resource_id=user_id,
                action_summary=f"Escalate {user.name} from {old_role} to {new_role}",
                requester_id=changed_by,
                impact_summary=f"User will gain {new_role} permissions"
            )
        
        # Downgrade is allowed
        user.role = UserRole(new_role)
        
        self._log_audit(
            actor_id=changed_by,
            action="update_role",
            resource_type="user",
            resource_id=user_id,
            resource_name=user.name,
            changes=json.dumps({"role": {"from": old_role, "to": new_role}}),
            reason=reason,
            outcome="success"
        )
        
        self.db.commit()
        
        return {
            "user_id": user_id,
            "old_role": old_role,
            "new_role": new_role,
            "status": "completed"
        }
    
    # ==================== APPROVAL WORKFLOWS ====================
    
    def create_approval_request(
        self,
        action_type: str,
        resource_type: str,
        resource_id: str,
        action_summary: str,
        requester_id: str,
        impact_summary: Optional[str] = None,
        is_reversible: bool = True,
        expires_in_hours: int = 48
    ) -> Dict[str, Any]:
        """
        Create an approval request for sensitive actions.
        
        Routes sensitive actions through approval chains.
        """
        sensitivity = self.SENSITIVE_ACTIONS.get(action_type, ActionSensitivity.MEDIUM)
        
        requester = self.db.query(User).filter(User.id == requester_id).first()
        
        approval = ApprovalRequest(
            id=str(uuid.uuid4()),
            action_type=action_type,
            sensitivity=sensitivity,
            resource_type=resource_type,
            resource_id=resource_id,
            action_summary=action_summary,
            impact_summary=impact_summary,
            is_reversible=is_reversible,
            requester_id=requester_id,
            requester_name=requester.name if requester else "Unknown",
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
        )
        
        self.db.add(approval)
        
        self._log_audit(
            actor_id=requester_id,
            action="create_approval_request",
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=json.dumps({"action_type": action_type, "sensitivity": sensitivity.value}),
            outcome="success"
        )
        
        self.db.commit()
        self.db.refresh(approval)
        
        return {
            "approval_id": approval.id,
            "action_type": action_type,
            "sensitivity": sensitivity.value,
            "status": "pending",
            "expires_at": approval.expires_at.isoformat(),
            "message": "Action requires approval before execution"
        }
    
    def process_approval(
        self,
        approval_id: str,
        approver_id: str,
        approved: bool,
        reason: str
    ) -> Dict[str, Any]:
        """
        Process approval or rejection.
        
        Tracks approval status and prevents bypassing approvals.
        """
        approval = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.id == approval_id
        ).first()
        
        if not approval:
            return {"error": "Approval request not found"}
        
        if approval.status != ApprovalStatus.PENDING:
            return {"error": f"Approval already {approval.status.value}"}
        
        if approval.expires_at < datetime.utcnow():
            approval.status = ApprovalStatus.EXPIRED
            self.db.commit()
            return {"error": "Approval request has expired"}
        
        # Check approver has permission
        perm_check = self.check_permission(approver_id, f"approve:{approval.action_type}")
        if not perm_check.get("allowed"):
            return {"error": "Not authorized to approve this action"}
        
        approver = self.db.query(User).filter(User.id == approver_id).first()
        
        approval.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        approval.resolved_by = approver_id
        approval.resolved_at = datetime.utcnow()
        approval.resolution_reason = reason
        
        self._log_audit(
            actor_id=approver_id,
            actor_name=approver.name if approver else None,
            action="approve" if approved else "reject",
            resource_type="approval_request",
            resource_id=approval_id,
            reason=reason,
            outcome="success"
        )
        
        self.db.commit()
        
        return {
            "approval_id": approval_id,
            "status": approval.status.value,
            "resolved_by": approver.name if approver else approver_id,
            "action_type": approval.action_type,
            "can_proceed": approved
        }
    
    def get_pending_approvals(self, approver_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all pending approval requests."""
        query = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.status == ApprovalStatus.PENDING,
            ApprovalRequest.expires_at > datetime.utcnow()
        )
        
        approvals = query.order_by(desc(ApprovalRequest.requested_at)).all()
        
        return [{
            "id": a.id,
            "action_type": a.action_type,
            "action_summary": a.action_summary,
            "sensitivity": a.sensitivity.value,
            "requester_name": a.requester_name,
            "requested_at": a.requested_at.isoformat(),
            "expires_at": a.expires_at.isoformat(),
            "is_reversible": a.is_reversible
        } for a in approvals]
    
    # ==================== AUDIT LOGGING ====================
    
    def _log_audit(
        self,
        action: str,
        resource_type: str,
        outcome: str,
        actor_id: Optional[str] = None,
        actor_name: Optional[str] = None,
        actor_role: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        changes: Optional[str] = None,
        metadata: Optional[str] = None,
        reason: Optional[str] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Create immutable audit log entry.
        
        Logs every action, decision, and tool call with who, what, when, why.
        """
        log = AgentAuditLog(
            id=str(uuid.uuid4()),
            actor_id=actor_id or "system",
            actor_name=actor_name,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            changes=changes,
            audit_metadata=metadata,
            reason=reason,
            outcome=outcome,
            error_message=error_message,
            ip_address=ip_address
        )
        self.db.add(log)
    
    def get_audit_trail(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get audit trail with filters."""
        query = self.db.query(AgentAuditLog)
        
        if resource_type:
            query = query.filter(AgentAuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AgentAuditLog.resource_id == resource_id)
        if actor_id:
            query = query.filter(AgentAuditLog.actor_id == actor_id)
        
        logs = query.order_by(desc(AgentAuditLog.timestamp)).limit(limit).all()
        
        return [{
            "id": l.id,
            "timestamp": l.timestamp.isoformat(),
            "actor_id": l.actor_id,
            "actor_name": l.actor_name,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "outcome": l.outcome,
            "reason": l.reason
        } for l in logs]
    
    def log_action(
        self,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        reason: Optional[str] = None,
        changes: Optional[Dict] = None
    ) -> str:
        """Public method to log actions from other agents."""
        actor = self.db.query(User).filter(User.id == actor_id).first()
        
        self._log_audit(
            actor_id=actor_id,
            actor_name=actor.name if actor else None,
            actor_role=actor.role.value if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=json.dumps(changes) if changes else None,
            reason=reason,
            outcome="success"
        )
        self.db.commit()
        
        return "logged"
    
    # ==================== IDEMPOTENCY & RELIABILITY ====================
    
    def ensure_idempotent(
        self,
        operation_id: str,
        operation_type: str,
        actor_id: str
    ) -> Dict[str, Any]:
        """
        Ensure operation is idempotent.
        
        Uses unique operation identifiers to prevent duplication.
        Returns existing result if operation was already completed.
        """
        existing = self.db.query(OperationLock).filter(
            OperationLock.operation_id == operation_id
        ).first()
        
        if existing:
            if existing.status == OperationStatus.COMPLETED:
                return {
                    "is_duplicate": True,
                    "original_result": json.loads(existing.result) if existing.result else None,
                    "completed_at": existing.completed_at.isoformat() if existing.completed_at else None
                }
            elif existing.status == OperationStatus.IN_PROGRESS:
                return {
                    "is_duplicate": True,
                    "status": "in_progress",
                    "message": "Operation is currently being processed"
                }
        
        # Create lock
        lock = OperationLock(
            id=str(uuid.uuid4()),
            operation_id=operation_id,
            operation_type=operation_type,
            status=OperationStatus.IN_PROGRESS,
            actor_id=actor_id,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        self.db.add(lock)
        self.db.commit()
        
        return {
            "is_duplicate": False,
            "lock_id": lock.id,
            "operation_id": operation_id
        }
    
    def complete_operation(
        self,
        operation_id: str,
        result: Dict[str, Any],
        success: bool = True
    ):
        """Mark operation as completed."""
        lock = self.db.query(OperationLock).filter(
            OperationLock.operation_id == operation_id
        ).first()
        
        if lock:
            lock.status = OperationStatus.COMPLETED if success else OperationStatus.FAILED
            lock.result = json.dumps(result)
            lock.completed_at = datetime.utcnow()
            self.db.commit()
    
    def execute_with_retry(
        self,
        operation: Callable,
        *args,
        max_retries: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute operation with retry and exponential backoff.
        
        Distinguishes between recoverable and fatal errors.
        """
        retries = max_retries or self.max_retries
        last_error = None
        
        for attempt in range(retries):
            try:
                result = operation(*args, **kwargs)
                return {"success": True, "result": result, "attempts": attempt + 1}
            except Exception as e:
                last_error = str(e)
                
                # Check if error is recoverable
                if self._is_fatal_error(e):
                    return {
                        "success": False,
                        "error": last_error,
                        "fatal": True,
                        "attempts": attempt + 1
                    }
                
                # Exponential backoff
                if attempt < retries - 1:
                    wait_time = self.retry_backoff_base ** attempt
                    time.sleep(wait_time)
        
        return {
            "success": False,
            "error": last_error,
            "attempts": retries,
            "message": "Max retries exceeded"
        }
    
    def _is_fatal_error(self, error: Exception) -> bool:
        """Determine if error is fatal (not worth retrying)."""
        fatal_messages = [
            "permission denied",
            "unauthorized",
            "not found",
            "invalid",
            "forbidden"
        ]
        error_str = str(error).lower()
        return any(msg in error_str for msg in fatal_messages)
    
    # ==================== STATE MANAGEMENT ====================
    
    def save_state(
        self,
        key: str,
        value: Any,
        changed_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save system state with versioning.
        
        Maintains consistent system state and supports rollback.
        """
        existing = self.db.query(SystemState).filter(
            SystemState.key == key
        ).first()
        
        value_json = json.dumps(value)
        
        if existing:
            previous_value = existing.value
            previous_version = existing.version
            
            existing.previous_value = previous_value
            existing.value = value_json
            existing.version = existing.version + 1
            existing.changed_by = changed_by
            existing.change_reason = reason
            existing.is_rollback = False
            existing.updated_at = datetime.utcnow()
        else:
            existing = SystemState(
                id=str(uuid.uuid4()),
                key=key,
                value=value_json,
                version=1,
                changed_by=changed_by,
                change_reason=reason
            )
            self.db.add(existing)
            previous_version = 0
        
        self._log_audit(
            actor_id=changed_by,
            action="save_state",
            resource_type="system_state",
            resource_id=key,
            changes=json.dumps({"version": existing.version}),
            reason=reason,
            outcome="success"
        )
        
        self.db.commit()
        
        return {
            "key": key,
            "version": existing.version,
            "previous_version": previous_version,
            "status": "saved"
        }
    
    def rollback_state(
        self,
        key: str,
        rolled_back_by: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Rollback state to previous version.
        
        Restores last known good state.
        """
        state = self.db.query(SystemState).filter(SystemState.key == key).first()
        
        if not state:
            return {"error": "State not found"}
        
        if not state.previous_value:
            return {"error": "No previous version to rollback to"}
        
        current_version = state.version
        current_value = state.value
        
        state.value = state.previous_value
        state.previous_value = current_value
        state.version = state.version + 1
        state.is_rollback = True
        state.rolled_back_from_version = current_version
        state.changed_by = rolled_back_by
        state.change_reason = reason
        
        self._log_audit(
            actor_id=rolled_back_by,
            action="rollback_state",
            resource_type="system_state",
            resource_id=key,
            changes=json.dumps({
                "rolled_back_from": current_version,
                "to_version": state.version
            }),
            reason=reason,
            outcome="success"
        )
        
        self.db.commit()
        
        return {
            "key": key,
            "rolled_back_from_version": current_version,
            "new_version": state.version,
            "status": "rolled_back"
        }
    
    def get_state(self, key: str) -> Dict[str, Any]:
        """Get current state value."""
        state = self.db.query(SystemState).filter(SystemState.key == key).first()
        
        if not state:
            return {"error": "State not found"}
        
        return {
            "key": key,
            "value": json.loads(state.value),
            "version": state.version,
            "updated_at": state.updated_at.isoformat()
        }
    
    # ==================== SYSTEM HEALTH ====================
    
    def health_check(self) -> Dict[str, Any]:
        """
        System health check.
        
        Enables debugging and incident analysis.
        """
        checks = {}
        
        # Database connectivity
        try:
            self.db.execute("SELECT 1")
            checks["database"] = {"status": "healthy"}
        except Exception as e:
            checks["database"] = {"status": "unhealthy", "error": str(e)}
        
        # Check for expired approvals
        expired = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.status == ApprovalStatus.PENDING,
            ApprovalRequest.expires_at < datetime.utcnow()
        ).count()
        
        # Check for stale operation locks
        stale_locks = self.db.query(OperationLock).filter(
            OperationLock.status == OperationStatus.IN_PROGRESS,
            OperationLock.expires_at < datetime.utcnow()
        ).count()
        
        checks["approvals"] = {
            "expired_count": expired,
            "status": "warning" if expired > 0 else "healthy"
        }
        
        checks["operations"] = {
            "stale_locks": stale_locks,
            "status": "warning" if stale_locks > 0 else "healthy"
        }
        
        overall = "healthy"
        if any(c.get("status") == "unhealthy" for c in checks.values()):
            overall = "unhealthy"
        elif any(c.get("status") == "warning" for c in checks.values()):
            overall = "degraded"
        
        return {
            "status": overall,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(
        self,
        email: str,
        name: str,
        role: str = "viewer",
        created_by: str = "system"
    ) -> Dict[str, Any]:
        """Create a new user."""
        existing = self.db.query(User).filter(User.email == email).first()
        if existing:
            return {"error": "User with this email already exists"}
        
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            role=UserRole(role)
        )
        self.db.add(user)
        
        self._log_audit(
            actor_id=created_by,
            action="create_user",
            resource_type="user",
            resource_id=user.id,
            resource_name=name,
            outcome="success"
        )
        
        self.db.commit()
        self.db.refresh(user)
        
        return {
            "user_id": user.id,
            "email": email,
            "name": name,
            "role": role
        }
    
    def get_users(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all users."""
        query = self.db.query(User)
        if role:
            query = query.filter(User.role == UserRole(role))
        
        users = query.all()
        
        return [{
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role.value,
            "is_active": u.is_active,
            "last_login": u.last_login.isoformat() if u.last_login else None
        } for u in users]
    
    # ==================== MCP TOOL MANAGEMENT ====================
    
    def discover_and_register_tools(self, server_name: str) -> Dict[str, Any]:
        """
        Discover and register tools from an MCP server.
        
        Scans configured MCP Servers and registers available tools.
        """
        from backend.app.mcp.communication import discover_mcp_tools
        from backend.app.services.platform_service import register_mcp_tool
        
        tools = discover_mcp_tools(server_name)
        
        registered = []
        for tool in tools:
            result = register_mcp_tool(
                db=self.db,
                name=tool["name"],
                server_name=server_name,
                description=tool.get("description"),
                input_schema=tool.get("input_schema"),
                requires_approval=tool.get("requires_approval", False),
                sensitivity_level=tool.get("sensitivity_level", "low")
            )
            registered.append(result)
        
        self._log_audit(
            actor_id="system",
            action="discover_tools",
            resource_type="mcp_server",
            resource_id=server_name,
            metadata=json.dumps({"tools_found": len(tools)}),
            outcome="success"
        )
        self.db.commit()
        
        return {
            "server": server_name,
            "tools_discovered": len(tools),
            "registered": registered
        }
    
    def execute_mcp_tool(
        self,
        tool_name: str,
        server_name: str,
        parameters: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool with safety checks.
        
        Wraps unsafe tools with human confirmation gate.
        """
        from backend.app.models import MCPTool
        
        # Find tool registration
        tool = self.db.query(MCPTool).filter(
            MCPTool.name == tool_name,
            MCPTool.server_name == server_name,
            MCPTool.is_active == True
        ).first()
        
        if not tool:
            return {"error": "Tool not found or not active"}
        
        if not tool.is_available:
            return {"error": "Tool is currently unavailable"}
        
        # Check role access
        if tool.allowed_roles:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                allowed = json.loads(tool.allowed_roles)
                if user.role.value.lower() not in [r.lower() for r in allowed]:
                    return {"error": "User role not authorized for this tool"}
        
        # Check if approval required
        if tool.requires_approval:
            return self.create_approval_request(
                action_type=f"execute_tool:{tool_name}",
                resource_type="mcp_tool",
                resource_id=tool.id,
                action_summary=f"Execute {tool_name} on {server_name}",
                requester_id=user_id,
                impact_summary=f"Parameters: {json.dumps(parameters)}",
                is_reversible=tool.sensitivity_level != "critical"
            )
        
        # Execute tool
        from backend.app.mcp.communication import execute_mcp_tool
        
        try:
            result = execute_mcp_tool(
                tool_name=tool_name,
                server_name=server_name,
                parameters=parameters,
                user_id=user_id
            )
            
            # Update last health check
            tool.last_health_check = datetime.utcnow()
            tool.error_count = 0
            
            self._log_audit(
                actor_id=user_id,
                action="execute_tool",
                resource_type="mcp_tool",
                resource_id=tool.id,
                metadata=json.dumps({"tool": tool_name, "server": server_name}),
                outcome="success"
            )
            
            self.db.commit()
            return result
            
        except Exception as e:
            # Track errors for circuit breaker
            tool.error_count = (tool.error_count or 0) + 1
            
            # Auto-disable after 5 consecutive errors
            if tool.error_count >= 5:
                tool.is_available = False
                self._log_audit(
                    actor_id="system",
                    action="disable_tool",
                    resource_type="mcp_tool",
                    resource_id=tool.id,
                    reason="Auto-disabled due to repeated failures",
                    outcome="warning"
                )
            
            self.db.commit()
            return {"error": str(e), "tool_error_count": tool.error_count}
    
    def get_tool_health(self) -> Dict[str, Any]:
        """Get health status of all registered MCP tools."""
        from backend.app.models import MCPTool
        
        tools = self.db.query(MCPTool).all()
        
        healthy = 0
        degraded = 0
        unavailable = 0
        
        tool_status = []
        for tool in tools:
            if not tool.is_active:
                continue
            
            if not tool.is_available:
                status = "unavailable"
                unavailable += 1
            elif (tool.error_count or 0) > 0:
                status = "degraded"
                degraded += 1
            else:
                status = "healthy"
                healthy += 1
            
            tool_status.append({
                "name": tool.name,
                "server": tool.server_name,
                "status": status,
                "error_count": tool.error_count or 0,
                "last_check": tool.last_health_check.isoformat() if tool.last_health_check else None
            })
        
        return {
            "summary": {
                "healthy": healthy,
                "degraded": degraded,
                "unavailable": unavailable,
                "total": len(tool_status)
            },
            "tools": tool_status
        }

