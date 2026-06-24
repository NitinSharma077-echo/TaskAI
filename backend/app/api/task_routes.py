import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.database.database import get_db
from app.models.task import Task
from app.models.audit_log import AuditLog
from app.models.approval import Approval

router = APIRouter()

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    current_step_index: int
    plan_data: Optional[str] = None
    execution_history: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[TaskResponse])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.created_at.desc()).all()

@router.post("/", response_model=TaskResponse)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    task = Task(
        title=task_in.title,
        description=task_in.description,
        status="pending",
        plan_data=json.dumps([]),
        current_step_index=0,
        execution_history=json.dumps([])
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Delete associated approvals and logs
    db.query(Approval).filter(Approval.task_id == task_id).delete()
    db.query(AuditLog).filter(AuditLog.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} and its logs deleted successfully"}

@router.get("/{task_id}/logs")
def get_task_logs(task_id: int, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(AuditLog.task_id == task_id).order_by(AuditLog.created_at.asc()).all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "details": l.details,
            "created_at": l.created_at
        }
        for l in logs
    ]
