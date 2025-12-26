"""
Execution Agent - Task Execution Monitoring and Control.

Implements:
- Task update processing
- Downstream impact analysis
- Execution decision logging
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.models import (
    Task, TaskStatus, TaskHistory, AgentActivity, Escalation
)
import uuid


class ExecutionAgent:
    """
    Execution Agent for monitoring and controlling task execution.
    Tracks progress, detects issues, and suggests interventions.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.stale_threshold_hours = 48
        self.blocked_threshold_hours = 24
    
    def process_task_update(
        self,
        task_id: str,
        update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a task status update and determine follow-up actions.
        
        Args:
            task_id: Task being updated
            update: Update details (status, progress, blockers)
        
        Returns:
            Processing result with any triggered actions
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        actions_triggered = []
        notifications = []
        
        # Process status change
        new_status = update.get("status")
        if new_status:
            old_status = task.status
            
            if new_status == "completed":
                # Check downstream tasks
                downstream = self.check_downstream_impact(task_id)
                if downstream["unblocked_tasks"]:
                    actions_triggered.append({
                        "type": "unblock",
                        "tasks": downstream["unblocked_tasks"]
                    })
                    for t in downstream["unblocked_tasks"]:
                        notifications.append(f"Task '{t['name']}' can now proceed")
            
            elif new_status == "blocked":
                # Log blocker and check if escalation needed
                if task.status != TaskStatus.BLOCKED:
                    actions_triggered.append({
                        "type": "blocker_detected",
                        "task_id": task_id,
                        "blocker_info": update.get("blockers")
                    })
        
        # Check for overdue
        if task.deadline and task.deadline < datetime.utcnow():
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                actions_triggered.append({
                    "type": "overdue_warning",
                    "task_id": task_id,
                    "days_overdue": (datetime.utcnow() - task.deadline).days
                })
        
        # Log the processing
        self._log_execution_decision(
            task_id=task_id,
            decision=f"Processed update: {json.dumps(update)}",
            actions=actions_triggered
        )
        
        return {
            "task_id": task_id,
            "processed_at": datetime.utcnow().isoformat(),
            "actions_triggered": actions_triggered,
            "notifications": notifications
        }
    
    def check_downstream_impact(self, task_id: str) -> Dict[str, Any]:
        """
        Analyze impact on tasks that depend on this task.
        
        Args:
            task_id: The task that was updated
        
        Returns:
            Impact analysis with affected tasks
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Find tasks that depend on this one
        from backend.app.models import TaskDependency
        
        dependent_tasks = self.db.query(Task).join(
            TaskDependency,
            TaskDependency.task_id == Task.id
        ).filter(
            TaskDependency.depends_on_id == task_id
        ).all()
        
        unblocked_tasks = []
        still_blocked_tasks = []
        
        for dep_task in dependent_tasks:
            # Check if all dependencies are now complete
            all_complete = True
            for d in dep_task.dependencies:
                dep_status = self.db.query(Task).filter(
                    Task.id == d.depends_on_id
                ).first()
                if dep_status and dep_status.status != TaskStatus.COMPLETED:
                    all_complete = False
                    break
            
            if all_complete and dep_task.status == TaskStatus.BLOCKED:
                unblocked_tasks.append({
                    "id": dep_task.id,
                    "name": dep_task.name,
                    "owner": dep_task.owner
                })
            elif not all_complete:
                still_blocked_tasks.append({
                    "id": dep_task.id,
                    "name": dep_task.name,
                    "owner": dep_task.owner
                })
        
        return {
            "source_task": {
                "id": task.id,
                "name": task.name,
                "status": task.status.value
            },
            "total_dependent_tasks": len(dependent_tasks),
            "unblocked_tasks": unblocked_tasks,
            "still_blocked_tasks": still_blocked_tasks
        }
    
    def detect_stale_tasks(self, threshold_hours: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Find tasks that haven't been updated recently.
        
        Args:
            threshold_hours: Hours without update to consider stale
        
        Returns:
            List of stale tasks with recommendations
        """
        threshold = threshold_hours or self.stale_threshold_hours
        cutoff = datetime.utcnow() - timedelta(hours=threshold)
        
        stale_tasks = self.db.query(Task).filter(
            Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]),
            Task.last_update_at < cutoff
        ).all()
        
        results = []
        for task in stale_tasks:
            hours_stale = (datetime.utcnow() - task.last_update_at).total_seconds() / 3600
            
            recommendation = "Request status update"
            if hours_stale > 72:
                recommendation = "Escalate to manager"
            elif hours_stale > 96:
                recommendation = "Consider reassignment"
            
            results.append({
                "id": task.id,
                "name": task.name,
                "owner": task.owner,
                "status": task.status.value,
                "hours_since_update": round(hours_stale, 1),
                "last_update": task.last_update_at.isoformat() if task.last_update_at else None,
                "recommendation": recommendation
            })
        
        return results
    
    def analyze_execution_health(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze overall execution health.
        
        Args:
            project_id: Optional project filter
        
        Returns:
            Health analysis with metrics and recommendations
        """
        query = self.db.query(Task).filter(
            Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED])
        )
        
        if project_id:
            query = query.filter(Task.project_id == project_id)
        
        active_tasks = query.all()
        
        if not active_tasks:
            return {
                "health": "good",
                "message": "No active tasks",
                "metrics": {}
            }
        
        now = datetime.utcnow()
        
        # Calculate metrics
        blocked = len([t for t in active_tasks if t.status == TaskStatus.BLOCKED])
        overdue = len([t for t in active_tasks if t.deadline and t.deadline < now])
        stale = len([t for t in active_tasks 
                     if t.last_update_at and (now - t.last_update_at).total_seconds() / 3600 > 48])
        
        total = len(active_tasks)
        blocked_rate = (blocked / total) * 100
        overdue_rate = (overdue / total) * 100
        stale_rate = (stale / total) * 100
        
        # Determine health
        if blocked_rate > 30 or overdue_rate > 20:
            health = "critical"
            message = "Execution is significantly impaired"
        elif blocked_rate > 15 or overdue_rate > 10 or stale_rate > 30:
            health = "at_risk"
            message = "Execution showing warning signs"
        else:
            health = "good"
            message = "Execution is on track"
        
        recommendations = []
        if blocked_rate > 10:
            recommendations.append("Focus on unblocking tasks - high blocker rate")
        if overdue_rate > 10:
            recommendations.append("Review and update overdue task deadlines")
        if stale_rate > 20:
            recommendations.append("Follow up on tasks without recent updates")
        
        return {
            "health": health,
            "message": message,
            "metrics": {
                "active_tasks": total,
                "blocked_tasks": blocked,
                "overdue_tasks": overdue,
                "stale_tasks": stale,
                "blocked_rate": round(blocked_rate, 1),
                "overdue_rate": round(overdue_rate, 1),
                "stale_rate": round(stale_rate, 1)
            },
            "recommendations": recommendations
        }
    
    def suggest_interventions(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Suggest interventions to improve execution.
        
        Returns:
            List of suggested interventions with priority
        """
        interventions = []
        
        # Check for stale tasks
        stale = self.detect_stale_tasks()
        for task in stale[:5]:  # Top 5
            interventions.append({
                "type": "nudge",
                "priority": "medium" if task["hours_since_update"] < 72 else "high",
                "task_id": task["id"],
                "task_name": task["name"],
                "owner": task["owner"],
                "action": f"Request update from {task['owner']}",
                "reason": f"No update for {task['hours_since_update']} hours"
            })
        
        # Check for blocked tasks
        blocked_tasks = self.db.query(Task).filter(
            Task.status == TaskStatus.BLOCKED
        ).all()
        
        for task in blocked_tasks[:5]:
            # Check how long blocked
            last_blocked = self.db.query(TaskHistory).filter(
                TaskHistory.task_id == task.id,
                TaskHistory.new_value == "blocked"
            ).order_by(TaskHistory.timestamp.desc()).first()
            
            if last_blocked:
                hours_blocked = (datetime.utcnow() - last_blocked.timestamp).total_seconds() / 3600
                if hours_blocked > self.blocked_threshold_hours:
                    interventions.append({
                        "type": "escalation",
                        "priority": "high",
                        "task_id": task.id,
                        "task_name": task.name,
                        "owner": task.owner,
                        "action": "Escalate blocker to project owner",
                        "reason": f"Blocked for {round(hours_blocked, 1)} hours"
                    })
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        interventions.sort(key=lambda x: priority_order.get(x["priority"], 2))
        
        return interventions
    
    def _log_execution_decision(
        self,
        task_id: str,
        decision: str,
        actions: List[Dict[str, Any]]
    ):
        """Log an execution decision."""
        activity = AgentActivity(
            id=str(uuid.uuid4()),
            agent_name="ExecutionAgent",
            activity_type="decision",
            message=decision,
            related_task_id=task_id,
            activity_metadata=json.dumps({"actions": actions})
        )
        self.db.add(activity)
        self.db.commit()
