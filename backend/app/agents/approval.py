"""Durable observe-decide-act loop with exact human approval checkpoints."""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.agents.planner import decide_next_action
from app.agents.router import execute_tool, requires_approval
from app.config import settings
from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation
from app.models.task import Task


def _load_json(value: Optional[str], default: Any) -> Any:
    try:
        parsed = json.loads(value) if value else default
        return parsed
    except (TypeError, json.JSONDecodeError):
        return default


def _audit(db: Session, task_id: int, action: str, details: Any) -> None:
    rendered = details if isinstance(details, str) else json.dumps(details, ensure_ascii=False)
    db.add(AuditLog(task_id=task_id, action=action, details=rendered))
    db.commit()


def _conversation_context(db: Session) -> List[Dict[str, str]]:
    rows = (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(settings.AGENT_MEMORY_MESSAGES)
        .all()
    )
    return [{"role": row.role, "content": row.content} for row in reversed(rows)]


def request_approval(
    db: Session, task_id: int, tool_name: str, tool_args: Dict[str, Any]
) -> Approval:
    """Persist the exact side effect that the user is being asked to approve."""
    approval = Approval(
        task_id=task_id,
        tool_name=tool_name,
        tool_args=json.dumps(tool_args, ensure_ascii=False, sort_keys=True),
        status="pending",
    )
    db.add(approval)
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.status = "awaiting_approval"
    db.commit()
    db.refresh(approval)
    _audit(
        db,
        task_id,
        "REQUEST_APPROVAL",
        {"approval_id": approval.id, "tool": tool_name, "args": tool_args},
    )
    return approval


def _record_tool_result(
    db: Session,
    task: Task,
    plan: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
    step: Dict[str, Any],
    approval_id: Optional[int] = None,
) -> None:
    tool_name = step["tool"]
    tool_args = step.get("args", {})
    _audit(
        db,
        task.id,
        "EXECUTE_TOOL_START",
        {"tool": tool_name, "args": tool_args, "approval_id": approval_id},
    )
    execution = execute_tool(tool_name, tool_args)
    event = {
        "iteration": len(history) + 1,
        "step_index": task.current_step_index,
        "step_title": step.get("title", f"Run {tool_name}"),
        "tool": tool_name,
        "args": tool_args,
        "rationale": step.get("rationale", ""),
        "status": "success" if execution["ok"] else "failed",
        "result": execution.get("output"),
        "error": execution.get("error"),
        "approval_id": approval_id,
    }
    history.append(event)
    if task.current_step_index < len(plan):
        plan[task.current_step_index]["status"] = event["status"]
    task.current_step_index += 1
    task.plan_data = json.dumps(plan, ensure_ascii=False)
    task.execution_history = json.dumps(history, ensure_ascii=False)
    db.commit()
    _audit(
        db,
        task.id,
        "EXECUTE_TOOL_SUCCESS" if execution["ok"] else "EXECUTE_TOOL_FAILURE",
        {"tool": tool_name, "error": execution.get("error")},
    )


def _consume_approval(
    db: Session,
    task: Task,
    approval_id: int,
    plan: List[Dict[str, Any]],
    history: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    approval = (
        db.query(Approval)
        .filter(Approval.id == approval_id, Approval.task_id == task.id)
        .first()
    )
    if not approval or approval.status != "approved":
        return {"status": "error", "message": "The exact approval is missing or is no longer valid."}

    # Claim the approval before the external call so concurrent resumes cannot execute it twice.
    approval.status = "executing"
    db.commit()

    args = _load_json(approval.tool_args, {})
    step = (
        plan[task.current_step_index]
        if task.current_step_index < len(plan)
        else {
            "title": f"Run approved {approval.tool_name}",
            "tool": approval.tool_name,
            "args": args,
        }
    )
    # Bind execution to the immutable approval record, not to regenerated model output.
    step["tool"] = approval.tool_name
    step["args"] = args
    if task.current_step_index >= len(plan):
        plan.append(step)
    _record_tool_result(db, task, plan, history, step, approval.id)
    approval.status = "executed"
    db.commit()
    return None


def run_agent_loop(
    db: Session, task_id: int, approved_approval_id: Optional[int] = None
) -> Dict[str, Any]:
    """Run bounded reasoning cycles, pausing only for input or an external side effect."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return {"status": "error", "message": "Task not found"}

    previous_status = task.status

    plan = _load_json(task.plan_data, [])
    history = _load_json(task.execution_history, [])
    if not isinstance(plan, list):
        plan = []
    if not isinstance(history, list):
        history = []

    task.status = "running"
    db.commit()

    if approved_approval_id is not None:
        approval_error = _consume_approval(
            db, task, approved_approval_id, plan, history
        )
        if approval_error:
            task.status = previous_status
            db.commit()
            return approval_error

    while len(history) < settings.AGENT_MAX_ITERATIONS:
        remaining = settings.AGENT_MAX_ITERATIONS - len(history)
        decision = decide_next_action(
            task.description or task.title,
            history,
            _conversation_context(db),
            remaining,
        )
        _audit(
            db,
            task.id,
            "AGENT_DECISION",
            {
                "action": decision.action,
                "tool": decision.tool,
                "rationale": decision.rationale,
            },
        )

        if decision.action == "final":
            task.status = "completed"
            db.commit()
            _audit(db, task.id, "TASK_COMPLETED", "The agent determined the goal was satisfied.")
            return {
                "status": "completed",
                "task_id": task.id,
                "results": history,
                "agent_response": decision.response,
            }

        if decision.action == "ask_user":
            task.status = "needs_input"
            db.commit()
            _audit(db, task.id, "WAITING_FOR_INPUT", decision.response)
            return {
                "status": "needs_input",
                "task_id": task.id,
                "results": history,
                "agent_response": decision.response,
            }

        step = {
            "title": decision.title,
            "tool": decision.tool,
            "args": decision.args,
            "rationale": decision.rationale,
            "status": "pending",
        }
        plan.append(step)
        task.plan_data = json.dumps(plan, ensure_ascii=False)
        db.commit()

        if requires_approval(decision.tool or ""):
            pending = request_approval(db, task.id, decision.tool or "", decision.args)
            return {
                "status": "awaiting_approval",
                "task_id": task.id,
                "approval_id": pending.id,
                "tool_name": decision.tool,
                "tool_args": decision.args,
                "results": history,
                "agent_response": (
                    f"I’m ready to {decision.title.lower()}. Please review and approve this external action."
                ),
            }

        _record_tool_result(db, task, plan, history, step)

    task.status = "failed"
    db.commit()
    _audit(db, task.id, "ITERATION_LIMIT_REACHED", {"limit": settings.AGENT_MAX_ITERATIONS})
    return {
        "status": "failed",
        "task_id": task.id,
        "results": history,
        "agent_response": (
            f"I stopped after {settings.AGENT_MAX_ITERATIONS} action cycles to avoid an unsafe loop. "
            "The execution trace contains everything completed so far."
        ),
    }
