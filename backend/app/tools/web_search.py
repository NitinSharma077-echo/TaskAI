import requests
import urllib.parse

def web_search_tool(query: str) -> dict:
    """
    Search the web for a query.
    Uses DuckDuckGo Instant Answer API if possible, with a fallback to mock results.
    """
    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                return {
                    "query": query,
                    "result": abstract,
                    "source": data.get("AbstractURL", "DuckDuckGo")
                }
    except Exception:
        pass
    
    # Fallback/Mock results for common queries
    query_lower = query.lower()
    if "weather" in query_lower:
        result = "Current weather in the requested location is 22°C, mostly cloudy with light rain showers. Humidity 65%, Wind NW at 12 km/h."
    elif "flight" in query_lower or "booking" in query_lower:
        result = "Found flights: AA-102 departing at 10:00 AM ($250), UA-405 departing at 2:30 PM ($210). Hotel options: Grand Plaza Hotel ($150/night), City Center Inn ($95/night)."
    elif "time" in query_lower or "date" in query_lower:
        result = "The current system date and time is synchronized. Time zone is UTC+5:30."
    else:
        result = f"Search result for '{query}': Found 1,240 articles. The query refers to a topic commonly discussed in technology and project management. TaskPilot AI suggests checking official docs for detailed steps."

    return {
        "query": query,
        "result": result,
        "source": "TaskPilot Search Engine (Mock Fallback)"
    }
