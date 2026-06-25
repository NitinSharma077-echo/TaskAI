from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.database import Base, engine

# Import models to register them with metadata
from app.models.user import User
from app.models.task import Task
from app.models.approval import Approval
from app.models.conversation import Conversation
from app.models.audit_log import AuditLog

# Create database tables
Base.metadata.create_all(bind=engine)

# Import routes
from app.api.chat import router as chat_router
from app.api.task_routes import router as task_router
from app.api.approvals import router as approvals_router
from app.api.integrations import router as integrations_router
from app.api.users import router as users_router

app = FastAPI(
    title="TaskPilot AI API",
    description="Backend API for TaskPilot AI Agent Workspace",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(task_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(approvals_router, prefix="/api/approvals", tags=["Approvals"])
app.include_router(integrations_router, prefix="/api/integrations", tags=["Integrations"])

@app.get("/")
def read_root():
    return {
        "message": "Welcome to TaskPilot AI API!",
        "status": "healthy",
        "version": "1.0.0"
    }
