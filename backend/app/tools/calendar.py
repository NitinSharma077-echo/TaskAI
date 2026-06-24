import os
import json
from datetime import datetime

CALENDAR_FILE = os.path.join(os.path.dirname(__file__), "calendar_events.json")

def _load_events() -> list:
    if not os.path.exists(CALENDAR_FILE):
        return []
    try:
        with open(CALENDAR_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _save_events(events: list):
    with open(CALENDAR_FILE, "w") as f:
        json.dump(events, f, indent=4)

def add_calendar_event_tool(summary: str, start_time: str, end_time: str = None, description: str = "") -> dict:
    events = _load_events()
    new_event = {
        "id": len(events) + 1,
        "summary": summary,
        "start_time": start_time,
        "end_time": end_time or start_time,
        "description": description,
        "created_at": datetime.utcnow().isoformat()
    }
    events.append(new_event)
    _save_events(events)
    return {"message": "Event added successfully", "event": new_event}

def list_calendar_events_tool() -> list:
    return _load_events()
