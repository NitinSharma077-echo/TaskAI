"""Model-driven next-action selection for TaskPilot's bounded agent loop."""

import json
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.agents.router import agent_tool_catalog, validate_tool_call
from app.utils.llm import query_llm


class AgentDecision(BaseModel):
    action: Literal["tool", "final", "ask_user"]
    title: str = ""
    tool: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""
    response: str = ""


def _parse_json_object(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError("The model did not return a JSON object")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("The model decision must be a JSON object")
    return value


def _model_validate(data: Dict[str, Any]) -> AgentDecision:
    if hasattr(AgentDecision, "model_validate"):
        return AgentDecision.model_validate(data)
    return AgentDecision.parse_obj(data)


def _recent_observations(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    compact = []
    for event in history[-10:]:
        compact.append(
            {
                "iteration": event.get("iteration"),
                "title": event.get("step_title"),
                "tool": event.get("tool"),
                "args": event.get("args"),
                "status": event.get("status"),
                "result": event.get("result"),
            }
        )
    return compact


def decide_next_action(
    goal: str,
    history: List[Dict[str, Any]],
    conversation: List[Dict[str, str]],
    iterations_remaining: int,
) -> AgentDecision:
    """Select exactly one next action after observing all prior tool results."""
    prompt = f"""
You are the decision engine for TaskPilot, an autonomous but safety-conscious assistant.

USER GOAL:
{goal}

RECENT CONVERSATION:
{json.dumps(conversation[-12:], ensure_ascii=False)}

OBSERVATIONS FROM ACTIONS ALREADY TAKEN:
{json.dumps(_recent_observations(history), ensure_ascii=False)}

AVAILABLE TOOLS (this catalog is authoritative):
{json.dumps(agent_tool_catalog(), ensure_ascii=False)}

You have {iterations_remaining} action cycles remaining. Choose exactly one next action.

Operating rules:
- Inspect observations before acting. Never repeat a successful action.
- Use a tool only when it materially advances the user's goal.
- If a tool failed, diagnose from its observation and either correct the arguments, use an alternative, ask the user, or finish honestly.
- Ask the user only when required information cannot be inferred safely.
- Actions with external side effects will be approval-gated by the runtime.
- Finish as soon as the goal is satisfied. Never claim an action succeeded unless an observation says it did.
- Keep rationale to one short operational sentence; do not provide hidden reasoning.

The "action" value MUST be exactly "tool", "ask_user", or "final". A tool name
belongs in the separate "tool" field and must never be used as the action value.

Return ONLY one JSON object in one of these forms:
{{"action":"tool","title":"short step title","tool":"tool name","args":{{}},"rationale":"short reason"}}
{{"action":"ask_user","response":"specific question","rationale":"what is missing"}}
{{"action":"final","response":"concise answer grounded in observations","rationale":"goal is complete"}}

Example for a search request:
{{"action":"tool","title":"Search for Pune weather","tool":"web_search","args":{{"query":"current Pune weather"}},"rationale":"Current information requires search."}}
"""
    raw = query_llm(prompt, json_mode=True)
    if raw:
        try:
            decision = _model_validate(_parse_json_object(raw))
            if decision.action == "tool":
                if not decision.tool:
                    raise ValueError("Tool action omitted the tool name")
                decision.args = validate_tool_call(decision.tool, decision.args)
                if not decision.title:
                    decision.title = f"Run {decision.tool}"
            elif not decision.response.strip():
                raise ValueError(f"{decision.action} action omitted its response")

            # Explicit user verbs are cheap to recognize and should not be second-guessed
            # by a small local model. The model still controls subsequent replanning.
            deterministic = _fallback_decision(goal, history)
            if not history and deterministic.action == "tool":
                if decision.action == "ask_user" or (
                    decision.action == "tool" and decision.tool != deterministic.tool
                ):
                    return deterministic
            return decision
        except Exception as exc:
            # A malformed model turn becomes an observation-quality fallback, not a crash.
            print(f"Agent decision validation failed: {exc}. Output: {raw}")

    return _fallback_decision(goal, history)


def _fallback_decision(goal: str, history: List[Dict[str, Any]]) -> AgentDecision:
    """Deterministic degraded mode when no model provider is available."""
    if history:
        last = history[-1]
        result = last.get("result", {})
        if last.get("status") == "success":
            return AgentDecision(
                action="final",
                response=f"Completed: {last.get('step_title', last.get('tool', 'requested action'))}. Result: {json.dumps(result, ensure_ascii=False)}",
                rationale="The deterministic action completed successfully.",
            )
        return AgentDecision(
            action="final",
            response=f"I could not complete the action. {last.get('error') or 'The tool reported a failure.'}",
            rationale="The available action failed and no model is connected to recover.",
        )

    lower = goal.lower()
    if "current time" in lower or re.search(r"\bwhat time\b", lower):
        timezone = None
        india_markers = ("pune", "india", "mumbai", "delhi", "kolkata", "chennai", "bengaluru", "bangalore")
        if any(marker in lower for marker in india_markers):
            timezone = "Asia/Kolkata"
        return AgentDecision(
            action="tool",
            title=f"Get current time{f' in {timezone}' if timezone else ''}",
            tool="current_time",
            args={"timezone": timezone} if timezone else {},
            rationale="An exact clock reading should come from the deterministic time tool.",
        )
    if any(word in lower for word in ("search", "find", "lookup", "google", "weather")):
        query = re.sub(r"^(search(?: for)?|find|lookup|google)\s+", "", goal, flags=re.I).strip()
        return AgentDecision(
            action="tool",
            title=f"Search for {query}",
            tool="web_search",
            args={"query": query or goal},
            rationale="The request explicitly asks for information retrieval.",
        )
    if "list" in lower and "calendar" in lower:
        return AgentDecision(action="tool", title="List calendar events", tool="calendar_list")
    if "list" in lower and "task" in lower:
        return AgentDecision(action="tool", title="List tasks", tool="task_list")
    if "telegram" in lower:
        match = re.search(r"telegram to\s+(.+?)\s+saying\s+(.+)", goal, re.I)
        if match:
            return AgentDecision(
                action="tool",
                title="Send Telegram message",
                tool="telegram",
                args={"chat_id": match.group(1).strip(), "message": match.group(2).strip()},
            )
        return AgentDecision(
            action="ask_user",
            response="What Telegram chat ID and exact message should I use?",
            rationale="The destination or message is missing.",
        )
    if "whatsapp" in lower:
        match = re.search(r"whatsapp to\s+([+\d ()-]+?)\s+saying\s+(.+)", goal, re.I)
        if match:
            return AgentDecision(
                action="tool",
                title="Send WhatsApp message",
                tool="whatsapp",
                args={"phone_number": match.group(1).strip(), "message": match.group(2).strip()},
            )
        return AgentDecision(
            action="ask_user",
            response="What WhatsApp number and exact message should I use?",
            rationale="The destination or message is missing.",
        )
    return AgentDecision(
        action="ask_user",
        response=(
            "I need a little more detail about the outcome you want. You can ask me to search, "
            "manage tasks or calendar events, send a message, or make a booking."
        ),
        rationale="No connected model is available and the intended action is ambiguous.",
    )


def plan_user_request(user_message: str) -> list:
    """Backward-compatible preview of the first dynamically selected action."""
    decision = decide_next_action(user_message, [], [], 1)
    if decision.action != "tool":
        return []
    return [{"title": decision.title, "tool": decision.tool, "args": decision.args}]
