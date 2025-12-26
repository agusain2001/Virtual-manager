# 🤖 VAM Agent System Documentation

This document connects the functional specifications to the codebase, explaining how the multi-agent system thinks, routes, and executes.

---

## 🧠 The Orchestrator (`backend/app/agents/orchestrator.py`)

The **Manager Orchestrator** is the root node of the LangGraph system. It acts as the "Prefrontal Cortex" of VAM.

- **Responsibility**: Interprets incoming intent from the user or environment signals and routes control to the specialized agent best suited to handle it.
- **Routing Logic**:
  - `intent: planning` -> **Planning Agent**
  - `intent: personnel/leave` -> **People Ops Agent**
  - `intent: hiring/growth` -> **Growth & Scaling Agent**
  - `intent: analytics/forecast` -> **Analytics & Automation Agent**
  - `intent: platform/security` -> **Platform & Enterprise Agent**
  - `intent: status/check` -> **Execution Agent**
  - `intent: notify` -> **Communication Agent**
  - `intent: strategy/risk` -> **Managerial Agent**
  - `intent: advanced/custom` -> **Advanced Capabilities Agent**

---

## 🕵️ Planning Agent (`backend/app/agents/planning.py`)

*The Strategist.*

- **Role**: Takes abstract goals and converts them into concrete Task Dependency Graphs (DAGs).
- **Capabilities**:
  - **Decomposition**: Breaks "Launch website" into "Design", "Frontend", "Backend", "Deploy".
  - **Estimation**: Uses historical data (Vector Memory) to estimate effort.
  - **Re-planning**: Triggered by the Execution Agent when deadlines slip.

---

## 👥 People Ops Agent (`backend/app/agents/people_ops.py`)

*The HR Manager.* (1,400+ lines)

- **Role**: Manages the human constraints of the system with capacity awareness.
- **Capabilities**:
  - **Leave Management**: Checks inputs against policy docs and calendar availability. **Requires rationale for all approvals/rejections.**
  - **Burnout Detection**: Monitors sustained overload (>40h for multiple weeks), deadline pressure, and days since last break.
  - **Skill Matrix**: Tracks employee skills and identifies gaps for project assignments.
  - **Meeting Scheduling**: Schedules meetings with conflict detection, time zone handling, and working hours validation.
  - **Availability Heatmap**: Uses `get_available_hours()` to show busy/free slots.
  - **Overload Detection**: `check_overload()` returns LOW/BALANCED/OVERLOADED status.

### Core Logic (`backend/app/core/availability.py`)
```python
get_available_hours(db, user_id, start_date, end_date) -> Dict
# Returns: total_working_hours, leave_hours, holiday_hours, meeting_hours, available_hours

check_overload(db, user_id) -> Dict
# Returns: status (LOW/BALANCED/OVERLOADED), utilization_percentage, recommendation
```

### Service Layer (`backend/app/services/people_service.py`)
- `request_leave()` - Create leave request with balance check
- `sync_calendar()` - Upsert CalendarEvent from Google/Outlook
- `get_user_calendar_events()` - Retrieve events for date range

---

## 📈 Growth & Scaling Agent (`backend/app/agents/growth_scaling.py`)

*The Recruiter & Onboarding Specialist.* (800+ lines)

- **Role**: Manages hiring pipelines, recruitment operations, and knowledge continuity.
- **Capabilities**:
  - **Job Role Definition**: Structured requirements with must-have vs. nice-to-have skills.
  - **JD Generation**: Auto-generates job descriptions from requirements.
  - **Candidate Pipeline**: Tracks candidates through APPLIED → SCREENING → INTERVIEWING → OFFER → HIRED stages.
  - **Resume Scoring**: `score_candidate()` uses keyword matching to rank applicants.
  - **Interview Management**: Scheduling, feedback collection, recommendation tracking.
  - **Onboarding Plans**: Generates 30-60-90 day plans with auto-assigned tasks.
  - **Knowledge Base**: Curates documentation, flags outdated content, role-based filtering.

### Core Logic (`backend/app/core/growth_logic.py`)
```python
score_candidate(resume_text, job_requirements) -> Dict
# Returns: score (0-100), matches, missing, recommendation

generate_onboarding_tasks(db, plan_id, employee_name, role, start_date) -> Dict
# Creates OnboardingTask and Task objects for Day 1, Week 1, Month 1
```

