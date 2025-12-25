"""
People Operations Agent - Resource Management and Workload Balancing.

Implements the Virtual AI Manager – People & Operations Agent:
- Employee profile management
- Skill matrix tracking
- Leave management with approval workflow
- Meeting scheduling and coordination
- Workload analysis and burnout detection
- Plan adjustment based on availability

Operating Principles:
1. People are not resources; treat availability as a constraint
2. Respect working hours, time zones, holidays, and approved leave
3. Avoid over-allocation and sustained overload
4. Always explain decisions that affect people
5. Ask for confirmation on sensitive people-related actions
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models import (
    Task, TaskStatus, TaskPriority, UserLeave, Holiday, AgentActivity,
    Employee, EmployeeSkill, Meeting, MeetingStatus, LeaveRequest, LeaveStatus,
    BurnoutIndicator, SkillProficiency
)


class PeopleOpsAgent:
    """
    People Operations Agent for resource and workload management.
    
    Operates as a people-focused operations manager.
    Responsible for managing human constraints, availability, leave,
    workload balance, and meeting coordination.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # ==================== EMPLOYEE PROFILE MANAGEMENT ====================
    
    def create_employee_profile(
        self,
        name: str,
        email: str,
        role: str,
        department: Optional[str] = None,
        timezone: str = "UTC",
        working_hours_start: str = "09:00",
        working_hours_end: str = "17:00",
        leave_balance: int = 20
    ) -> Employee:
        """
        Create a new employee profile.
        
        Profiles must include: name, role, skills, time zone, working hours,
        current workload, and leave balance.
        """
        employee = Employee(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            role=role,
            department=department,
            timezone=timezone,
            working_hours_start=working_hours_start,
            working_hours_end=working_hours_end,
            leave_balance=leave_balance
        )
        self.db.add(employee)
        
        self._log_activity(f"Created employee profile for {name} ({role})")
        
        self.db.commit()
        self.db.refresh(employee)
        return employee
    
    def get_employee_profile(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed employee profile."""
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            return None
        
        return self._format_employee_profile(employee)
    
    def get_all_employees(self, department: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all employee profiles."""
        query = self.db.query(Employee).filter(Employee.is_active == True)
        
        if department:
            query = query.filter(Employee.department == department)
        
        employees = query.all()
        return [self._format_employee_profile(e) for e in employees]
    
    def update_employee_profile(
        self,
        employee_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update employee profile. Profiles must be updated when assignments, leave, or role changes occur."""
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            return None
        
        allowed_fields = [
            'name', 'role', 'department', 'timezone', 
            'working_hours_start', 'working_hours_end', 'is_active'
        ]
        
        for field, value in updates.items():
            if field in allowed_fields and hasattr(employee, field):
                setattr(employee, field, value)
        
        self._log_activity(f"Updated profile for {employee.name}: {list(updates.keys())}")
        
        self.db.commit()
        self.db.refresh(employee)
        return self._format_employee_profile(employee)
    
    def _format_employee_profile(self, employee: Employee) -> Dict[str, Any]:
        """Format employee profile with all required fields."""
        return {
            "id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "role": employee.role,
            "department": employee.department,
            "timezone": employee.timezone,
            "working_hours": {
                "start": employee.working_hours_start,
                "end": employee.working_hours_end
            },
            "leave_balance": employee.leave_balance,
            "current_workload_hours": employee.current_workload_hours,
            "is_active": employee.is_active,
            "skills": [
                {
                    "name": s.skill_name,
                    "proficiency": s.proficiency.value,
                    "years_experience": s.years_experience,
                    "is_primary": s.is_primary
                }
                for s in employee.skills
            ]
        }
    
    # ==================== SKILL MATRIX MANAGEMENT ====================
    
    def update_employee_skills(
        self,
        employee_id: str,
        skills: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update skills for an employee.
        
        Skills are used to inform task assignment and identify skill gaps.
        """
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            return {"success": False, "error": "Employee not found"}
        
        # Clear existing skills
        self.db.query(EmployeeSkill).filter(
            EmployeeSkill.employee_id == employee_id
        ).delete()
        
        # Add new skills
        for skill_data in skills:
            proficiency = SkillProficiency(skill_data.get('proficiency', 'beginner'))
            skill = EmployeeSkill(
                id=str(uuid.uuid4()),
                employee_id=employee_id,
                skill_name=skill_data['name'],
                proficiency=proficiency,
                years_experience=skill_data.get('years_experience', 0),
                is_primary=skill_data.get('is_primary', False)
            )
            self.db.add(skill)
        
        self._log_activity(f"Updated skills for {employee.name}: {[s['name'] for s in skills]}")
        
        self.db.commit()
        return {"success": True, "skills_updated": len(skills)}
    
    def get_skill_matrix(self) -> Dict[str, Any]:
        """
        Get skill coverage summary across the team.
        
        Returns skill matrix with proficiency levels per person.
        """
        employees = self.db.query(Employee).filter(Employee.is_active == True).all()
        
        skill_matrix = {}
        all_skills = set()
        
        for employee in employees:
            for skill in employee.skills:
                all_skills.add(skill.skill_name)
                if skill.skill_name not in skill_matrix:
                    skill_matrix[skill.skill_name] = []
                skill_matrix[skill.skill_name].append({
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "proficiency": skill.proficiency.value,
                    "years_experience": skill.years_experience
                })
        
        # Calculate coverage stats
        coverage_summary = {}
        for skill_name, holders in skill_matrix.items():
            expert_count = sum(1 for h in holders if h['proficiency'] == 'expert')
            intermediate_count = sum(1 for h in holders if h['proficiency'] == 'intermediate')
            beginner_count = sum(1 for h in holders if h['proficiency'] == 'beginner')
            
            coverage_summary[skill_name] = {
                "total_holders": len(holders),
                "expert_count": expert_count,
                "intermediate_count": intermediate_count,
                "beginner_count": beginner_count,
                "is_single_point_of_failure": expert_count == 1 and intermediate_count == 0
            }
        
        return {
            "skills": list(all_skills),
            "matrix": skill_matrix,
            "coverage_summary": coverage_summary
        }
    
    def identify_skill_gaps(self, required_skills: List[str]) -> Dict[str, Any]:
        """
        Identify skill gaps when planning work.
        
        Returns gaps with recommendations for addressing them.
        """
        skill_matrix = self.get_skill_matrix()
        available_skills = set(skill_matrix['skills'])
        required_set = set(required_skills)
        
        missing = required_set - available_skills
        weak = []
        adequate = []
        
        for skill in required_set.intersection(available_skills):
            summary = skill_matrix['coverage_summary'][skill]
            if summary['expert_count'] == 0:
                weak.append({
                    "skill": skill,
                    "reason": "No experts available",
                    "holders": summary['total_holders']
                })
            elif summary['is_single_point_of_failure']:
                weak.append({
                    "skill": skill,
                    "reason": "Single point of failure - only one expert",
                    "holders": summary['total_holders']
                })
            else:
                adequate.append(skill)
        
        recommendations = []
        if missing:
            recommendations.append(f"Consider hiring or training for: {', '.join(missing)}")
        if weak:
            for w in weak:
                recommendations.append(f"Upskill team in {w['skill']}: {w['reason']}")
        
        return {
            "required_skills": required_skills,
            "missing_skills": list(missing),
            "weak_coverage": weak,
            "adequate_coverage": adequate,
            "recommendations": recommendations
        }
    
    # ==================== WORKLOAD & BURNOUT MANAGEMENT ====================
    
    def analyze_workload(self, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze current workload distribution.
        
        Availability is determined by:
        - Contracted working hours
        - Time zone
        - Approved leave
        - Public holidays
        """
        query = self.db.query(Task).filter(
            Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.NOT_STARTED, TaskStatus.BLOCKED])
        )
        
        if user:
            query = query.filter(Task.owner == user)
            tasks = query.all()
            return self._analyze_user_workload(user, tasks)
        
        # Analyze all users
        tasks = query.all()
        workload_by_user = {}
        
        for task in tasks:
            if task.owner not in workload_by_user:
                workload_by_user[task.owner] = {
                    "tasks": [],
                    "total_estimated_hours": 0,
                    "critical_count": 0,
                    "blocked_count": 0
                }
            
            workload_by_user[task.owner]["tasks"].append({
                "id": task.id,
                "name": task.name,
                "priority": task.priority.value,
                "status": task.status.value,
                "deadline": task.deadline.isoformat() if task.deadline else None
            })
            workload_by_user[task.owner]["total_estimated_hours"] += task.estimated_hours or 4
            
            if task.priority == TaskPriority.CRITICAL:
                workload_by_user[task.owner]["critical_count"] += 1
            if task.status == TaskStatus.BLOCKED:
                workload_by_user[task.owner]["blocked_count"] += 1
        
        # Calculate statistics
        workloads = []
        for owner, data in workload_by_user.items():
            workloads.append({
                "user": owner,
                "task_count": len(data["tasks"]),
                "estimated_hours": data["total_estimated_hours"],
                "critical_tasks": data["critical_count"],
                "blocked_tasks": data["blocked_count"],
                "is_overloaded": data["total_estimated_hours"] > 40  # Weekly capacity
            })
        
        workloads.sort(key=lambda x: x["estimated_hours"], reverse=True)
        
        overloaded = [w for w in workloads if w["is_overloaded"]]
        underloaded = [w for w in workloads if w["estimated_hours"] < 20]
        
        recommendations = []
        if overloaded and underloaded:
            recommendations.append(
                f"Consider redistributing tasks from {overloaded[0]['user']} to {underloaded[0]['user']}"
            )
        
        return {
            "total_active_tasks": len(tasks),
            "team_members": len(workloads),
            "workload_distribution": workloads,
            "overloaded_members": [w["user"] for w in overloaded],
            "available_capacity": [w["user"] for w in underloaded],
            "recommendations": recommendations
        }
    
    def _analyze_user_workload(self, user: str, tasks: List[Task]) -> Dict[str, Any]:
        """Analyze workload for a specific user."""
        total_hours = sum(t.estimated_hours or 4 for t in tasks)
        
        by_priority = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": []
        }
        
        for task in tasks:
            by_priority[task.priority.value].append({
                "id": task.id,
                "name": task.name,
                "status": task.status.value,
                "deadline": task.deadline.isoformat() if task.deadline else None
            })
        
        # Check upcoming deadlines
        now = datetime.utcnow()
        week_ahead = now + timedelta(days=7)
        urgent = [t for t in tasks if t.deadline and now <= t.deadline <= week_ahead]
        
        return {
            "user": user,
            "total_tasks": len(tasks),
            "estimated_hours": total_hours,
            "capacity_used_percentage": min(100, int((total_hours / 40) * 100)),
            "by_priority": by_priority,
            "urgent_this_week": len(urgent),
            "is_overloaded": total_hours > 40,
            "recommendation": self._get_workload_recommendation(total_hours, len(tasks))
        }
    
    def _get_workload_recommendation(self, hours: int, task_count: int) -> str:
        """Generate workload recommendation."""
        if hours > 50:
            return "Severely overloaded - immediate task redistribution needed"
        elif hours > 40:
            return "At capacity - avoid adding new tasks"
        elif hours > 30:
            return "Good workload - maintaining productivity"
        elif hours > 15:
            return "Light workload - available for additional tasks"
        else:
            return "Underutilized - can take on significantly more work"
    
    def assess_burnout_risk(self, employee_id: str) -> Dict[str, Any]:
        """
        Assess burnout risk for an employee.
        
        Burnout risk indicators:
        - Sustained overload (>40h for multiple weeks)
        - Frequent deadline pressure
        - Lack of recovery time
        """
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            return {"error": "Employee not found"}
        
        # Get task history for the past 4 weeks
        four_weeks_ago = datetime.utcnow() - timedelta(weeks=4)
        tasks = self.db.query(Task).filter(
            Task.owner == employee.name,
            Task.updated_at >= four_weeks_ago
        ).all()
        
        # Calculate indicators
        total_hours = sum(t.estimated_hours or 4 for t in tasks)
        overload_weeks = max(0, (total_hours - 40 * 4) // 40)  # weeks exceeding capacity
        
        # Count tasks with tight deadlines
        deadline_pressure = sum(
            1 for t in tasks 
            if t.deadline and (t.deadline - t.created_at).days < 3
        )
        
        # Check for recent leave
        recent_leave = self.db.query(UserLeave).filter(
            UserLeave.user == employee.name,
            UserLeave.status == "approved",
            UserLeave.start_date >= four_weeks_ago
        ).first()
        
        days_since_break = 30 if not recent_leave else (datetime.utcnow() - recent_leave.end_date).days
        
        # Calculate risk score
        risk_score = min(100, 
            (overload_weeks * 20) + 
            (deadline_pressure * 5) + 
            (days_since_break // 7 * 5)
        )
        
        if risk_score >= 75:
            risk_level = "critical"
            recommendation = "Immediate intervention needed. Consider mandatory time off."
        elif risk_score >= 50:
            risk_level = "high"
            recommendation = "Reduce workload immediately. Redistribute tasks."
        elif risk_score >= 25:
            risk_level = "medium"
            recommendation = "Monitor closely. Avoid adding new tasks."
        else:
            risk_level = "low"
            recommendation = "Healthy workload. Continue current pace."
        
        # Record burnout indicator
        indicator = BurnoutIndicator(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            sustained_overload_weeks=overload_weeks,
            consecutive_deadline_pressure=deadline_pressure,
            days_since_last_break=days_since_break,
            risk_level=risk_level,
            risk_score=risk_score,
            recommendation=recommendation,
            is_flagged=risk_score >= 50
        )
        self.db.add(indicator)
        
        if risk_score >= 50:
            self._log_activity(
                f"Burnout risk ALERT for {employee.name}: {risk_level} ({risk_score}/100)"
            )
        
        self.db.commit()
        
        return {
            "employee_id": employee_id,
            "employee_name": employee.name,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "indicators": {
                "sustained_overload_weeks": overload_weeks,
                "deadline_pressure_events": deadline_pressure,
                "days_since_last_break": days_since_break
            },
            "recommendation": recommendation,
            "is_flagged": risk_score >= 50
        }
    
    def get_team_burnout_report(self) -> Dict[str, Any]:
        """Get burnout risk report for entire team."""
        employees = self.db.query(Employee).filter(Employee.is_active == True).all()
        
        assessments = []
        flagged = []
        
        for employee in employees:
            assessment = self.assess_burnout_risk(employee.id)
            if "error" not in assessment:
                assessments.append(assessment)
                if assessment.get("is_flagged"):
                    flagged.append(assessment)
        
        return {
            "assessment_date": datetime.utcnow().isoformat(),
            "total_employees": len(employees),
            "flagged_count": len(flagged),
            "flagged_employees": flagged,
            "all_assessments": assessments,
            "summary": {
                "critical": sum(1 for a in assessments if a['risk_level'] == 'critical'),
                "high": sum(1 for a in assessments if a['risk_level'] == 'high'),
                "medium": sum(1 for a in assessments if a['risk_level'] == 'medium'),
                "low": sum(1 for a in assessments if a['risk_level'] == 'low')
            }
        }
    
    # ==================== LEAVE MANAGEMENT ====================
    
    def submit_leave_request(
        self,
        employee_id: str,
        start_date: datetime,
        end_date: datetime,
        leave_type: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit a leave request.
        
        Validates request against leave balance and checks for critical dependencies.
        """
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            return {"success": False, "error": "Employee not found"}
        
        # Calculate days requested
        days = (end_date - start_date).days + 1
        
        # Validate against leave balance
        if days > employee.leave_balance:
            return {
                "success": False,
                "error": f"Insufficient leave balance. Requested: {days}, Available: {employee.leave_balance}"
            }
        
        # Check for critical dependencies during leave period
        impact = self._check_leave_impact(employee.name, start_date, end_date)
        
        leave_request = LeaveRequest(
            id=str(uuid.uuid4()),
            employee_id=employee_id,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
            days_requested=days,
            reason=reason,
            has_delivery_impact=impact["has_impact"],
            impact_description=impact.get("description")
        )
        self.db.add(leave_request)
        
        self._log_activity(
            f"Leave request submitted: {employee.name} for {days} days ({leave_type})"
        )
        
        self.db.commit()
        self.db.refresh(leave_request)
        
        return {
            "success": True,
            "leave_request_id": leave_request.id,
            "status": "pending",
            "days_requested": days,
            "leave_balance_after": employee.leave_balance - days,
            "impact_warning": impact if impact["has_impact"] else None
        }
    
    def _check_leave_impact(
        self, 
        user: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Check for delivery impact during leave period."""
        # Find tasks with deadlines during leave period
        affected_tasks = self.db.query(Task).filter(
            Task.owner == user,
            Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.NOT_STARTED]),
            Task.deadline >= start_date,
            Task.deadline <= end_date
        ).all()
        
        # Find critical tasks
        critical_tasks = [t for t in affected_tasks if t.priority == TaskPriority.CRITICAL]
        
        if not affected_tasks:
            return {"has_impact": False}
        
        return {
            "has_impact": True,
            "description": f"{len(affected_tasks)} task(s) have deadlines during leave period",
            "affected_tasks": [
                {"id": t.id, "name": t.name, "deadline": t.deadline.isoformat()}
                for t in affected_tasks
            ],
            "critical_count": len(critical_tasks),
            "suggested_action": "Review deadlines and assign coverage"
        }
    
    def approve_leave(
        self,
        leave_id: str,
        reviewed_by: str,
        rationale: str,
        coverage_plan: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a leave request with rationale.
        
        Approval logic: Default to approval unless strong business risk exists.
        All decisions must include rationale.
        """
        leave = self.db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
        if not leave:
            return {"success": False, "error": "Leave request not found"}
        
        if leave.status != LeaveStatus.PENDING:
            return {"success": False, "error": f"Leave already {leave.status.value}"}
        
        employee = self.db.query(Employee).filter(Employee.id == leave.employee_id).first()
        
        # Update leave request
        leave.status = LeaveStatus.APPROVED
        leave.reviewed_by = reviewed_by
        leave.reviewed_at = datetime.utcnow()
        leave.approval_rationale = rationale
        leave.coverage_plan = coverage_plan
        
        # Deduct from leave balance
        if employee:
            employee.leave_balance -= leave.days_requested
        
        self._log_activity(
            f"Leave APPROVED for {employee.name if employee else 'unknown'}: "
            f"{leave.days_requested} days. Rationale: {rationale}"
        )
        
        self.db.commit()
        
        return {
            "success": True,
            "status": "approved",
            "rationale": rationale,
            "remaining_leave_balance": employee.leave_balance if employee else None
        }
    
    def reject_leave(
        self,
        leave_id: str,
        reviewed_by: str,
        rationale: str,
        suggested_alternative: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reject a leave request with rationale and alternatives.
        
        If risk exists, suggest alternatives (date shift, temporary coverage).
        All decisions must include rationale.
        """
        leave = self.db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
        if not leave:
            return {"success": False, "error": "Leave request not found"}
        
        if leave.status != LeaveStatus.PENDING:
            return {"success": False, "error": f"Leave already {leave.status.value}"}
        
        employee = self.db.query(Employee).filter(Employee.id == leave.employee_id).first()
        
        # Update leave request
        leave.status = LeaveStatus.REJECTED
        leave.reviewed_by = reviewed_by
        leave.reviewed_at = datetime.utcnow()
        leave.approval_rationale = rationale
        leave.rejection_alternative = suggested_alternative
        
        self._log_activity(
            f"Leave REJECTED for {employee.name if employee else 'unknown'}: "
            f"Rationale: {rationale}"
        )
        
        self.db.commit()
        
        return {
            "success": True,
            "status": "rejected",
            "rationale": rationale,
            "suggested_alternative": suggested_alternative
        }
    
    def get_leave_requests(
        self,
        status: Optional[str] = None,
        employee_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get leave requests with optional filters."""
        query = self.db.query(LeaveRequest)
        
        if status:
            query = query.filter(LeaveRequest.status == LeaveStatus(status))
        if employee_id:
            query = query.filter(LeaveRequest.employee_id == employee_id)
        
        leaves = query.order_by(LeaveRequest.created_at.desc()).all()
        
        return [
            {
                "id": l.id,
                "employee_id": l.employee_id,
                "start_date": l.start_date.isoformat(),
                "end_date": l.end_date.isoformat(),
                "leave_type": l.leave_type,
                "days_requested": l.days_requested,
                "status": l.status.value,
                "reason": l.reason,
                "has_delivery_impact": l.has_delivery_impact,
                "reviewed_by": l.reviewed_by,
                "rationale": l.approval_rationale
            }
            for l in leaves
        ]
    
    # ==================== MEETING & CALENDAR MANAGEMENT ====================
    
    def schedule_meeting(
        self,
        title: str,
        organizer: str,
        participant_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Schedule a meeting.
        
        Meeting scheduling logic:
        - Check participant availability
        - Respect working hours and time zones
        - Avoid back-to-back overload
        """
        # Check for conflicts
        conflicts = self._detect_conflicts(participant_ids, start_time, end_time)
        
        if conflicts["has_conflicts"]:
            return {
                "success": False,
                "error": "Scheduling conflicts detected",
                "conflicts": conflicts["details"],
                "suggested_times": self.suggest_meeting_times(
                    participant_ids, 
                    int((end_time - start_time).total_seconds() / 60)
                )
            }
        
        # Check working hours
        working_hours_issues = self._check_working_hours(participant_ids, start_time, end_time)
        if working_hours_issues:
            return {
                "success": False,
                "error": "Meeting outside working hours for some participants",
                "issues": working_hours_issues
            }
        
        meeting = Meeting(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            organizer=organizer,
            start_time=start_time,
            end_time=end_time,
            location=location
        )
        self.db.add(meeting)
        
        # Add participants
        for emp_id in participant_ids:
            employee = self.db.query(Employee).filter(Employee.id == emp_id).first()
            if employee:
                meeting.participants.append(employee)
        
        self._log_activity(f"Meeting scheduled: {title} with {len(participant_ids)} participants")
        
        self.db.commit()
        self.db.refresh(meeting)
        
        return {
            "success": True,
            "meeting_id": meeting.id,
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "participant_count": len(participant_ids)
        }
    
    def _detect_conflicts(
        self,
        participant_ids: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Detect calendar conflicts for participants."""
        conflicts = []
        
        for emp_id in participant_ids:
            employee = self.db.query(Employee).filter(Employee.id == emp_id).first()
            if not employee:
                continue
            
            # Check existing meetings
            overlapping = self.db.query(Meeting).filter(
                Meeting.participants.any(Employee.id == emp_id),
                Meeting.status == MeetingStatus.SCHEDULED,
                Meeting.start_time < end_time,
                Meeting.end_time > start_time
            ).all()
            
            for m in overlapping:
                conflicts.append({
                    "employee_id": emp_id,
                    "employee_name": employee.name,
                    "conflicting_meeting": m.title,
                    "meeting_time": f"{m.start_time.isoformat()} - {m.end_time.isoformat()}"
                })
            
            # Check leaves
            leaves = self.db.query(LeaveRequest).filter(
                LeaveRequest.employee_id == emp_id,
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.start_date <= end_time.date(),
                LeaveRequest.end_date >= start_time.date()
            ).all()
            
            for l in leaves:
                conflicts.append({
                    "employee_id": emp_id,
                    "employee_name": employee.name,
                    "reason": f"On leave ({l.leave_type})"
                })
        
        return {
            "has_conflicts": len(conflicts) > 0,
            "details": conflicts
        }
    
    def _check_working_hours(
        self,
        participant_ids: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Check if meeting time respects working hours."""
        issues = []
        
        for emp_id in participant_ids:
            employee = self.db.query(Employee).filter(Employee.id == emp_id).first()
            if not employee:
                continue
            
            meeting_start_hour = start_time.hour
            meeting_end_hour = end_time.hour
            
            work_start = int(employee.working_hours_start.split(':')[0])
            work_end = int(employee.working_hours_end.split(':')[0])
            
            if meeting_start_hour < work_start or meeting_end_hour > work_end:
                issues.append({
                    "employee_id": emp_id,
                    "employee_name": employee.name,
                    "working_hours": f"{employee.working_hours_start} - {employee.working_hours_end}",
                    "timezone": employee.timezone,
                    "issue": "Meeting outside working hours"
                })
        
        return issues
    
    def suggest_meeting_times(
        self,
        participant_ids: List[str],
        duration_minutes: int,
        search_days: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Suggest optimal meeting times.
        
        Optimal time selection considers:
        - Maximum participant overlap
        - Minimal disruption
        - Fair distribution across time zones
        """
        suggestions = []
        now = datetime.utcnow()
        
        # Get participant working hours
        employees = self.db.query(Employee).filter(Employee.id.in_(participant_ids)).all()
        
        if not employees:
            return []
        
        # Find common working hours
        common_start = max(int(e.working_hours_start.split(':')[0]) for e in employees)
        common_end = min(int(e.working_hours_end.split(':')[0]) for e in employees)
        
        if common_start >= common_end:
            return [{
                "warning": "No common working hours available",
                "recommendation": "Consider splitting into multiple meetings"
            }]
        
        # Generate time slots for next N days
        for day_offset in range(1, search_days + 1):
            check_date = now + timedelta(days=day_offset)
            
            # Skip weekends
            if check_date.weekday() >= 5:
                continue
            
            for hour in range(common_start, common_end):
                slot_start = check_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                
                if slot_end.hour > common_end:
                    continue
                
                conflicts = self._detect_conflicts(participant_ids, slot_start, slot_end)
                
                if not conflicts["has_conflicts"]:
                    suggestions.append({
                        "start_time": slot_start.isoformat(),
                        "end_time": slot_end.isoformat(),
                        "all_available": True,
                        "score": 100 - day_offset * 10 - (hour - common_start) * 2  # Prefer sooner
                    })
                    
                    if len(suggestions) >= 5:
                        break
            
            if len(suggestions) >= 5:
                break
        
        # Sort by score
        suggestions.sort(key=lambda x: x.get('score', 0), reverse=True)
        return suggestions[:5]
    
    def create_agenda(
        self,
        meeting_id: str,
        related_task_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate agenda for a meeting.
        
        Agenda generation:
        - Derive agenda items from related tasks and goals
        - Keep agendas concise and outcome-focused
        """
        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return {"error": "Meeting not found"}
        
        agenda_items = []
        
        # Add standard opening
        agenda_items.append("1. Welcome and introductions (2 min)")
        
        # If related tasks provided, add them
        if related_task_ids:
            tasks = self.db.query(Task).filter(Task.id.in_(related_task_ids)).all()
            for i, task in enumerate(tasks, start=2):
                status_note = f" [{task.status.value}]" if task.status != TaskStatus.NOT_STARTED else ""
                agenda_items.append(f"{i}. {task.name}{status_note}")
        
        # Add closing items
        agenda_items.append(f"{len(agenda_items) + 1}. Action items and next steps (5 min)")
        agenda_items.append(f"{len(agenda_items) + 1}. Closing")
        
        agenda_text = "\n".join(agenda_items)
        meeting.agenda = agenda_text
        
        self.db.commit()
        
        return {
            "meeting_id": meeting_id,
            "title": meeting.title,
            "agenda": agenda_text,
            "item_count": len(agenda_items)
        }
    
    def extract_action_items(
        self,
        meeting_id: str,
        meeting_notes: str
    ) -> Dict[str, Any]:
        """
        Extract action items from meeting notes.
        
        Post-meeting behavior:
        - Identify decisions and actions
        - Convert actions into tasks
        - Assign owners and deadlines
        """
        meeting = self.db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            return {"error": "Meeting not found"}
        
        meeting.meeting_notes = meeting_notes
        
        # Simple action item extraction based on keywords
        action_items = []
        lines = meeting_notes.split('\n')
        
        action_keywords = ['action:', 'todo:', 'task:', 'action item:', '@', 'will', 'needs to', 'should']
        
        for line in lines:
            line_lower = line.lower().strip()
            if any(kw in line_lower for kw in action_keywords):
                action_items.append({
                    "text": line.strip(),
                    "extracted_from": "meeting_notes",
                    "status": "pending"
                })
        
        # Store as JSON
        meeting.action_items = json.dumps(action_items)
        
        self._log_activity(
            f"Extracted {len(action_items)} action items from meeting: {meeting.title}"
        )
        
        self.db.commit()
        
        return {
            "meeting_id": meeting_id,
            "action_items": action_items,
            "item_count": len(action_items)
        }
    
    # ==================== PLAN ADJUSTMENT ====================
    
    def adjust_plans_for_availability(
        self,
        user: str,
        unavailable_start: datetime,
        unavailable_end: datetime,
        reason: str
    ) -> Dict[str, Any]:
        """
        Adjust plans when availability changes.
        
        When availability changes:
        - Recalculate timelines
        - Notify impacted stakeholders
        - Suggest replanning options
        """
        # Find affected tasks
        affected_tasks = self.db.query(Task).filter(
            Task.owner == user,
            Task.status.in_([TaskStatus.IN_PROGRESS, TaskStatus.NOT_STARTED]),
            Task.deadline > unavailable_start,
            Task.deadline <= unavailable_end + timedelta(days=7)  # Buffer
        ).all()
        
        adjustments = []
        impacted_projects = set()
        
        for task in affected_tasks:
            # Calculate new deadline (add unavailable days)
            unavailable_days = (unavailable_end - unavailable_start).days + 1
            original_deadline = task.deadline
            new_deadline = original_deadline + timedelta(days=unavailable_days)
            
            adjustments.append({
                "task_id": task.id,
                "task_name": task.name,
                "project_id": task.project_id,
                "original_deadline": original_deadline.isoformat() if original_deadline else None,
                "suggested_deadline": new_deadline.isoformat() if new_deadline else None,
                "days_shifted": unavailable_days,
                "options": [
                    {
                        "option": "extend_deadline",
                        "description": f"Extend deadline by {unavailable_days} days"
                    },
                    {
                        "option": "reassign",
                        "description": "Reassign to another team member"
                    },
                    {
                        "option": "prioritize",
                        "description": "Complete before absence with overtime"
                    }
                ]
            })
            impacted_projects.add(task.project_id)
        
        self._log_activity(
            f"Plan adjustment triggered for {user}: {len(adjustments)} tasks affected "
            f"due to {reason}"
        )
        
        self.db.commit()
        
        return {
            "user": user,
            "unavailable_period": {
                "start": unavailable_start.isoformat(),
                "end": unavailable_end.isoformat(),
                "reason": reason
            },
            "affected_tasks_count": len(adjustments),
            "impacted_projects": list(impacted_projects),
            "suggested_adjustments": adjustments,
            "requires_stakeholder_notification": len(adjustments) > 0
        }
    
    # ==================== ASSIGNMENT SUGGESTIONS ====================
    
    def suggest_assignment(
        self,
        task_name: str,
        required_skills: Optional[List[str]] = None,
        priority: str = "medium",
        estimated_hours: int = 8
    ) -> Dict[str, Any]:
        """
        Suggest the best person to assign a task to.
        
        Uses skills to inform task assignment while respecting workload constraints.
        """
        # Get current workload
        workload_analysis = self.analyze_workload()
        
        candidates = []
        for member in workload_analysis["workload_distribution"]:
            # Skip overloaded members for non-critical tasks
            if member["is_overloaded"] and priority != "critical":
                continue
            
            # Calculate capacity score (lower is better)
            capacity_score = member["estimated_hours"]
            
            # Adjust for blocked tasks (prefer people with fewer blockers)
            capacity_score += member["blocked_tasks"] * 4
            
            candidates.append({
                "user": member["user"],
                "capacity_score": capacity_score,
                "current_load": member["estimated_hours"],
                "task_count": member["task_count"]
            })
        
        if not candidates:
            return {
                "task_name": task_name,
                "suggestion": None,
                "reason": "All team members are overloaded",
                "alternatives": []
            }
        
        # Sort by capacity score
        candidates.sort(key=lambda x: x["capacity_score"])
        
        best = candidates[0]
        
        return {
            "task_name": task_name,
            "suggestion": best["user"],
            "reason": f"Best available capacity ({best['current_load']}h current load)",
            "new_load": best["current_load"] + estimated_hours,
            "alternatives": [c["user"] for c in candidates[1:3]]
        }
    
    # ==================== AVAILABILITY & CALENDAR ====================
    
    def check_availability(
        self,
        user: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Check if a user is available during a date range."""
        # Check leaves
        leaves = self.db.query(UserLeave).filter(
            UserLeave.user == user,
            UserLeave.status == "approved",
            UserLeave.start_date <= end_date,
            UserLeave.end_date >= start_date
        ).all()
        
        # Check holidays
        holidays = self.db.query(Holiday).filter(
            Holiday.date >= start_date,
            Holiday.date <= end_date
        ).all()
        
        unavailable_dates = []
        
        for leave in leaves:
            unavailable_dates.append({
                "type": "leave",
                "start": leave.start_date.isoformat(),
                "end": leave.end_date.isoformat(),
                "reason": leave.leave_type
            })
        
        for holiday in holidays:
            unavailable_dates.append({
                "type": "holiday",
                "date": holiday.date.isoformat(),
                "name": holiday.name
            })
        
        # Calculate available days
        total_days = (end_date - start_date).days + 1
        unavailable_days = len(set(
            d["date"] if d["type"] == "holiday" else d["start"] 
            for d in unavailable_dates
        ))
        
        return {
            "user": user,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "is_available": len(unavailable_dates) == 0,
            "unavailable_periods": unavailable_dates,
            "available_days": total_days - unavailable_days,
            "total_days": total_days
        }
    
    def get_team_calendar(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get team availability calendar."""
        # Get all leaves in period
        leaves = self.db.query(UserLeave).filter(
            UserLeave.status == "approved",
            UserLeave.start_date <= end_date,
            UserLeave.end_date >= start_date
        ).all()
        
        # Get holidays
        holidays = self.db.query(Holiday).filter(
            Holiday.date >= start_date,
            Holiday.date <= end_date
        ).all()
        
        # Get meetings
        meetings = self.db.query(Meeting).filter(
            Meeting.status == MeetingStatus.SCHEDULED,
            Meeting.start_time >= start_date,
            Meeting.end_time <= end_date
        ).all()
        
        calendar = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "holidays": [{
                "date": h.date.isoformat(),
                "name": h.name
            } for h in holidays],
            "leaves": [{
                "user": l.user,
                "start": l.start_date.isoformat(),
                "end": l.end_date.isoformat(),
                "type": l.leave_type
            } for l in leaves],
            "meetings": [{
                "id": m.id,
                "title": m.title,
                "start": m.start_time.isoformat(),
                "end": m.end_time.isoformat(),
                "organizer": m.organizer
            } for m in meetings]
        }
        
        return calendar
    
    def record_leave(
        self,
        user: str,
        start_date: datetime,
        end_date: datetime,
        leave_type: str = "vacation",
        status: str = "approved"
    ) -> UserLeave:
        """Record a user leave (legacy support)."""
        leave = UserLeave(
            id=str(uuid.uuid4()),
            user=user,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
            status=status
        )
        self.db.add(leave)
        
        self._log_activity(
            f"Recorded {leave_type} leave for {user}: {start_date.date()} to {end_date.date()}"
        )
        
        self.db.commit()
        self.db.refresh(leave)
        return leave
    
    # ==================== ACTIVITY LOGGING ====================
    
    def _log_activity(self, message: str):
        """Log people ops activity."""
        activity = AgentActivity(
            id=str(uuid.uuid4()),
            agent_name="PeopleOpsAgent",
            activity_type="action",
            message=message
        )
        self.db.add(activity)
