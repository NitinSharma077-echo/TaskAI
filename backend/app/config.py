import os
from dotenv import load_dotenv

load_dotenv()


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
        return value if value > 0 else default
    except ValueError:
        return default


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "TaskPilot AI")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./taskpilot.db")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OLLAMA_API_URL: str = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # 'ollama', 'gemini', or 'fallback'
    AGENT_MAX_ITERATIONS: int = _positive_int("AGENT_MAX_ITERATIONS", 8)
    AGENT_MEMORY_MESSAGES: int = _positive_int("AGENT_MEMORY_MESSAGES", 12)

settings = Settings()
