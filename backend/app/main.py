from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.database import engine, Base
from backend.app.routes import router as api_router
from backend.app.routers import managerial, goals, milestones, execution, people_ops, growth_scaling, analytics, platform, advanced, auth, webhooks, google_auth, slack_auth

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Virtual AI Manager",
    version="2.0.0",
    description="Autonomous AI Manager with Task, Project, Execution Management & Communication Integrations"
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

# Phase 2: Google and Slack auth routers
app.include_router(google_auth.router)
app.include_router(slack_auth.router)

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


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("[Startup] Initializing VAM services...")
    
    # Start the scheduler
    try:
        from backend.app.core.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        print(f"[Startup] Could not start scheduler: {e}")
    
    # Initialize Slack bot (if configured)
    try:
        from backend.app.services.slack_service import get_slack_service
        from backend.app.agents.standup_handler import register_standup_message_handler
        
        service = get_slack_service()
        if service.is_configured:
            service.start(blocking=False)
            register_standup_message_handler()
            print("[Startup] Slack bot started")
        else:
            print("[Startup] Slack not configured (set SLACK_BOT_TOKEN and SLACK_APP_TOKEN)")
    except Exception as e:
        print(f"[Startup] Could not start Slack bot: {e}")
    
    print("[Startup] VAM is ready!")


@app.get("/")
async def root():
    return {
        "message": "Virtual AI Manager System Online",
        "version": "2.0.0",
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
            "GitHub OAuth & Issue Sync",
            "Google Calendar Integration",
            "Slack Integration & Standups"
        ]
    }


@app.get("/health")
async def health_check():
    # Check integrations status
    integrations = {
        "google_calendar": "available",
        "slack": "available"
    }
    
    try:
        from backend.app.services.slack_service import get_slack_service
        service = get_slack_service()
        integrations["slack"] = "running" if service._running else ("configured" if service.is_configured else "not_configured")
    except:
        integrations["slack"] = "not_configured"
    
    return {
        "status": "healthy",
        "database": "connected",
        "agents": {
            "orchestrator": "online",
            "managerial": "online",
            "planning": "online",
            "execution": "online",
            "people_ops": "online",
            "communication": "online",
            "standup_handler": "online"
        },
        "integrations": integrations
    }
