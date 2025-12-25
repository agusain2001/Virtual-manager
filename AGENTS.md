# 🤖 VAM Agent System Documentation

This document connects the functional specifications to the codebase, explaining how the multi-agent system thinks, routes, and executes.

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

## 🕵️ Planning Agent (`backend/app/agents/planning.py`)

*The Strategist.*
- **Role**: Takes abstract goals and converts them into concrete Task Dependency Graphs (DAGs).
- **Capabilities**:
  - **Decomposition**: Breaks "Launch website" into "Design", "Frontend", "Backend", "Deploy".
  - **Estimation**: Uses historical data (Vector Memory) to estimate effort.
  - **Re-planning**: Triggered by the Execution Agent when deadlines slip.

## 👥 People Ops Agent (`backend/app/agents/people_ops.py`)

*The HR Manager.*
- **Role**: Manages the human constraints of the system.
- **Capabilities**:
  - **Leave Management**: Checks inputs against policy docs and calendar availability. **Requires rationale for all approvals/rejections.**
  - **Burnout Detection**: Monitors sustained overload, deadline pressure, and overtime to flag risks.
  - **Skill Matrix**: Tracks employee skills and identifies gaps for project assignments.
  - **Meeting Scheduling**: Schedules meetings with conflict detection and working hours validation.

## 📈 Growth & Scaling Agent (`backend/app/agents/growth_scaling.py`)

*The Recruiter & Onboarding Specialist.*
- **Role**: Manages hiring pipelines, recruitment operations, and knowledge continuity.
- **Capabilities**:
  - **Hiring Pipeline**: Tracks candidates from application to offer. **Requires human approval for job postings and rejections.**
  - **Role Definition**: Structured job requirements with must-have vs. nice-to-have skills.
  - **Onboarding**: Generates and tracks 30-60-90 day onboarding plans.
  - **Knowledge Base**: Curates internal documentation and flags outdated content.

## ⚙️ Execution Agent (`backend/app/agents/execution.py`)

*The Project Manager.*
- **Role**: The "nagger" that ensures things get done.
- **Capabilities**:
  - **Monitoring**: Polls the database for tasks approaching deadlines.
  - **Blocker Detection**: Identifies tasks with no recent updates.
  - **Escalation**: Triggers the Manager Orchestrator to re-assign or notify stakeholders if a hard blocker is found.
  - **Milestone Tracking**: Validates critical path progress.

## 👔 Managerial Agent (`backend/app/agents/managerial.py`)

*The Executive.*
- **Role**: Provides high-level strategic oversight, risk analysis, and communication synthesis.
- **Capabilities**:
  - **Risk Analysis**: Evaluates task delays and resource bottlenecks to predict project risks.
  - **Goal Refinement**: Uses AI to structure vague objectives into measurable KPIs.
  - **Reporting**: Generates automated standups, weekly reports, and stakeholder updates.
  - **Meeting Intelligence**: Summarizes transcripts into decisions and action items.

## 📣 Communication Agent (`backend/app/agents/communication.py`)

*The Spokesperson.*
- **Role**: Manages all outgoing information to humans.
- **Capabilities**:
  - **Summarization**: Compresses complex logs into readable status updates.
  - **Routing**: Decides whether to ping via Slack (urgent) or Email (digest).
  - **Tone Adaptation**: Adjusts language based on whether it's talking to a dev (technical) or a stakeholder (high-level).

## 📊 Analytics & Automation Agent (`backend/app/agents/analytics_automation.py`)

*The Data Scientist.*
- **Role**: Analyzes execution data, detects patterns, forecasts outcomes, and triggers proactive recommendations.
- **Capabilities**:
  - **Project Analytics**: Health scores, trends, and contributing factors analysis.
  - **Risk Forecasting**: Probability-based risk detection with time-to-risk windows.
  - **Executive Dashboards**: Concise, outcome-focused summaries for leadership.
  - **Proactive Suggestions**: Actionable recommendations with rationale and expected impact.
  - **Early Warnings**: Prioritized alerts that trigger early enough to act.
  - **Pattern Learning**: Tracks recurring issues to improve forecasts over time.

## 🛡️ Platform & Enterprise Agent (`backend/app/agents/platform_enterprise.py`)

*The Security & Reliability Engineer.*
- **Role**: Enforces security, manages access control, and ensures system reliability.
- **Capabilities**:
  - **RBAC**: Role-based access control with Admin, Manager, Contributor, Viewer roles.
  - **Approval Workflows**: Routes sensitive actions through approval chains.
  - **Audit Trail**: Immutable logging of who, what, when, why for every action.
  - **State Management**: Versioned state with rollback support.
  - **Idempotency**: Prevents duplicate operations.
  - **Health Monitoring**: System health checks and observability.

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

## 🔌 MCP Tool Integration

VAM uses the **Model Context Protocol (MCP)** to interact with the outside world safely.

| Tool Server | Functionality | Status |
|-------------|---------------|--------|
| `mcp/calendar.py` | Read/Write events to Calendars | ✅ Stubbed |
| `mcp/communication.py` | Send Emails, Slack Messages | ✅ Stubbed |
| `mcp/github.py` | Create issues, check PR status | 🚧 Planned |
| `mcp/linear.py` | Sync tasks with Linear | 🚧 Planned |

## 🔄 Example Flow: Leave Approval

1. **Input**: User clicks "Request Leave" or types "Approve leave for Ashish tomorrow".
2. **Orchestrator**: Analyzes text -> detects `personnel` intent -> Routes to **People Ops**.
3. **People Ops Agent**:
   - Calls `calendar_tool.get_events(ashish, tomorrow)`.
   - Checks `policy_db.get_balance(ashish)`.
   - *Logic*: If free and balance > 0, returns `Approved`.
4. **Orchestrator**: Receives `Approved` signal.
5. **Orchestrator**: Routes to **Communication Agent**.
6. **Communication Agent**: Generates: "Leave approved for Ashish. Calendar updated."
7. **Output**: Displayed on Dashboard Log.
