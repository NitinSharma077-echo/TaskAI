from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.database.database import Base

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    tool_name = Column(String(100), nullable=False)
    tool_args = Column(Text, nullable=False)  # JSON-serialized arguments
    status = Column(String(50), default="pending")  # pending, approved, denied, executing, executed
    created_at = Column(DateTime, default=datetime.utcnow)
