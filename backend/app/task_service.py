from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import uuid
from backend.app.core.logging import logger
from backend.app.models import (
    Task, Project, TaskDependency, TaskHistory, TaskStatus, 
    TaskPriority, AgentActivity
)

class TaskService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_task(
        self,
        name: str,
        project_id: str,
        owner: str,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        deadline: Optional[datetime] = None,
        trigger: str = "user"
    ) -> Task:
        """Create a new task with validation and history logging"""
        
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
            owner=owner,
            priority=priority,
            deadline=deadline,
            status=TaskStatus.NOT_STARTED
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
        """Update task status with validation and downstream checks"""
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        old_status = task.status
        task.status = new_status
        task.updated_at = datetime.utcnow()
        
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
    
    def add_dependency(
        self,
        task_id: str,
        depends_on_id: str
    ) -> TaskDependency:
        """Add task dependency with circular dependency check"""
        
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
    
    def get_overdue_tasks(self) -> List[Task]:
        """Get all overdue tasks that are not completed or cancelled"""
        
        now = datetime.utcnow()
        return self.db.query(Task).filter(
            Task.deadline < now,
            Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED])
        ).all()
    
    def get_blocked_tasks(self) -> List[Task]:
        """Get all tasks in blocked status"""
        
        return self.db.query(Task).filter(
            Task.status == TaskStatus.BLOCKED
        ).all()
    
    def prioritize_tasks(self, project_id: str) -> List[Task]:
        """Get prioritized list of tasks for a project"""
        
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
            
            return -score  # Negative for descending sort
        
        tasks.sort(key=priority_score)
        return tasks
    
    def _has_circular_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """Check if adding dependency would create a cycle"""
        
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
        """Check and update status of tasks that depend on this task"""
        
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
                    self._log_agent_activity(
                        agent_name="ExecutionAgent",
                        activity_type="notification",
                        message=f"Task '{dep_task.name}' unblocked - all dependencies complete",
                        related_task_id=dep_task.id
                    )
    
    def _all_dependencies_complete(self, task_id: str) -> bool:
        """Check if all dependencies for a task are complete"""
        
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
        """Log task history entry"""
        
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
        """Log agent activity"""
        
        activity = AgentActivity(
            id=str(uuid.uuid4()),
            agent_name=agent_name,
            activity_type=activity_type,
            message=message,
            related_task_id=related_task_id,
            related_project_id=related_project_id
        )
        self.db.add(activity)