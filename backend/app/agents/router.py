"""Tool registry, argument validation, and safe execution for the agent."""

from typing import Any, Callable, Dict, List, Type

from pydantic import BaseModel, Field, ValidationError

from app.tools.browser_booking import book_appointment_tool
from app.tools.calendar import add_calendar_event_tool, list_calendar_events_tool
from app.tools.task_manager import (
    create_task_tool,
    list_tasks_tool,
    update_task_status_tool,
)
from app.tools.current_time import current_time_tool
from app.tools.telegram import send_telegram_message_tool
from app.tools.web_search import web_search_tool
from app.tools.whatsapp import send_whatsapp_message_tool


class StrictArgs(BaseModel):
    class Config:
        extra = "forbid"


class WebSearchArgs(StrictArgs):
    query: str = Field(min_length=1, max_length=500)


class CurrentTimeArgs(StrictArgs):
    timezone: str | None = None


class BookingArgs(StrictArgs):
    service_name: str = Field(min_length=1)
    date: str = Field(min_length=1)
    time_slot: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)


class TelegramArgs(StrictArgs):
    chat_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4096)


class WhatsAppArgs(StrictArgs):
    phone_number: str = Field(min_length=3)
    message: str = Field(min_length=1, max_length=4096)


class CalendarAddArgs(StrictArgs):
    summary: str = Field(min_length=1)
    start_time: str = Field(min_length=1)
    end_time: str | None = None
    description: str = ""


class EmptyArgs(StrictArgs):
    pass


class TaskCreateArgs(StrictArgs):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class TaskUpdateArgs(StrictArgs):
    task_id: int = Field(gt=0)
    status: str = Field(pattern="^(pending|running|completed|failed|cancelled)$")


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        args_model: Type[BaseModel],
        handler: Callable[..., Any],
        requires_approval: bool = False,
    ):
        self.name = name
        self.description = description
        self.args_model = args_model
        self.handler = handler
        self.requires_approval = requires_approval


TOOL_REGISTRY: Dict[str, ToolDefinition] = {
    "current_time": ToolDefinition(
        "current_time",
        "Get the exact current date and time, optionally in an IANA timezone such as Asia/Kolkata.",
        CurrentTimeArgs,
        current_time_tool,
    ),
    "web_search": ToolDefinition(
        "web_search", "Search the web for current information.", WebSearchArgs, web_search_tool
    ),
    "browser_booking": ToolDefinition(
        "browser_booking",
        "Book an appointment or reservation using the supplied details.",
        BookingArgs,
        book_appointment_tool,
        True,
    ),
    "telegram": ToolDefinition(
        "telegram", "Send a Telegram message.", TelegramArgs, send_telegram_message_tool, True
    ),
    "whatsapp": ToolDefinition(
        "whatsapp", "Send a WhatsApp message.", WhatsAppArgs, send_whatsapp_message_tool, True
    ),
    "calendar_add": ToolDefinition(
        "calendar_add", "Create a calendar event.", CalendarAddArgs, add_calendar_event_tool
    ),
    "calendar_list": ToolDefinition(
        "calendar_list", "List existing calendar events.", EmptyArgs, list_calendar_events_tool
    ),
    "task_create": ToolDefinition(
        "task_create", "Create a task record.", TaskCreateArgs, create_task_tool
    ),
    "task_update": ToolDefinition(
        "task_update", "Update the status of a task record.", TaskUpdateArgs, update_task_status_tool
    ),
    "task_list": ToolDefinition(
        "task_list", "List task records.", EmptyArgs, list_tasks_tool
    ),
}


def _schema(model: Type[BaseModel]) -> Dict[str, Any]:
    if hasattr(model, "model_json_schema"):
        return model.model_json_schema()
    return model.schema()


def tool_catalog() -> List[Dict[str, Any]]:
    """Return the model-facing tool catalog from the same registry used at runtime."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "requires_approval": tool.requires_approval,
            "arguments": _schema(tool.args_model),
        }
        for tool in TOOL_REGISTRY.values()
    ]


def agent_tool_catalog() -> List[Dict[str, Any]]:
    """Compact catalog for smaller local models with limited context capacity."""
    catalog = []
    for tool in TOOL_REGISTRY.values():
        schema = _schema(tool.args_model)
        required = set(schema.get("required", []))
        arguments = {}
        for name, details in schema.get("properties", {}).items():
            argument = {"type": details.get("type", "string")}
            if name in required:
                argument["required"] = True
            if details.get("enum"):
                argument["allowed"] = details["enum"]
            arguments[name] = argument
        catalog.append(
            {
                "name": tool.name,
                "description": tool.description,
                "approval_required": tool.requires_approval,
                "arguments": arguments,
            }
        )
    return catalog


def requires_approval(tool_name: str) -> bool:
    tool = TOOL_REGISTRY.get(tool_name)
    return bool(tool and tool.requires_approval)


def validate_tool_call(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        raise ValueError(f"Tool '{tool_name}' is not recognized")
    try:
        validated = tool.args_model(**(args or {}))
    except ValidationError as exc:
        raise ValueError(f"Invalid arguments for '{tool_name}': {exc}") from exc
    if hasattr(validated, "model_dump"):
        return validated.model_dump(exclude_none=True)
    return validated.dict(exclude_none=True)


def execute_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and execute one tool call, always returning a normalized observation."""
    try:
        validated_args = validate_tool_call(tool_name, args)
        tool = TOOL_REGISTRY[tool_name]
        output = tool.handler(**validated_args)
        if tool_name in {"calendar_list", "task_list"}:
            output = {"items": output}
        reported_failure = isinstance(output, dict) and (
            output.get("status") == "error" or bool(output.get("error"))
        )
        return {
            "ok": not reported_failure,
            "tool": tool_name,
            "output": output,
            "error": output.get("error") if isinstance(output, dict) else None,
        }
    except Exception as exc:
        return {"ok": False, "tool": tool_name, "output": None, "error": str(exc)}
