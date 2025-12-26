"""
GitHub Webhook Router - Handle Inbound GitHub Events.

Endpoints:
- POST /webhooks/github - Receive and process GitHub webhook events

Handles:
- issues.closed -> Mark task as completed
- issues.reopened -> Mark task as in_progress
- issues.edited -> Update task description
"""

import json
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models import Task, TaskStatus, TaskHistory, AgentActivity
from backend.app.services.github_service import github_service
import uuid

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = logging.getLogger(__name__)


async def verify_github_signature(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """Verify GitHub webhook signature."""
    body = await request.body()
    
    if x_hub_signature_256:
        is_valid = github_service.verify_webhook_signature(body, x_hub_signature_256)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    return body


def log_agent_activity(
    db: Session,
    agent_name: str,
    activity_type: str,
    message: str,
    task_id: Optional[str] = None,
    project_id: Optional[str] = None,
    metadata: Optional[dict] = None
):
    """Log agent activity for audit trail."""
    activity = AgentActivity(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        agent_name=agent_name,
        activity_type=activity_type,
        message=message,
        related_task_id=task_id,
        related_project_id=project_id,
        activity_metadata=json.dumps(metadata) if metadata else None
    )
    db.add(activity)


def create_task_history(
    db: Session,
    task_id: str,
    action: str,
    field_changed: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    trigger: str = "github_webhook",
    reason: Optional[str] = None
):
    """Create task history entry."""
    history = TaskHistory(
        id=str(uuid.uuid4()),
        task_id=task_id,
        timestamp=datetime.utcnow(),
        action=action,
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value,
        trigger=trigger,
        reason=reason
    )
    db.add(history)


@router.post("/github")
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None)
):
    """
    Handle GitHub webhook events.
    
    Supported events:
    - issues: Handle issue state changes
    - ping: Respond to webhook setup ping
    """
    # Verify signature
    body = await request.body()
    if x_hub_signature_256:
        is_valid = github_service.verify_webhook_signature(body, x_hub_signature_256)
        if not is_valid:
            logger.warning(f"Invalid webhook signature for delivery {x_github_delivery}")
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    event_type = x_github_event
    logger.info(f"Received GitHub webhook: {event_type} (delivery: {x_github_delivery})")
    
    # Handle ping event (webhook setup)
    if event_type == "ping":
        return {
            "message": "pong",
            "hook_id": payload.get("hook_id"),
            "zen": payload.get("zen")
        }
    
    # Handle issues event
    if event_type == "issues":
        return await handle_issue_event(db, payload)
    
    # Handle issue_comment event (optional)
    if event_type == "issue_comment":
        return await handle_issue_comment_event(db, payload)
    
    # Unknown event - just acknowledge
    return {"message": f"Event {event_type} received but not processed"}


