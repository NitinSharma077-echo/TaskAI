from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="pending")  # pending, running, completed, failed, awaiting_approval, needs_input
    plan_data = Column(Text, nullable=True)  # JSON list of planned steps
    current_step_index = Column(Integer, default=0)
    execution_history = Column(Text, nullable=True)  # JSON list of executed step results
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
