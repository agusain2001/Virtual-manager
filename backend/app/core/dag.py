"""
DAG Manager - Core Logic Engine for Task Dependencies.

This module enforces the "Physics" of the project management world:
- Cycle Detection: Prevents circular dependencies
- Auto-Blocking: Blocks tasks with incomplete dependencies
- Auto-Unblocking: Unblocks tasks when dependencies complete

Rules:
1. A task cannot depend on itself
2. No circular chains (A -> B -> C -> A)
3. If Task B depends on Task A (incomplete), B must be BLOCKED
4. When A completes, B auto-unblocks if no other incomplete blockers
"""

from typing import List, Dict, Set, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from backend.app.models import Task, TaskDependency, TaskStatus


class DAGManager:
    """
    Implements the 'Task Dependency Graphs (DAGs)' requirement from the 
    Task, Project & Execution Prompt Spec.
    
    Ensures no circular dependencies and calculates blockage.
    Supports both static methods (for simple checks) and instance methods
    (when database operations are needed).
    """
    
    def __init__(self, db: Session = None):
        self.db = db

    # ==================== STATIC METHODS (Original) ====================

    @staticmethod
    def build_graph(tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Builds an adjacency list representation of the task graph.
        Key: Task ID, Value: List of Dependency Task IDs (Prerequisites)
        """
        graph = {}
        for task in tasks:
            deps = [d.depends_on_id for d in task.dependencies] if task.dependencies else []
            graph[task.id] = deps
        return graph

    @staticmethod
    def detect_cycles(tasks: List[Task], new_dependency: Optional[Tuple[str, str]] = None) -> bool:
        """
        Detects if a cycle exists in the task graph.
        Optionally checks a hypothetical new dependency (task_id, dependency_id).
        Returns True if a cycle is detected.
        """
        graph = DAGManager.build_graph(tasks)
        
        if new_dependency:
            task_id, dep_id = new_dependency
            if task_id not in graph:
                graph[task_id] = []
            graph[task_id].append(dep_id)

        visited = set()
        recursion_stack = set()

        def dfs(node):
            visited.add(node)
            recursion_stack.add(node)
            neighbors = graph.get(node, [])
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    return True

            recursion_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False

    @staticmethod
    def get_blocked_tasks(tasks: List[Task]) -> Set[str]:
        """
        Identifies tasks that are 'blocked' because their dependencies are not 'done'.
        Returns a set of Blocked Task IDs.
        """
        task_status_map = {t.id: t.status for t in tasks}
        blocked_ids = set()

        for task in tasks:
            if task.status == TaskStatus.COMPLETED:
                continue
            
            deps = [d.depends_on_id for d in task.dependencies] if task.dependencies else []
            for dep_id in deps:
                dep_status = task_status_map.get(dep_id)
                if not dep_status or dep_status != TaskStatus.COMPLETED:
                    blocked_ids.add(task.id)
                    break
        
        return blocked_ids

    @staticmethod
    def topological_sort(tasks: List[Task]) -> List[str]:
        """
        Returns a valid execution order for tasks.
        If A depends on B, B comes before A in the list.
        """
        graph = DAGManager.build_graph(tasks)
        visited = set()
        stack = []

        def dfs(node):
            visited.add(node)
            neighbors = graph.get(node, [])
            for neighbor in neighbors:
                if neighbor not in visited:
                    dfs(neighbor)
            stack.append(node)

        for node in graph:
            if node not in visited:
                dfs(node)
        
        return stack

    # ==================== INSTANCE METHODS (New - Require DB) ====================

    def add_dependency(self, blocker_id: str, blocked_id: str) -> Dict:
        """
        Add a dependency: blocked_id depends on blocker_id.
        
        Steps:
        1. Validates no cycle would be created
        2. Creates the dependency link
        3. Updates blocked task status if blocker is incomplete
        """
        if not self.db:
            return {"success": False, "error": "No database session"}
        
        # Self-reference check
        if blocker_id == blocked_id:
            return {
                "success": False,
                "error": "cycle_detected",
                "message": "Task cannot depend on itself"
            }
        
        # Verify both tasks exist
        blocker = self.db.query(Task).filter(Task.id == blocker_id).first()
        blocked = self.db.query(Task).filter(Task.id == blocked_id).first()
        
        if not blocker:
            return {"success": False, "error": "blocker_not_found"}
        if not blocked:
            return {"success": False, "error": "blocked_not_found"}
        
        # Check for existing dependency
        existing = self.db.query(TaskDependency).filter(
            TaskDependency.task_id == blocked_id,
            TaskDependency.depends_on_id == blocker_id
        ).first()
        
        if existing:
            return {"success": False, "error": "dependency_exists"}
        
        # Get all tasks in project for cycle detection
        tasks = self.db.query(Task).filter(Task.project_id == blocked.project_id).all()
        
        # Check for cycle
        if self.detect_cycles(tasks, (blocked_id, blocker_id)):
            return {
                "success": False,
                "error": "cycle_detected",
                "message": f"Adding this dependency would create a circular reference"
            }
        
        # Create dependency
        dependency = TaskDependency(
            id=str(uuid.uuid4()),
            task_id=blocked_id,
            depends_on_id=blocker_id
        )
        self.db.add(dependency)
        
        # Auto-block if blocker is not completed
        if blocker.status != TaskStatus.COMPLETED:
            blocked.status = TaskStatus.BLOCKED
        
        self.db.commit()
        
        return {
            "success": True,
            "blocker_id": blocker_id,
            "blocked_id": blocked_id,
            "blocked_status": blocked.status.value
        }

    def remove_dependency(self, blocker_id: str, blocked_id: str) -> Dict:
        """Remove a dependency and potentially unblock the task."""
        if not self.db:
            return {"success": False, "error": "No database session"}
        
        dependency = self.db.query(TaskDependency).filter(
            TaskDependency.task_id == blocked_id,
            TaskDependency.depends_on_id == blocker_id
        ).first()
        
        if not dependency:
            return {"success": False, "error": "dependency_not_found"}
        
        self.db.delete(dependency)
        
        # Check if blocked task can be unblocked
        blocked = self.db.query(Task).filter(Task.id == blocked_id).first()
        if blocked and blocked.status == TaskStatus.BLOCKED:
            self._try_unblock_task(blocked)
        
        self.db.commit()
        
        return {"success": True}

    def update_downstream_status(self, completed_task_id: str) -> Dict:
        """
        When a task is completed, check all tasks that depend on it
        and potentially unblock them.
        """
        if not self.db:
            return {"success": False, "error": "No database session"}
        
        # Find all tasks that depend on the completed task
        downstream_deps = self.db.query(TaskDependency).filter(
            TaskDependency.depends_on_id == completed_task_id
        ).all()
        
        unblocked_tasks = []
        
        for dep in downstream_deps:
            blocked_task = self.db.query(Task).filter(Task.id == dep.task_id).first()
            
            if blocked_task and blocked_task.status == TaskStatus.BLOCKED:
                if self._try_unblock_task(blocked_task):
                    unblocked_tasks.append({
                        "id": blocked_task.id,
                        "name": blocked_task.name,
                        "new_status": blocked_task.status.value
                    })
        
        self.db.commit()
        
        return {
            "completed_task_id": completed_task_id,
            "unblocked_count": len(unblocked_tasks),
            "unblocked_tasks": unblocked_tasks
        }

    def _try_unblock_task(self, task: Task) -> bool:
        """
        Try to unblock a task by checking if all its blockers are completed.
        Returns True if task was unblocked.
        """
        # Get all dependencies for this task
        dependencies = self.db.query(TaskDependency).filter(
            TaskDependency.task_id == task.id
        ).all()
        
        # Check if all blockers are completed
        for dep in dependencies:
            blocker = self.db.query(Task).filter(Task.id == dep.depends_on_id).first()
            if blocker and blocker.status != TaskStatus.COMPLETED:
                return False
        
        # All blockers complete - unblock the task
        task.status = TaskStatus.NOT_STARTED
        return True

    def validate_status_change(self, task_id: str, new_status: TaskStatus) -> Tuple[bool, Optional[str]]:
        """
        Validate if a status change is allowed.
        
        Rule: Cannot set to IN_PROGRESS or COMPLETED if task is BLOCKED
        """
        if not self.db:
            return False, "No database session"
        
        task = self.db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            return False, "Task not found"
        
        if task.status == TaskStatus.BLOCKED:
            if new_status in [TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED]:
                # Get incomplete blockers
                deps = self.db.query(TaskDependency).filter(
                    TaskDependency.task_id == task_id
                ).all()
                
                incomplete_blockers = []
                for dep in deps:
                    blocker = self.db.query(Task).filter(Task.id == dep.depends_on_id).first()
                    if blocker and blocker.status != TaskStatus.COMPLETED:
                        incomplete_blockers.append(blocker.name)
                
                return False, f"Cannot proceed: blocked by {', '.join(incomplete_blockers)}"
        
        return True, None

    def get_task_blockers(self, task_id: str) -> List[Dict]:
        """Get all tasks that are blocking a given task."""
        if not self.db:
            return []
        
        dependencies = self.db.query(TaskDependency).filter(
            TaskDependency.task_id == task_id
        ).all()
        
        blockers = []
        for dep in dependencies:
            blocker = self.db.query(Task).filter(Task.id == dep.depends_on_id).first()
            if blocker:
                blockers.append({
                    "id": blocker.id,
                    "name": blocker.name,
                    "status": blocker.status.value,
                    "is_complete": blocker.status == TaskStatus.COMPLETED
                })
        
        return blockers

    def get_downstream_tasks(self, task_id: str) -> List[Dict]:
        """Get all tasks that are waiting on a given task."""
        if not self.db:
            return []
        
        dependencies = self.db.query(TaskDependency).filter(
            TaskDependency.depends_on_id == task_id
        ).all()
        
        downstream = []
        for dep in dependencies:
            blocked = self.db.query(Task).filter(Task.id == dep.task_id).first()
            if blocked:
                downstream.append({
                    "id": blocked.id,
                    "name": blocked.name,
                    "status": blocked.status.value
                })
        
        return downstream