async def handle_issue_event(db: Session, payload: dict) -> dict:
    """
    Handle issue events from GitHub.
    
    Actions:
    - closed: Mark linked task as completed
    - reopened: Mark linked task as in_progress
    - edited: Update task description
    """
    action = payload.get("action")
    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    
    issue_number = issue.get("number")
    repo_full_name = repo.get("full_name")
    
    if not issue_number or not repo_full_name:
        return {"message": "Missing issue number or repository"}
    
    # Find linked task
    task = db.query(Task).filter(
        Task.github_issue_number == issue_number,
        Task.github_repo == repo_full_name
    ).first()
    
    if not task:
        logger.info(f"No task linked to issue #{issue_number} in {repo_full_name}")
        return {"message": f"No task linked to issue #{issue_number}"}
    
    # Handle based on action
    if action == "closed":
        old_status = task.status.value if task.status else "unknown"
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.github_sync_status = "synced"
        task.github_synced_at = datetime.utcnow()
        task.last_update_at = datetime.utcnow()
        
        create_task_history(
            db=db,
            task_id=task.id,
            action="status_changed",
            field_changed="status",
            old_value=old_status,
            new_value="completed",
            reason=f"GitHub issue #{issue_number} was closed"
        )
        
        log_agent_activity(
            db=db,
            agent_name="GitHubWebhook",
            activity_type="sync",
            message=f"Task '{task.name}' marked completed (GitHub issue #{issue_number} closed)",
            task_id=task.id,
            project_id=task.project_id,
            metadata={
                "issue_number": issue_number,
                "repo": repo_full_name,
                "closed_by": issue.get("closed_by", {}).get("login")
            }
        )
        
        db.commit()
        logger.info(f"Task {task.id} marked completed via GitHub webhook")
        
        # Phase 3: Save task completion to long-term memory
        try:
            from backend.app.core.memory import memory_service
            import asyncio
            
            # Get user_id from task owner or project context
            user_id = task.owner  # Assuming owner is the user_id
            if user_id:
                await memory_service.store_memory(
                    user_id=user_id,
                    content=f"Completed task: {task.name}. Project: {task.project_id}. Issue #{issue_number} closed.",
                    memory_type="task_completion",
                    db=db,
                    source="github",
                    metadata={
                        "task_id": task.id,
                        "task_name": task.name,
                        "project_id": task.project_id,
                        "github_issue": issue_number,
                        "github_repo": repo_full_name,
                        "completed_at": datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"Saved task completion to memory for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to save task completion to memory: {e}")
        
        return {
            "message": "Task marked as completed",
            "task_id": task.id,
            "task_name": task.name
        }
    
    elif action == "reopened":
        old_status = task.status.value if task.status else "unknown"
        task.status = TaskStatus.IN_PROGRESS
        task.completed_at = None
        task.github_sync_status = "synced"
        task.github_synced_at = datetime.utcnow()
        task.last_update_at = datetime.utcnow()
        
        create_task_history(
            db=db,
            task_id=task.id,
            action="status_changed",
            field_changed="status",
            old_value=old_status,
            new_value="in_progress",
            reason=f"GitHub issue #{issue_number} was reopened"
        )
        
        log_agent_activity(
            db=db,
            agent_name="GitHubWebhook",
            activity_type="sync",
            message=f"Task '{task.name}' reopened (GitHub issue #{issue_number} reopened)",
            task_id=task.id,
            project_id=task.project_id
        )
        
        db.commit()
        logger.info(f"Task {task.id} reopened via GitHub webhook")
        
        return {
            "message": "Task reopened",
            "task_id": task.id,
            "task_name": task.name
        }
    
    elif action == "edited":
        changes = payload.get("changes", {})
        
        # Update title if changed
        if "title" in changes:
            old_title = changes["title"].get("from", "")
            task.name = issue.get("title", task.name)
            
            create_task_history(
                db=db,
                task_id=task.id,
                action="updated",
                field_changed="name",
                old_value=old_title,
                new_value=task.name,
                reason="Updated from GitHub issue title change"
            )
        
        # Update description if changed
        if "body" in changes:
            old_body = changes["body"].get("from", "")
            task.description = issue.get("body", task.description)
            
            create_task_history(
                db=db,
                task_id=task.id,
                action="updated",
                field_changed="description",
                old_value=old_body[:100] + "..." if len(old_body) > 100 else old_body,
                new_value=task.description[:100] + "..." if task.description and len(task.description) > 100 else task.description,
                reason="Updated from GitHub issue body change"
            )
        
        task.github_synced_at = datetime.utcnow()
        task.last_update_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Task {task.id} updated via GitHub webhook")
        
        return {
            "message": "Task updated",
            "task_id": task.id,
            "changes": list(changes.keys())
        }
    
    elif action == "labeled" or action == "unlabeled":
        # Could map labels to task priority in future
        return {"message": f"Label {action} event received"}
    
    elif action == "assigned" or action == "unassigned":
        # Could update task owner in future
        return {"message": f"Assignment {action} event received"}
    
    return {"message": f"Action {action} not handled"}


async def handle_issue_comment_event(db: Session, payload: dict) -> dict:
    """
    Handle issue comment events from GitHub.
    Could be used to sync comments or trigger actions.
    """
    action = payload.get("action")
    issue = payload.get("issue", {})
    comment = payload.get("comment", {})
    repo = payload.get("repository", {})
    
    issue_number = issue.get("number")
    repo_full_name = repo.get("full_name")
    
    # Find linked task
    task = db.query(Task).filter(
        Task.github_issue_number == issue_number,
        Task.github_repo == repo_full_name
    ).first()
    
    if not task:
        return {"message": f"No task linked to issue #{issue_number}"}
    
    if action == "created":
        # Log the comment activity
        log_agent_activity(
            db=db,
            agent_name="GitHubWebhook",
            activity_type="notification",
            message=f"New comment on task '{task.name}' from @{comment.get('user', {}).get('login')}",
            task_id=task.id,
            project_id=task.project_id,
            metadata={
                "issue_number": issue_number,
                "comment_id": comment.get("id"),
                "comment_author": comment.get("user", {}).get("login"),
                "comment_preview": comment.get("body", "")[:200]
            }
        )
        db.commit()
        
        return {"message": "Comment event logged"}
    
    return {"message": f"Comment action {action} received"}


@router.get("/github/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    return {
        "status": "healthy",
        "endpoint": "/webhooks/github",
        "supported_events": ["ping", "issues", "issue_comment"]
    }
