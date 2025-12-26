from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.database import engine, Base
from backend.app.routes import router as api_router
from backend.app.routers import managerial, goals, milestones, execution, people_ops, growth_scaling, analytics, platform, advanced, auth, webhooks

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Virtual AI Manager",
    version="1.0.0",
    description="Autonomous AI Manager with Task, Project & Execution Management"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Include authentication and webhook routers (no prefix for standard paths)
app.include_router(auth.router)
app.include_router(webhooks.router)

# Include feature-specific routers
app.include_router(managerial.router, prefix="/api")
app.include_router(goals.router, prefix="/api")
app.include_router(milestones.router, prefix="/api")
app.include_router(execution.router, prefix="/api")
app.include_router(people_ops.router)
app.include_router(growth_scaling.router)
app.include_router(analytics.router)
app.include_router(platform.router)
app.include_router(advanced.router)


@app.get("/")
async def root():
    return {
        "message": "Virtual AI Manager System Online",
        "version": "1.0.0",
        "features": [
            "Task Management",
            "Project Management", 
            "Milestone Tracking",
            "Goal Alignment",
            "Execution Monitoring",
            "Managerial Intelligence",
            "Escalation System",
            "Agent Orchestration",
            "People & Operations",
            "Growth & Scaling",
            "Analytics & Automation",
            "Platform & Enterprise (RBAC, Audit, MCP)",
            "GitHub OAuth & Issue Sync"
        ]
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "agents": {
            "orchestrator": "online",
            "managerial": "online",
            "planning": "online",
            "execution": "online",
            "people_ops": "online",
            "communication": "online"
        }
    }