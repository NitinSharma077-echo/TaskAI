import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.database.database import get_db
from app.models.approval import Approval
from app.models.task import Task
from app.models.conversation import Conversation
from app.agents.approval import run_agent_loop

router = APIRouter()

class ApprovalResponse(BaseModel):
    id: int
    task_id: Optional[int]
    tool_name: str
    tool_args: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ApprovalResponse])
def get_approvals(db: Session = Depends(get_db)):
    return db.query(Approval).order_by(Approval.created_at.desc()).all()

@router.post("/{approval_id}/approve")
def approve_action(approval_id: int, db: Session = Depends(get_db)):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval request already {approval.status}")
        
    approval.status = "approved"
    db.commit()
    
    # Resume the agent loop
    task_id = approval.task_id
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Associated task not found")
        
    outcome = run_agent_loop(db, task_id, approved_approval_id=approval_id)
    response_text = outcome.get("agent_response") or outcome.get("message") or "Resumed execution failed."
    db.add(Conversation(role="assistant", content=response_text))
    db.commit()
    outcome["agent_response"] = response_text
    if "results" in outcome:
        outcome["history"] = outcome["results"]
    return outcome

@router.post("/{approval_id}/deny")
def deny_action(approval_id: int, db: Session = Depends(get_db)):
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail=f"Approval request already {approval.status}")
        
    approval.status = "denied"
    db.commit()
    
    # Fail the task
    task_id = approval.task_id
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.status = "failed"
        db.commit()
        
    response_text = f"Action '{approval.tool_name}' was denied. Execution stopped."
    agent_msg = Conversation(role="assistant", content=response_text)
    db.add(agent_msg)
    db.commit()
    
    return {
        "status": "denied",
        "task_id": task_id,
        "agent_response": response_text
    }
