from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid
import json
from openai import OpenAI
import os
from backend.app.core.logging import logger
from backend.app.models import (
    Task, Project, TaskDependency, TaskHistory, TaskStatus, 
    TaskPriority, AgentActivity, Holiday, UserLeave
)


class TaskService:
    """
    Enhanced Task Service with full VAM capabilities.
    Implements: Task CRUD, prioritization, dependencies, reassignment, escalation.
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
    
    def create_task(
        self,
        name: str,
        project_id: str,
        owner: str,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        deadline: Optional[datetime] = None,
        milestone_id: Optional[str] = None,
        trigger: str = "user"
    ) -> Task:
        """Create a new task with validation and history logging."""
        
        # Validate project exists
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            description=description,
            project_id=project_id,
            milestone_id=milestone_id,
            owner=owner,
            priority=priority,
            deadline=deadline,
            status=TaskStatus.NOT_STARTED,
            last_update_at=datetime.utcnow()
        )
        
        self.db.add(task)
        
        # Log history
        self._log_history(
            task_id=task_id,
            action="created",
            trigger=trigger,
            reason=f"Task created in project {project.name}"
        )
        
        # Log agent activity
        self._log_agent_activity(
            agent_name="TaskManager",
            activity_type="action",
            message=f"Created task '{name}' assigned to {owner}",
            related_task_id=task_id,
            related_project_id=project_id
        )
        
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(f"Created task {task_id}: {name}")
        return task
    
    def update_task_status(
        self,
        task_id: str,
        new_status: TaskStatus,
        trigger: str = "user",
        reason: Optional[str] = None
    ) -> Task:
        """Update task status with validation and downstream checks."""
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # VALIDATION: Cannot set IN_PROGRESS or COMPLETED if BLOCKED
        if task.status == TaskStatus.BLOCKED:
            if new_status in [TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]:
                # Check if still has incomplete blockers
                if not self._all_dependencies_complete(task_id):
                    raise ValueError(f"Cannot proceed: task is blocked by incomplete dependencies")
        
        old_status = task.status
        task.status = new_status
        task.updated_at = datetime.utcnow()
        task.last_update_at = datetime.utcnow()
        
        if new_status == TaskStatus.COMPLETED:
            task.completed_at = datetime.utcnow()
        
        # Log history
        self._log_history(
            task_id=task_id,
            action="status_changed",
            field_changed="status",
            old_value=old_status.value,
            new_value=new_status.value,
            trigger=trigger,
            reason=reason or f"Status updated to {new_status.value}"
        )
        
        # Check downstream dependencies
        self._check_downstream_tasks(task_id)
        
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(f"Updated task {task_id} status: {old_status.value} -> {new_status.value}")
        return task
    
    def reassign_task(
        self,
        task_id: str,
        new_owner: str,
        reason: str,
        trigger: str = "user"
    ) -> Task:
        """Reassign task to a new owner with notification logging."""
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        old_owner = task.owner
        task.owner = new_owner
        task.updated_at = datetime.utcnow()
        
        # Log history
        self._log_history(
            task_id=task_id,
            action="reassigned",
            field_changed="owner",
            old_value=old_owner,
            new_value=new_owner,
            trigger=trigger,
            reason=reason
        )
        
        # Log notifications for both owners
        self._log_agent_activity(
            agent_name="TaskManager",
            activity_type="notification",
            message=f"Task '{task.name}' reassigned from {old_owner} to {new_owner}. Reason: {reason}",
            related_task_id=task_id
        )
        
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(f"Reassigned task {task_id} from {old_owner} to {new_owner}")
        return task
    
    def validate_deadline(
        self,
        task_id: str,
        proposed_deadline: datetime
    ) -> Dict[str, Any]:
        """
        Check deadline feasibility against:
        - Dependencies
        - Holidays
        - User leaves
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        issues = []
        warnings = []
        
        # Check if deadline is in the past
        if proposed_deadline < datetime.utcnow():
            issues.append("Deadline is in the past")
        
        # Check dependencies
        for dep in task.dependencies:
            dep_task = dep.depends_on
            if dep_task.deadline and dep_task.deadline > proposed_deadline:
                issues.append(f"Dependency '{dep_task.name}' has deadline after proposed: {dep_task.deadline.date()}")
            if dep_task.status != TaskStatus.COMPLETED:
                warnings.append(f"Dependency '{dep_task.name}' is not completed yet")
        
        # Check holidays
        holidays = self.db.query(Holiday).filter(
            Holiday.date >= datetime.utcnow(),
            Holiday.date <= proposed_deadline
        ).all()
        
        if holidays:
            warnings.append(f"{len(holidays)} holidays between now and deadline")
        
        # Check owner leaves
        leaves = self.db.query(UserLeave).filter(
            UserLeave.user == task.owner,
            UserLeave.status == "approved",
            UserLeave.start_date <= proposed_deadline,
            UserLeave.end_date >= datetime.utcnow()
        ).all()
        
        if leaves:
            for leave in leaves:
                warnings.append(f"Owner {task.owner} on leave {leave.start_date.date()} to {leave.end_date.date()}")
        
        return {
            "task_id": task_id,
            "proposed_deadline": proposed_deadline.isoformat(),
            "is_feasible": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    def extract_tasks_from_text(
        self,
        text: str,
        project_id: str,
        default_owner: Optional[str] = None
    ) -> List[Task]:
        """
        Use LLM to extract actionable tasks from meeting notes/goals.
        """
        if not self.llm_client:
            raise ValueError("OpenAI API key not configured")
        
        prompt = f"""
        Extract actionable tasks from the following text.
        Return a JSON array of tasks with these fields:
        - name: Short, clear task name
        - description: Detailed description
        - priority: critical, high, medium, or low
        - estimated_hours: Estimated hours to complete (integer)
        
        Text:
        {text}
        
        Return ONLY valid JSON array.
        """
        
        response = self.llm_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a task extraction assistant. Extract actionable items from text."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        try:
            result = json.loads(response.choices[0].message.content)
            tasks_data = result.get("tasks", result) if isinstance(result, dict) else result
            if not isinstance(tasks_data, list):
                tasks_data = [tasks_data]
        except (json.JSONDecodeError, KeyError):
            return []
        
        created_tasks = []
        for task_data in tasks_data:
            if not task_data.get("name"):
                continue
                
            priority = TaskPriority.MEDIUM
            if task_data.get("priority"):
                try:
                    priority = TaskPriority[task_data["priority"].upper()]
                except KeyError:
                    pass
            
            task = self.create_task(
                name=task_data["name"],
                description=task_data.get("description"),
                project_id=project_id,
                owner=default_owner or "Unassigned",
                priority=priority,
                trigger="agent"
            )
            
            if task_data.get("estimated_hours"):
                task.estimated_hours = int(task_data["estimated_hours"])
            
            created_tasks.append(task)
        
        self._log_agent_activity(
            agent_name="TaskManager",
            activity_type="action",
            message=f"Extracted {len(created_tasks)} tasks from text",
            related_project_id=project_id
        )
        
        self.db.commit()
        return created_tasks
    
    def add_dependency(
        self,
        task_id: str,
        depends_on_id: str
    ) -> TaskDependency:
        """Add task dependency with circular dependency check."""
        
        # Validate both tasks exist
        task = self.db.query(Task).filter(Task.id == task_id).first()
        depends_on = self.db.query(Task).filter(Task.id == depends_on_id).first()
        
        if not task or not depends_on:
            raise ValueError("One or both tasks not found")
        
        # Check for circular dependencies
        if self._has_circular_dependency(task_id, depends_on_id):
            raise ValueError("Circular dependency detected")
        
        dependency = TaskDependency(
            id=str(uuid.uuid4()),
            task_id=task_id,
            depends_on_id=depends_on_id
        )
        
        self.db.add(dependency)
        
        # AUTO-BLOCK: If blocker is not complete, block the dependent task
        if depends_on.status != TaskStatus.COMPLETED:
            task.status = TaskStatus.BLOCKED
            self._log_history(
                task_id=task_id,
                action="status_changed",
                field_changed="status",
                old_value=task.status.value,
                new_value=TaskStatus.BLOCKED.value,
                trigger="system",
                reason=f"Auto-blocked: waiting on dependency {depends_on.name}"
            )
        
        # Log history
        self._log_history(
            task_id=task_id,
            action="dependency_added",
            trigger="system",
            reason=f"Added dependency on task {depends_on.name}"
        )
        
        self.db.commit()
        logger.info(f"Added dependency: {task_id} depends on {depends_on_id}")
        
        return dependency
    
    def remove_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """Remove a task dependency."""
        dependency = self.db.query(TaskDependency).filter(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_id == depends_on_id
        ).first()
        
        if dependency:
            self.db.delete(dependency)
            self._log_history(
                task_id=task_id,
                action="dependency_removed",
                trigger="user",
                reason=f"Removed dependency on task {depends_on_id}"
            )
            self.db.commit()
            return True
        return False
    
    def get_overdue_tasks(self) -> List[Task]:
        """Get all overdue tasks that are not completed or cancelled."""
        
        now = datetime.utcnow()
        return self.db.query(Task).filter(
            Task.deadline < now,
            Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED])
        ).all()
    
    def get_blocked_tasks(self) -> List[Task]:
        """Get all tasks in blocked status."""
        
        return self.db.query(Task).filter(
            Task.status == TaskStatus.BLOCKED
        ).all()
    
    def prioritize_tasks(self, project_id: str) -> List[Task]:
        """Get prioritized list of tasks for a project."""
        
        tasks = self.db.query(Task).filter(
            Task.project_id == project_id,
            Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED])
        ).all()
        
        # Sort by: Critical first, then deadline urgency
        def priority_score(task):
            priority_weights = {
                TaskPriority.CRITICAL: 1000,
                TaskPriority.HIGH: 100,
                TaskPriority.MEDIUM: 10,
                TaskPriority.LOW: 1
            }
            
            score = priority_weights.get(task.priority, 0)
            
            # Add urgency based on deadline
            if task.deadline:
                days_until = (task.deadline - datetime.utcnow()).days
                if days_until < 0:
                    score += 10000  # Overdue
                elif days_until < 3:
                    score += 5000   # Very urgent
                elif days_until < 7:
                    score += 1000   # Urgent
            
            # Blocked tasks get penalty
            if task.status == TaskStatus.BLOCKED:
                score -= 500
            
            return -score  # Negative for descending sort
        
        tasks.sort(key=priority_score)
        return tasks
    
    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get full history of a task."""
        history = self.db.query(TaskHistory).filter(
            TaskHistory.task_id == task_id
        ).order_by(TaskHistory.timestamp.desc()).all()
        
        return [{
            "id": h.id,
            "timestamp": h.timestamp.isoformat(),
            "action": h.action,
            "field_changed": h.field_changed,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "trigger": h.trigger,
            "reason": h.reason
        } for h in history]
    
    def archive_task(self, task_id: str) -> bool:
        """Archive a completed or cancelled task."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        if task.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
            raise ValueError("Only completed or cancelled tasks can be archived")
        
        # In a real system, this would move to archive table
        # For now, we just log it
        self._log_agent_activity(
            agent_name="TaskManager",
            activity_type="action",
            message=f"Archived task '{task.name}'",
            related_task_id=task_id
        )
        
        self.db.commit()
        return True
    
    def _has_circular_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """Check if adding dependency would create a cycle."""
        
        visited = set()
        
        def dfs(current_id: str) -> bool:
            if current_id in visited:
                return True
            if current_id == task_id:
                return True
            
            visited.add(current_id)
            
            dependencies = self.db.query(TaskDependency).filter(
                TaskDependency.task_id == current_id
            ).all()
            
            for dep in dependencies:
                if dfs(dep.depends_on_id):
                    return True
            
            return False
        
        return dfs(depends_on_id)
    
    def _check_downstream_tasks(self, task_id: str):
        """Check and update status of tasks that depend on this task."""
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        
        # Find tasks that depend on this one
        dependent_tasks = self.db.query(Task).join(
            TaskDependency,
            TaskDependency.task_id == Task.id
        ).filter(
            TaskDependency.depends_on_id == task_id
        ).all()
        
        for dep_task in dependent_tasks:
            if task.status == TaskStatus.COMPLETED:
                # Check if all dependencies are complete
                all_deps_complete = self._all_dependencies_complete(dep_task.id)
                
                if all_deps_complete and dep_task.status == TaskStatus.BLOCKED:
                    # AUTO-UNBLOCK: Change status from BLOCKED to NOT_STARTED
                    dep_task.status = TaskStatus.NOT_STARTED
                    dep_task.updated_at = datetime.utcnow()
                    
                    self._log_history(
                        task_id=dep_task.id,
                        action="status_changed",
                        field_changed="status",
                        old_value=TaskStatus.BLOCKED.value,
                        new_value=TaskStatus.NOT_STARTED.value,
                        trigger="system",
                        reason="Auto-unblocked: all dependencies complete"
                    )
                    
                    self._log_agent_activity(
                        agent_name="ExecutionAgent",
                        activity_type="notification",
                        message=f"Task '{dep_task.name}' unblocked - all dependencies complete",
                        related_task_id=dep_task.id
                    )
    
    def _all_dependencies_complete(self, task_id: str) -> bool:
        """Check if all dependencies for a task are complete."""
        
        dependencies = self.db.query(TaskDependency).filter(
            TaskDependency.task_id == task_id
        ).all()
        
        for dep in dependencies:
            dep_task = self.db.query(Task).filter(Task.id == dep.depends_on_id).first()
            if dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    def _log_history(
        self,
        task_id: str,
        action: str,
        field_changed: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        trigger: str = "system",
        reason: Optional[str] = None
    ):
        """Log task history entry."""
        
        history = TaskHistory(
            id=str(uuid.uuid4()),
            task_id=task_id,
            action=action,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            trigger=trigger,
            reason=reason
        )
        self.db.add(history)
    
    def _log_agent_activity(
        self,
        agent_name: str,
        activity_type: str,
        message: str,
        related_task_id: Optional[str] = None,
        related_project_id: Optional[str] = None
    ):
        """Log agent activity."""
        
        activity = AgentActivity(
            id=str(uuid.uuid4()),
            agent_name=agent_name,
            activity_type=activity_type,
            message=message,
            related_task_id=related_task_id,
            related_project_id=related_project_id
        )
        self.db.add(activity)