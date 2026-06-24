from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    user_message: str
    chat_history: List[Dict[str, str]] = Field(default_factory=list)
    plan_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    current_task_index: int = 0
    execution_results: List[Dict[str, Any]] = Field(default_factory=list)
    needs_approval: bool = False
    pending_approval_id: Optional[int] = None
    response_message: str = ""
