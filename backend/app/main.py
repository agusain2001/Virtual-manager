from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.database import engine, Base
from backend.app.routes import router

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Virtual AI Manager",
    version="0.2.0",
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
app.include_router(router)

@app.get("/")
async def root():
    return {
        "message": "Virtual AI Manager System Online",
        "version": "0.1.0",
        "features": [
            "Task Management",
            "Project Management",
            "Execution Monitoring",
            "Agent Orchestration"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "agents": {
            "orchestrator": "online",
            "planning": "online",
            "execution": "online",
            "people_ops": "online",
            "communication": "online"
        }
    }