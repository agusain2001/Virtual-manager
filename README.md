# Virtual AI Manager (VAM)

![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Backend-FastAPI%20%7C%20LangGraph-blue)
![Frontend](https://img.shields.io/badge/Frontend-Next.js%20%7C%20TailwindCSS-black)
![Phases](https://img.shields.io/badge/Phases-1--6%20Complete-purple)

## 🌟 Vision

The **Virtual AI Manager (VAM)** is an autonomous managerial system designed to operate continuously alongside human teams. Unlike request-response chatbots, VAM proactively plans, monitors, and executes management tasks—scheduling meetings, approving leave, tracking deadlines, forecasting risks, and reporting progress—while keeping humans in the loop via a dedicated control plane.

## 🏗 System Architecture

VAM operates on a multi-agent architecture using **LangGraph** for orchestration and **MCP (Model Context Protocol)** for tool integration.

```mermaid
graph TD
    User[Control Plane UI] <--> API[FastAPI Backend]
    API <--> Orchestrator[Manager Orchestrator]
    
    subgraph "Agent Core (8 Agents)"
        Orchestrator --> Planning[Planning Agent]
        Orchestrator --> People[People Ops Agent]
        Orchestrator --> Growth[Growth & Scaling Agent]
        Orchestrator --> Exec[Execution Agent]
        Orchestrator --> Comm[Communication Agent]
        Orchestrator --> Managerial[Managerial Agent]
        Orchestrator --> Analytics[Analytics Agent]
        Orchestrator --> Platform[Platform Agent]
    end
    
    subgraph "Memory & Tools"
        Planning --> VectorDB[(Vector Memory)]
        People --> Cal[Calendar MCP]
        Growth --> KB[Knowledge Base]
        Exec --> Mon[Task Monitors]
        Comm --> Slack[Slack/Email MCP]
        Analytics --> Forecast[Risk & Velocity]
        Platform --> RBAC[Security & Audit]
    end
```

## ✨ Key Features (Phases 1-6 Complete)

### Phase 1-2: Core Foundation & Communication
- **🧠 Autonomous Planning**: Decomposes goals into actionable DAGs with dependency tracking
- **📋 Task & Project Management**: Full lifecycle management with milestones and goals
- **🐙 GitHub Integration**: Bi-directional sync with GitHub Issues, OAuth login, and webhook automation
- **📅 Google Calendar**: Real-time calendar sync, free slot detection, focus block scheduling
- **💬 Slack Integration**: Socket Mode bot, DM handling, proactive standups
- **☀️ Morning Standups**: Automated 09:00 check-ins with GitHub issue context
- **👁️ Active Monitoring**: Proactive risk detection and deadline tracking
- **📊 Managerial Intelligence**: Strategic risk analysis, goal refinement, automated reporting

### Phase 3: Human-Centric Intelligence
- **🤝 People Operations**: Leave management, burnout detection, skill matrices
- **📅 Calendar Integration**: Working hours, time zones, meeting scheduling
- **⚖️ Capacity Planning**: `get_available_hours()`, `check_overload()` functions
- **🔥 Burnout Watchdog**: Sustained overload and deadline pressure monitoring

### Phase 4: Cognitive Persistence (New)
- **🧠 Long-Term Memory**: Vector embeddings (OpenAI `text-embedding-3-small`) to recall past decisions
- **📚 Context Injection**: Semantic search retrieves relevant history into agent prompts
- **📌 Semantic Search**: `pgvector` integration for finding related tasks, plans, and meetings
- **🔄 Auto-Memory triggers**: Daily standup focus and task completions are automatically memorized

### Phase 5: Growth Intelligence
- **📈 Hiring Pipeline**: Candidate tracking with automated resume scoring
- **✅ Interview Management**: Scheduling, feedback collection, offer workflows
- **🎯 Onboarding**: 30-60-90 day plans with auto-generated tasks
- **📚 Knowledge Base**: Internal documentation with role-based curation

### Phase 6: Analytics & Automation
- **📉 Velocity Tracking**: Task completion trends and projected dates
- **⚠️ Risk Scoring**: Weighted algorithm (overdue × 5, blocked × 3, load × 10)
- **📊 Executive Dashboards**: Goal + project + risk summaries
- **🤖 Automation Rules**: IFTTT triggers for proactive interventions
- **📸 Project Snapshots**: Historical metrics for trend analysis
- **🔮 AI Forecasting**: Completion predictions with confidence scores

### Phase 7: Safety & Governance (Implemented)
- **🛡️ Risk Gate**: Intercepts high-risk actions (score > 50) for human approval
- **✋ Intervention UI**: Modal to review, approve, or reject agent actions
- **🔐 RBAC**: Role-based access (Admin, Manager, Contributor, Viewer)
- **📝 Immutable Audit Logs**: Automatic `@log_activity` capture for all sensitive ops
- **✅ Approval Workflow**: Async approval requests with risk scoring (Critical/High/Medium)
- **🔌 MCP Tool Safety**: Circuit breakers and permissions for tool execution

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **Git**
- **GitHub OAuth App** (Client ID & Secret)
- **Google OAuth App** (for Calendar - optional)
- **Slack App** (for Slack integration - optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/agusain2001/Virtual-manager.git
   cd Virtual-manager
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   # Windows
   ./venv/Scripts/Activate.ps1
   # Linux/Mac
   # source venv/bin/activate
   
   pip install -r requirements.txt
   
   # Configure Environment
   cp .env.example .env
   # Edit .env with your GitHub Client ID/Secret and DB settings
   ```
   
3. **Frontend Setup**
   ```bash
   cd ../frontend
   npm install
   ```

### Running the System

**1. Start the Brain (Backend)**
```bash
cd backend
uvicorn backend.app.main:app --reload
```
API runs on: `http://localhost:8000`

**2. Start the Control Plane (Frontend)**
```bash
cd frontend
npm run dev
```
Dashboard runs on: `http://localhost:3000`

## 📂 Project Structure

```
Virtual-manager/
├── backend/                     # Python/FastAPI Agent Core
│   ├── app/
│   │   ├── agents/              # 8 Specialized Agents
│   │   │   ├── orchestrator.py      # Manager Orchestrator (LangGraph)
│   │   │   ├── planning.py          # Task decomposition & DAGs
│   │   │   ├── execution.py         # Monitoring & escalation
│   │   │   ├── people_ops.py        # HR & capacity (1400+ lines)
│   │   │   ├── growth_scaling.py    # Hiring & onboarding (800+ lines)
│   │   │   ├── analytics_automation.py  # Forecasting & insights (720+ lines)
│   │   │   ├── platform_enterprise.py   # Security & RBAC (1000+ lines)
│   │   │   └── advanced_capabilities.py # Rules, plugins, voice
│   │   ├── core/                # Core Logic Modules
│   │   │   ├── availability.py      # Capacity calculations
│   │   │   ├── analytics.py         # Velocity & risk scoring
│   │   │   ├── growth_logic.py      # Candidate scoring
│   │   │   ├── security.py          # RBAC middleware
│   │   │   └── scheduler.py         # Cron jobs
│   │   ├── services/            # Service Layer
│   │   │   ├── people_service.py    # Leave & calendar CRUD
│   │   │   ├── growth_service.py    # Applications & onboarding
│   │   │   ├── analytics_service.py # Dashboard & rules
│   │   │   ├── platform_service.py  # Tenants & audit export
│   │   │   ├── github_service.py    # GitHub API & Sync
│   │   │   ├── google_calendar_service.py  # Google Calendar API
│   │   │   └── slack_service.py     # Slack Socket Mode
│   │   ├── routers/             # API Routers (auth, webhooks, etc)
│   │   ├── mcp/                 # MCP Tool Servers
│   │   ├── models.py            # 30+ SQLAlchemy models
│   │   └── main.py              # FastAPI entry point
│   └── requirements.txt
│
├── frontend/                    # Next.js Control Plane
│   ├── src/
│   │   ├── app/                 # Pages & Layouts
│   │   └── components/          # 20+ UI Components
│   └── package.json
│
├── AGENTS.md                    # Detailed Agent Documentation
└── README.md                    # Project Overview
```

## 📊 API Endpoints (100+)

| Category | Endpoints | Description |
|----------|-----------|-------------|
| Tasks | `/api/v1/tasks/*` | CRUD, status, assignment |
| Projects | `/api/v1/projects/*` | Health, DAG, milestones |
| Goals | `/api/v1/goals/*` | OKR tracking, alignment |
| People | `/api/v1/people/*` | Leave, availability, workload |
| Growth | `/api/v1/growth/*` | Jobs, candidates, onboarding |
| Analytics | `/api/v1/analytics/*` | Velocity, forecasts, rules |
| Platform | `/api/v1/platform/*` | Users, RBAC, audit, tools |
| Managerial | `/api/v1/managerial/*` | Risk, reports, strategy |
| Auth | `/auth/*` | GitHub OAuth, session, repo selection |
| Google | `/auth/google/*` | Calendar OAuth, connect/disconnect |
| Slack | `/auth/slack/*` | User linking, bot status, test DM |
| Webhooks | `/webhooks/*` | GitHub inbound event processing |

## 🤝 Contributing

We welcome contributions to expand agent capabilities!
1. Fork the repo.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes.
4. Push to the branch.
5. Open a Pull Request.

## 📄 License

Distributed under the MIT License.
