from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.database.database import get_db
from app.models.conversation import Conversation
from app.agents.graph import run_agent

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    task_id: Optional[int] = None

class ChatResponse(BaseModel):
    status: str
    task_id: Optional[int] = None
    approval_id: Optional[int] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    agent_response: str
    history: Optional[List[Dict[str, Any]]] = None

@router.post("/", response_model=ChatResponse)
def chat_with_agent(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        result = run_agent(request.message, db, request.task_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

@router.get("/history")
def get_chat_history(db: Session = Depends(get_db)):
    try:
        conversations = db.query(Conversation).order_by(Conversation.created_at.asc()).all()
        return [
            {
                "id": c.id,
                "role": c.role,
                "content": c.content,
                "created_at": c.created_at
            }
            for c in conversations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {str(e)}")

@router.delete("/history")
def clear_chat_history(db: Session = Depends(get_db)):
    try:
        db.query(Conversation).delete()
        db.commit()
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear chat history: {str(e)}")