### Service Layer (`backend/app/services/growth_service.py`)
- `create_job_role()` - Initialize job opening
- `process_application()` - Score and save candidate
- `start_onboarding()` - Activate plan and generate tasks

---

## ⚙️ Execution Agent (`backend/app/agents/execution.py`)

*The Project Manager.*

- **Role**: The "nagger" that ensures things get done.
- **Capabilities**:
  - **Monitoring**: Polls the database for tasks approaching deadlines.
  - **GitHub Synchronization**:
    - **Outbound**: Creates and updates GitHub Issues from VAM tasks.
    - **Inbound**: Listens for webhook events (close/reopen) to update VAM status.
    - **Linking**: Maintains mapping between internal Task IDs and GitHub Issue Numbers.
  - **Blocker Detection**: Identifies tasks with no recent updates.
  - **Escalation**: Triggers the Manager Orchestrator to re-assign or notify stakeholders if blockers persist.
  - **Milestone Tracking**: Validates critical path progress.

### Service Layer (`backend/app/services/github_service.py`)
- `create_issue()` - Create new GitHub issue from VAM task
- `update_issue()` - Sync VAM updates to GitHub
- `verify_webhook_signature()` - Securely validate inbound webhooks
- `exchange_code_for_token()` - Handle OAuth flow

---

## 👔 Managerial Agent (`backend/app/agents/managerial.py`)

*The Executive.*

- **Role**: Provides high-level strategic oversight, risk analysis, and communication synthesis.
- **Capabilities**:
  - **Risk Analysis**: Evaluates task delays and resource bottlenecks to predict project risks.
  - **Goal Refinement**: Uses AI to structure vague objectives into measurable KPIs.
  - **Reporting**: Generates automated standups, weekly reports, and stakeholder updates.
  - **Meeting Intelligence**: Summarizes transcripts into decisions and action items.
  - **Trade-off Analysis**: Compares options with pros/cons.
  - **Escalation Briefs**: Concise summaries for leadership attention.

---

## 📣 Communication Agent (`backend/app/agents/communication.py`)

*The Spokesperson & Proactive Communicator.*

- **Role**: Manages all outgoing information to humans and drives proactive engagement.
- **Capabilities**:
  - **Summarization**: Compresses complex logs into readable status updates.
  - **Routing**: Decides whether to ping via Slack (urgent) or Email (digest).
  - **Tone Adaptation**: Adjusts language based on audience (technical dev vs. executive).
  - **Slack Integration**: Real-time messaging via Socket Mode.
  - **Morning Standups**: Proactive 09:00 check-ins via Slack DM.
  - **Calendar Blocking**: Creates focus time blocks based on user responses.

### Standup Handler (`backend/app/agents/standup_handler.py`)
```python
initiate_standup(user_id, db) -> Dict
# Fetches GitHub issues, sends Slack prompt, tracks conversation state

process_standup_response(user_id, response_text, db) -> Dict
# Parses focus from response, finds free slot, schedules calendar block

extract_focus_from_response(text) -> Optional[str]
# NLP extraction: "I'm working on the API" -> "API"
```

### Service Layer (`backend/app/services/slack_service.py`)
- `SlackService` class - Socket Mode bot with message handlers
- `send_dm()` - Send direct messages to Slack users
- `get_user_info()` - Fetch Slack user profile
- `send_standup_prompt()` - Send formatted standup message with GitHub issues
- `link_slack_user()` - Map Slack User ID to VAM user

### Service Layer (`backend/app/services/google_calendar_service.py`)
- `GoogleCalendarService` class - Full Calendar API integration
- `get_daily_schedule()` - Events + free slots analysis
- `schedule_focus_block()` - Create focus time blocks
- `move_event()` - Reschedule flexible meetings

---

## 📊 Analytics & Automation Agent (`backend/app/agents/analytics_automation.py`)

*The Data Scientist.* (720+ lines)

