"""Task lifecycle around the durable agent loop."""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.agents.approval import run_agent_loop
from app.models.conversation import Conversation
from app.models.task import Task
from app.utils.llm import query_llm


def _save_message(db: Session, role: str, content: str) -> None:
    db.add(Conversation(role=role, content=content))
    db.commit()


def generate_agent_response(user_message: str, results: List[Dict[str, Any]]) -> str:
    """Compatibility summarizer for callers with a completed execution history."""
    prompt = f"""
You are TaskPilot. Answer the user's request using only the tool observations below.
Do not claim success for failed actions. Be concise and include useful result details.
User request: {user_message}
Observations: {json.dumps(results, ensure_ascii=False)}
"""
    response = query_llm(prompt)
    if response:
        return response
    if not results:
        return "I completed the request without needing a tool."
    successful = [event for event in results if event.get("status") == "success"]
    failed = [event for event in results if event.get("status") == "failed"]
    parts = [
        f"Completed {len(successful)} action{'s' if len(successful) != 1 else ''}."
    ]
    if failed:
        parts.append(f"{len(failed)} action{'s' if len(failed) != 1 else ''} failed; see the execution trace for details.")
    return " ".join(parts)


def run_agent(
    user_message: str, db: Session, task_id: Optional[int] = None
) -> Dict[str, Any]:
    """Create a task or resume one that explicitly requested more user input."""
    _save_message(db, "user", user_message)

    if task_id is not None:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"status": "error", "agent_response": "The task to resume was not found."}
        if task.status != "needs_input":
            return {
                "status": "error",
                "task_id": task.id,
                "agent_response": "Only a task waiting for input can be resumed.",
            }
        task.description = f"{task.description}\n\nAdditional user input: {user_message}"
        task.status = "running"
        db.commit()
    else:
        task = Task(
            title=user_message[:100],
            description=user_message,
            status="pending",
            plan_data=json.dumps([]),
            current_step_index=0,
            execution_history=json.dumps([]),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

    outcome = run_agent_loop(db, task.id)
    response_text = outcome.get("agent_response") or outcome.get("message") or "The agent stopped unexpectedly."
    _save_message(db, "assistant", response_text)
    outcome["agent_response"] = response_text
    outcome.setdefault("task_id", task.id)
    if "results" in outcome:
        outcome["history"] = outcome["results"]
    return outcome
