import requests
from app.config import settings

def call_ollama(prompt: str, json_mode: bool = False) -> str:
    url = f"{settings.OLLAMA_API_URL.rstrip('/')}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0.15 if json_mode else 0.35,
            "num_ctx": 8192,
            "num_predict": 900 if json_mode else 1400,
        },
    }
    if json_mode:
        payload["format"] = "json"
        payload["think"] = False
    try:
        response = requests.post(url, json=payload, timeout=(5, 60))
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            print(f"Ollama returned error code {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Ollama connection error: {str(e)}")
    return ""

def call_gemini(prompt: str) -> str:
    if not settings.GEMINI_API_KEY:
        print("Gemini API key is not configured.")
        return ""
    try:
        try:
            from google import genai

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )
        except ImportError:
            # Compatibility for existing environments until requirements are reinstalled.
            import google.generativeai as legacy_genai

            legacy_genai.configure(api_key=settings.GEMINI_API_KEY)
            model = legacy_genai.GenerativeModel(settings.GEMINI_MODEL)
            response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API connection error: {str(e)}")
    return ""

def query_llm(prompt: str, json_mode: bool = False) -> str:
    """
    Unified entry point to query the active LLM provider.
    """
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "ollama":
        return call_ollama(prompt, json_mode=json_mode)
            
    elif provider == "gemini":
        result = call_gemini(prompt)
        if result:
            return result
        return ""

    elif provider == "fallback":
        result = call_ollama(prompt, json_mode=json_mode)
        if result:
            return result
        return call_gemini(prompt) if settings.GEMINI_API_KEY else ""
        
    return ""