- **Role**: Analyzes execution data, detects patterns, forecasts outcomes, and triggers proactive recommendations.
- **Capabilities**:
  - **Project Analytics**: Health scores (0-100), trends (improving/stable/declining), contributing factors.
  - **Team Workload Analytics**: Distribution analysis, overload/underutilization signals.
  - **Delivery Trends**: Planned vs actual timeline comparison.
  - **Risk Forecasting**: Probability-based risk detection with time-to-risk windows and suggested mitigations.
  - **Executive Dashboards**: Concise, outcome-focused summaries for leadership.
  - **Proactive Suggestions**: Actionable recommendations with rationale and expected impact.
  - **Early Warnings**: Prioritized alerts that trigger early enough to act (avoids alert fatigue).
  - **Pattern Learning**: Tracks recurring issues to improve forecast accuracy over time.
  - **Replanning Proposals**: Suggests task reassignments when delays detected.

### Core Logic (`backend/app/core/analytics.py`)
```python
calculate_velocity(db, project_id, days=30) -> Dict
# Returns: velocity_per_week, remaining_tasks, projected_completion, trend

compute_risk_score(db, project_id) -> Dict
# Algorithm: overdue*5 + blocked*3 + high_load*10 + deadline_proximity*5
# Returns: risk_score (0-100), risk_level (low/medium/high/critical), factors

take_project_snapshot(db, project_id) -> Dict
# Captures metrics for historical trend analysis
```

### Service Layer (`backend/app/services/analytics_service.py`)
- `get_dashboard_data()` - Risk heatmap, goals summary, task distribution
- `evaluate_rules()` - IFTTT automation rule processor
- `run_forecast()` - Generate and store AI predictions

### Automation Models
- **ProjectSnapshot**: Historical state for velocity trends
- **AutomationRule**: IFTTT triggers (`{"metric": "overdue_tasks", "operator": ">", "value": 5}`)
- **Forecast**: AI predictions with confidence scores and validation tracking

---

## 🛡️ Platform & Enterprise Agent (`backend/app/agents/platform_enterprise.py`)

*The Security & Reliability Engineer.* (1,000+ lines)

- **Role**: Enforces security, manages access control, and ensures system reliability.
- **Capabilities**:
  - **RBAC**: Role-based access control with Admin, Manager, Contributor, Viewer roles.
  - **Identity Management**: GitHub OAuth 2.0 integration for authentication and user profile sync.
  - **Permission Verification**: `check_permission(user_id, permission)` with audit logging.
  - **Approval Workflows**: Routes sensitive actions through approval chains with expiration.
  - **Audit Trail**: Immutable logging of who, what, when, why—including AI prompt/response.
  - **State Management**: Versioned state storage with rollback support.
  - **Idempotency**: Prevents duplicate operations via operation locks.
  - **Retry Logic**: Exponential backoff with fatal error detection.
  - **Health Monitoring**: Database connectivity, stale locks, expired approvals.
  - **MCP Tool Discovery**: Scans MCP servers and registers tools dynamically.
  - **Safe Tool Execution**: Wraps dangerous tools with approval gates.
  - **Circuit Breaker**: Auto-disables tools after 5 consecutive failures.

### Core Security (`backend/app/core/security.py`)
```python
verify_permission(db, user_id, resource, action) -> Dict
# Checks role permissions against DEFAULT_PERMISSIONS matrix

log_action(db, actor_id, action_type, target_entity, ...) -> str
# Creates immutable AuditLog entry with prompt/response for AI explainability

require_permission(resource, action)  # FastAPI dependency decorator
```

### Service Layer (`backend/app/services/platform_service.py`)
- `configure_tenant()` - Multi-tenant setup with feature flags
- `export_audit_logs()` - Compliance reporting with date/actor filters
- `register_mcp_tool()` - Dynamic tool registration with safety detection
- `seed_default_permissions()` - Bootstrap RBAC rules

### Enterprise Models
- **AuditLog**: Immutable record with prompt/response for AI actions
- **AgentActivity**: Log of agent actions (syncs, notifications) for timeline view
- **UserIntegration**: OAuth tokens for secondary providers (Google, Slack)
- **RolePermission**: Granular role → resource → action mappings
- **Tenant**: Multi-tenancy with subscription tiers and limits
- **MCPTool**: Tool registry with safety gates and health tracking

---

