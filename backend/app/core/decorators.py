"""
Decorators for VAM backend services.

Phase 4: Includes @log_activity for automatic audit logging.
"""

import uuid
import json
import functools
from datetime import datetime
from typing import Optional, Callable, Any

# Logging
try:
    from app.core.logging import logger
except ImportError:
    try:
        from backend.app.core.logging import logger
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)


def log_activity(action: str, resource_type: str):
    """
    Decorator to automatically log function calls to AuditLog.
    
    Usage:
        @log_activity(action="create", resource_type="task")
        async def create_task(user_id: str, db: Session, ...):
            ...
    
    The decorator extracts user_id and db from function arguments,
    logs before execution, executes the function, and logs the result.
    
    Args:
        action: The action being performed (create, update, delete, etc.)
        resource_type: Type of resource (task, project, user, etc.)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # Try to extract user_id and db from kwargs or args
            user_id = kwargs.get('user_id')
            db = kwargs.get('db')
            
            # If not in kwargs, try to find in args by name inspection
            if not user_id or not db:
                import inspect
                sig = inspect.signature(func)
                params = list(sig.parameters.keys())
                
                for i, (param_name, arg_value) in enumerate(zip(params, args)):
                    if param_name == 'user_id' and not user_id:
                        user_id = arg_value
                    elif param_name == 'db' and not db:
                        db = arg_value
            
            # Generate activity ID
            activity_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            
            # Log start (if we have db session)
            logger.info(f"[Activity:{activity_id}] Starting {action} on {resource_type}")
            
            result = None
            error_msg = None
            outcome = "success"
            
            try:
                # Execute the actual function
                result = await func(*args, **kwargs)
                
                # Check if result indicates failure
                if isinstance(result, dict) and result.get("error"):
                    outcome = "failure"
                    error_msg = result.get("error")
                
                return result
                
            except Exception as e:
                outcome = "failure"
                error_msg = str(e)
                logger.error(f"[Activity:{activity_id}] Error: {e}")
                raise
                
            finally:
                # Log completion
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.info(f"[Activity:{activity_id}] Completed {action} on {resource_type}: {outcome} ({duration_ms:.0f}ms)")
                
                # Save to AuditLog if we have a db session
                if db:
                    try:
                        from backend.app.models import AuditLog
                        
                        # Extract resource_id from result or kwargs
                        resource_id = None
                        if isinstance(result, dict):
                            resource_id = result.get('id') or result.get('task_id') or result.get('project_id')
                        if not resource_id:
                            resource_id = kwargs.get('resource_id') or kwargs.get('task_id') or kwargs.get('project_id')
                        
                        audit_log = AuditLog(
                            id=activity_id,
                            timestamp=start_time,
                            actor_id=user_id or "system",
                            action=action,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            outcome=outcome,
                            error_message=error_msg,
                            metadata=json.dumps({
                                "duration_ms": duration_ms,
                                "function": func.__name__
                            })
                        )
                        db.add(audit_log)
                        db.commit()
                    except Exception as log_error:
                        logger.warning(f"Failed to save audit log: {log_error}")
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # Sync version - simplified logging without async
            user_id = kwargs.get('user_id')
            db = kwargs.get('db')
            
            activity_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            
            logger.info(f"[Activity:{activity_id}] Starting {action} on {resource_type}")
            
            result = None
            error_msg = None
            outcome = "success"
            
            try:
                result = func(*args, **kwargs)
                
                if isinstance(result, dict) and result.get("error"):
                    outcome = "failure"
                    error_msg = result.get("error")
                
                return result
                
            except Exception as e:
                outcome = "failure"
                error_msg = str(e)
                logger.error(f"[Activity:{activity_id}] Error: {e}")
                raise
                
            finally:
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                logger.info(f"[Activity:{activity_id}] Completed {action} on {resource_type}: {outcome} ({duration_ms:.0f}ms)")
                
                if db:
                    try:
                        from backend.app.models import AuditLog
                        
                        resource_id = None
                        if isinstance(result, dict):
                            resource_id = result.get('id') or result.get('task_id') or result.get('project_id')
                        
                        audit_log = AuditLog(
                            id=activity_id,
                            timestamp=start_time,
                            actor_id=user_id or "system",
                            action=action,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            outcome=outcome,
                            error_message=error_msg,
                            metadata=json.dumps({
                                "duration_ms": duration_ms,
                                "function": func.__name__
                            })
                        )
                        db.add(audit_log)
                        db.commit()
                    except Exception as log_error:
                        logger.warning(f"Failed to save audit log: {log_error}")
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def require_approval(action_type: str, risk_threshold: int = 50):
    """
    Decorator to require human approval for high-risk actions.
    
    Usage:
        @require_approval(action_type="delete_project")
        async def delete_project(user_id: str, db: Session, project_id: str):
            ...
    
    If the action's risk score exceeds the threshold, the function
    will NOT execute. Instead, it returns an approval request.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            from backend.app.agents.risk import RiskGateService
            
            db = kwargs.get('db')
            user_id = kwargs.get('user_id')
            
            if not db or not user_id:
                # Can't gate without context - just execute
                return await func(*args, **kwargs)
            
            # Create risk gate and assess
            risk_gate = RiskGateService(db, approval_threshold=risk_threshold)
            risk_assessment = risk_gate.assess_risk(action_type, kwargs)
            
            if risk_assessment["requires_approval"]:
                # Submit for approval instead of executing
                result = await risk_gate.submit_for_approval(
                    user_id=user_id,
                    agent_name=func.__module__.split('.')[-1],
                    action_type=action_type,
                    action_summary=f"{func.__name__} requires approval",
                    payload=kwargs
                )
                return {
                    "requires_approval": True,
                    **result
                }
            
            # Low risk - execute directly
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
