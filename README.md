# Virtual AI Manager (VAM)

![Status](https://img.shields.io/badge/Status-MVP-green)
![Python](https://img.shields.io/badge/Backend-FastAPI%20%7C%20LangGraph-blue)
![Frontend](https://img.shields.io/badge/Frontend-Next.js%20%7C%20TailwindCSS-black)

## 🌟 Vision

The **Virtual AI Manager (VAM)** is an autonomous managerial system designed to operate continuously alongside human teams. Unlike requested-response chatbots, VAM proactively plans, monitors, and executes management tasks—scheduling meetings, approving leave, tracking deadlines, and reporting progress—while keeping humans in the loop via a dedicated control plane.

## 🏗 System Architecture

VAM operates on a multi-agent architecture using **LangGraph** for orchestration and **MCP (Model Context Protocol)** for tool integration.

```mermaid
graph TD
    User[Control Plane UI] <--> API[FastAPI Backend]
    API <--> Orchestrator[Manager Orchestrator]
    
    subgraph "Agent Core"
        Orchestrator --> Planning[Planning Agent]
        Orchestrator --> People[People Ops Agent]
        Orchestrator --> Exec[Execution Agent]
        Orchestrator --> Comm[Communication Agent]
    end
    
    subgraph "Memory & Tools"
        Planning --> VectorDB[(Vector Memory)]
        People --> Cal[Calendar MCP]
        Exec --> Mon[Task Monitors]
        Comm --> Slack[Slack/Email MCP]
    end
```

## ✨ Key Features

- **🧠 Autonomous Planning**: Decomposes high-level goals (e.g., "Launch Marketing Campaign") into actionable steps and dependency graphs.
- **busts People Operations**: Handling leave requests, team availability, and resource allocation automatically against policies.
- **👁️ Active Monitoring**: Continuously watches task statuses and proactively flags risks before deadlines are missed.
- **🛡️ Human Control Plane**: A "God Mode" dashboard to observe agent thought processes in real-time and intervene/override actions instantly.
- **🔌 Deep Integration**: Built on MCP to plug into Google Calendar, Slack, GitHub, and Jira without custom glue code.

## 🚀 Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **Git**

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
uvicorn app.main:app --reload
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
├── backend/                 # Python/FastAPI Agent Core
│   ├── app/
│   │   ├── agents/          # Agent Logic (Orchestrator, Planning, etc.)
│   │   ├── core/            # Config, Database, Logging, Memory
│   │   ├── mcp/             # Model Context Protocol Tool Servers
│   │   └── main.py          # API Entry Point
│   └── requirements.txt
│
├── frontend/                # Next.js Control Plane
│   ├── src/
│   │   ├── app/             # Pages & Layouts
│   │   └── components/      # UI Components (ActivityLog, Modal)
│   └── package.json
│
├── AGENTS.md                # Detailed Agent Documentation
└── README.md                # Project Overview
```

## 🤝 Contributing

This is an MVP implementation. We welcome contributions to expand agent capabilities!
1. Fork the repo.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes.
4. Push to the branch.
5. Open a Pull Request.

## 📄 License

Distributed under the MIT License.
