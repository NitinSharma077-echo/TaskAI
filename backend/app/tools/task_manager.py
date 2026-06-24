from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.task import Task
from app.models.audit_log import AuditLog

def create_task_tool(title: str, description: str = None) -> dict:
    db: Session = SessionLocal()
    try:
        db_task = Task(title=title, description=description, status="pending")
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        
        # Log the action
        log = AuditLog(task_id=db_task.id, action="CREATE_TASK", details=f"Task '{title}' created via tool.")
        db.add(log)
        db.commit()
        
        return {"id": db_task.id, "title": db_task.title, "status": db_task.status}
    finally:
        db.close()

def update_task_status_tool(task_id: int, status: str) -> dict:
    db: Session = SessionLocal()
    try:
        db_task = db.query(Task).filter(Task.id == task_id).first()
        if not db_task:
            return {"error": f"Task with ID {task_id} not found"}
        
        old_status = db_task.status
        db_task.status = status
        db.commit()
        
        # Log the action
        log = AuditLog(task_id=task_id, action="UPDATE_STATUS", details=f"Status changed from {old_status} to {status} via tool.")
        db.add(log)
        db.commit()
        
        return {"id": db_task.id, "title": db_task.title, "status": db_task.status}
    finally:
        db.close()

def list_tasks_tool() -> list:
    db: Session = SessionLocal()
    try:
        tasks = db.query(Task).all()
        return [{"id": t.id, "title": t.title, "description": t.description, "status": t.status} for t in tasks]
    finally:
        db.close()