## 🔮 Advanced Capabilities Agent (`backend/app/agents/advanced_capabilities.py`)

*The Extension Platform.*

- **Role**: Sandboxed platform for customization, extensions, and advanced features.
- **Capabilities**:
  - **Rules Engine**: Organization-specific condition-action rules with conflict resolution.
  - **Custom Workflows**: DAG-based workflows with cycle detection and validation.
  - **Plugin System**: Sandboxed plugin execution with timeouts and schema validation.
  - **Voice Intents**: Voice-to-intent pipeline (confirmation always required).
  - **Predictive Staffing**: Headcount recommendations with confidence bands.
  - **Performance Coaching**: Private, supportive feedback (no ranking).
  - **Feature Flags**: Gradual rollout with percentage targeting.

---

## 🧠 Cognitive Persistence (`backend/app/core/memory.py`)

*The Long-Term Memory.*

- **Role**: Stores and retrieves semantic context using vector embeddings.
- **Components**:
  - **Vector Store**: PostgreSQL with `pgvector` extension.
  - **Embeddings**: OpenAI `text-embedding-3-small` (1536 dimensions).
  - **Retrieval**: Cosine similarity search for relevant context query.
- **Memory Types**:
  - `DECISION`: Strategic choices made by agents.
  - `PREFERENCE`: User preferences learned over time.
  - `STANDUP_FOCUS`: Daily focus items from standups.
  - `TASK_COMPLETION`: Completed work context.
- **Context Injection**:
  - `MemoryService.retrieve_context()` finds relevant memories.
  - `format_context_for_prompt()` injects them into Agent system prompts.
  - Enables agents to "remember" past instructions and project history.

---

## 🛡️ Safety & Governance (`backend/app/agents/risk.py`)

*The Safety Valve.*

- **Role**: Prevents catastrophic AI mistakes by intercepting high-risk actions.
- **Risk Gate Service**:
  - **Scoring**: Actions are scored 0-100 (e.g., `delete_project`=90, `create_task`=5).
  - **Threshold**: Actions > 50 require human approval.
- **Intervention Flow**:
  1. Agent proposes action (e.g., "Delete Repository").
  2. `@require_approval` decorator calls `RiskGateService.assess_risk()`.
  3. Risk Score is 100 -> **Blocked**.
  4. `ApprovalRequest` created with status `PENDING`.
  5. UI shows **Intervention Modal**.
  6. Manager clicks "Approve" -> Action executes.
- **Audit Logging**:
  - `@log_activity` decorator automatically records:
    - Actor (User/Agent)
    - Action Type & Payload
    - Timestamp & Duration
    - Outcome (Success/Failure)
  - Stored in `audit_logs` table for compliance.

---

## 🔌 MCP Tool Integration

VAM uses the **Model Context Protocol (MCP)** to interact with the outside world safely.

| Tool Server | Functionality | Status |
|-------------|---------------|--------|
| `mcp/calendar.py` | Read/Write events to Calendars | ✅ Implemented |
| `mcp/communication.py` | Send Emails, Slack Messages, Approvals | ✅ Implemented |
| `github` | Create issues, PRs (via MCP discovery) | ✅ Registered |
| `slack` | Send messages, create channels | ✅ Registered |
| `google_drive` | Create/share documents | ✅ Registered |

### Tool Safety Features
- **Auto-Approval Detection**: Tools with "delete", "destroy", "send" in name require approval
- **Role-Based Access**: Tools can be restricted to specific roles
- **Circuit Breaker**: Auto-disables after 5 consecutive failures
- **Health Monitoring**: Tracks error counts and last successful execution

---

## 🔄 Example Flows

### Leave Approval Flow
1. **Input**: User clicks "Request Leave" or types "Approve leave for Ashish tomorrow".
2. **Orchestrator**: Analyzes text -> detects `personnel` intent -> Routes to **People Ops**.
3. **People Ops Agent**:
   - Calls `get_available_hours(ashish, tomorrow)`.
   - Checks `employee.leave_balance`.
   - Checks for conflicting meetings or deadlines.
   - *Logic*: If free and balance > 0, returns `Approved`.
