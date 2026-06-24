"""Deterministic local and timezone-aware clock tool."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def current_time_tool(timezone: str | None = None) -> dict:
    try:
        now = datetime.now(ZoneInfo(timezone)) if timezone else datetime.now().astimezone()
    except ZoneInfoNotFoundError:
        return {
            "status": "error",
            "error": f"Unknown IANA timezone: {timezone}",
        }

    return {
        "status": "success",
        "timezone": timezone or str(now.tzinfo),
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "utc_offset": now.strftime("%z"),
    }