4. **Orchestrator**: Receives `Approved` signal.
5. **Orchestrator**: Routes to **Communication Agent**.
6. **Communication Agent**: Generates: "Leave approved for Ashish. Calendar updated."
7. **Output**: Displayed on Dashboard Log + logged in AuditLog.

### GitHub Task Sync Flow
1. **Trigger**: User clicks "Sync to GitHub" on a Task.
2. **Backend**: Checks `User.github_access_token` and `default_repo`.
3. **GitHub Service**: Creates Issue via GitHub API with labels `vam-sync`.
4. **Task Update**: Stores `github_issue_id` and sets sync status to `synced`.
5. **Bi-directional**:
   - **VAM → GitHub**: Updates to Task title/desc push to Issue.
   - **GitHub → VAM**: Webhook triggers on Issue Close → Marks Task Completed.
6. **Audit**: Sync events logged to `AgentActivity`.

### Morning Standup Flow (Phase 2)
1. **Trigger**: Scheduler fires at 09:00 local time.
2. **Standup Handler**: Queries all users with linked Slack accounts.
3. **For Each User**:
   - Fetches assigned GitHub Issues via `GitHubService`.
   - Sends Slack DM: "Good morning! I see 3 issues assigned to you. What's your focus?"
4. **User Response**: "I'm working on the API."
5. **Standup Handler**:
   - Parses response via `extract_focus_from_response()`.
   - Calls `find_free_slot()` on Google Calendar.
   - Creates focus block via `schedule_focus_block()`.
6. **Confirmation DM**: "Got it! I've blocked 10am-12pm for 'API Work'."
7. **Audit**: Standup logged to `AgentActivity`.

### Hiring Pipeline Flow
1. **Input**: "Post a new Backend Engineer role".
2. **Orchestrator**: Routes to **Growth & Scaling Agent**.
3. **Growth Agent**:
   - Creates `JobRole` with requirements.
   - Generates job description.
   - Creates `ApprovalRequest` for posting (requires human approval).
4. **Manager Approves**: Approval processed via **Platform Agent**.
5. **Candidates Apply**: Each application scored via `score_candidate()`.
6. **Interviews Scheduled**: Respect participant availability.
7. **Offer Extended**: Creates `ApprovalRequest` for offer letter.
8. **Onboarding Activated**: Auto-generates 30-60-90 day tasks.

### Risk Detection Flow
1. **Trigger**: Daily snapshot job or real-time task update.
2. **Analytics Agent**: Runs `compute_risk_score()` on all projects.
3. **Rule Evaluation**: Checks `AutomationRule` triggers.
4. **High Risk Detected**: Generates early warning alert.
5. **Proactive Suggestion**: "Reassign Task A from User X (Overloaded) to User Y (Free)".
6. **Manager Review**: Suggestion presented for approval.
7. **Audit Logged**: All decisions recorded with reasoning.

---

## 📊 Data Models Overview

| Category | Models |
|----------|--------|
| **Core** | Task, Project, Milestone, Goal, User, Employee, TaskHistory |
| **People** | LeaveRequest, UserLeave, Holiday, Meeting, CalendarEvent, WorkCapacity, BurnoutIndicator |
| **Growth** | JobRole, Candidate, Interview, OnboardingPlan, OnboardingTask, KnowledgeArticle |
| **Analytics** | ProjectSnapshot, AutomationRule, Forecast |
| **Platform** | AuditLog, AgentActivity, RolePermission, Tenant, MCPTool, ApprovalRequest, SystemState, OperationLock |
| **Advanced** | OrganizationRule, CustomWorkflow, Plugin, VoiceIntent, StaffingPrediction, PerformanceFeedback, FeatureFlag |

---

## 🔐 Role Permission Matrix

| Role | Project | Task | User | Budget | Goal | Audit |
|------|---------|------|------|--------|------|-------|
| **Admin** | CRUD + Approve | CRUD + Approve | CRUD + Approve | CRUD + Approve | CRUD + Approve | Read |
| **Manager** | CRU + Approve | CRUD + Approve | RU | RU + Approve | CRU | Read |
| **Contributor** | R | CRU (own) | R | R | R | - |
| **Viewer** | R | R | R | - | R | - |

*C=Create, R=Read, U=Update, D=Delete*
