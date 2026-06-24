import os
import json
from typing import Literal

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.config import settings as runtime_settings

router = APIRouter()

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "integration_config.json")

class IntegrationSettings(BaseModel):
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    whatsapp_phone_number: str = ""
    google_calendar_configured: bool = False
    llm_provider: Literal["ollama", "gemini", "fallback"] = "ollama"
    ollama_api_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

def _load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "whatsapp_phone_number": "",
            "google_calendar_configured": False,
            "llm_provider": runtime_settings.LLM_PROVIDER,
            "ollama_api_url": runtime_settings.OLLAMA_API_URL,
            "ollama_model": runtime_settings.OLLAMA_MODEL,
            "gemini_api_key": "",
            "gemini_model": runtime_settings.GEMINI_MODEL,
        }
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def _apply_runtime_config(config: dict) -> None:
    runtime_settings.LLM_PROVIDER = config.get("llm_provider", runtime_settings.LLM_PROVIDER)
    runtime_settings.OLLAMA_API_URL = config.get("ollama_api_url", runtime_settings.OLLAMA_API_URL)
    runtime_settings.OLLAMA_MODEL = config.get("ollama_model", runtime_settings.OLLAMA_MODEL)
    runtime_settings.GEMINI_MODEL = config.get("gemini_model", runtime_settings.GEMINI_MODEL)
    if config.get("gemini_api_key"):
        runtime_settings.GEMINI_API_KEY = config["gemini_api_key"]
    if config.get("telegram_bot_token"):
        os.environ["TELEGRAM_BOT_TOKEN"] = config["telegram_bot_token"]


_apply_runtime_config(_load_config())


@router.get("/ollama/status")
def get_ollama_status():
    """Report local Ollama health and installed generation models."""
    url = f"{runtime_settings.OLLAMA_API_URL.rstrip('/')}/api/tags"
    try:
        response = requests.get(url, timeout=3)
        response.raise_for_status()
        raw_models = response.json().get("models", [])
        models = []
        for item in raw_models:
            capabilities = item.get("capabilities", [])
            if "embedding" in capabilities and "completion" not in capabilities:
                continue
            details = item.get("details") or {}
            models.append(
                {
                    "name": item.get("name"),
                    "size": item.get("size"),
                    "parameter_size": details.get("parameter_size"),
                    "quantization": details.get("quantization_level"),
                    "capabilities": capabilities,
                }
            )
        return {
            "connected": True,
            "url": runtime_settings.OLLAMA_API_URL,
            "active_model": runtime_settings.OLLAMA_MODEL,
            "models": models,
        }
    except Exception as exc:
        return {
            "connected": False,
            "url": runtime_settings.OLLAMA_API_URL,
            "active_model": runtime_settings.OLLAMA_MODEL,
            "models": [],
            "error": str(exc),
        }

@router.get("/")
def get_integrations():
    config = _load_config()
    # Mask token
    token = config.get("telegram_bot_token", "")
    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else token
    return {
        "telegram_bot_token": masked_token,
        "telegram_chat_id": config.get("telegram_chat_id", ""),
        "whatsapp_phone_number": config.get("whatsapp_phone_number", ""),
        "google_calendar_configured": config.get("google_calendar_configured", False),
        "llm_provider": config.get("llm_provider", runtime_settings.LLM_PROVIDER),
        "ollama_api_url": config.get("ollama_api_url", runtime_settings.OLLAMA_API_URL),
        "ollama_model": config.get("ollama_model", runtime_settings.OLLAMA_MODEL),
        "gemini_api_key": "configured" if config.get("gemini_api_key") else "",
        "gemini_model": config.get("gemini_model", runtime_settings.GEMINI_MODEL),
    }

@router.post("/")
def update_integrations(settings: IntegrationSettings):
    config = _load_config()
    
    # Only update if a value is provided and not masked
    if settings.telegram_bot_token and "..." not in settings.telegram_bot_token:
        config["telegram_bot_token"] = settings.telegram_bot_token
        # Update env var in active process
        os.environ["TELEGRAM_BOT_TOKEN"] = settings.telegram_bot_token
        
    config["telegram_chat_id"] = settings.telegram_chat_id
    config["whatsapp_phone_number"] = settings.whatsapp_phone_number
    config["google_calendar_configured"] = settings.google_calendar_configured
    config["llm_provider"] = settings.llm_provider
    config["ollama_api_url"] = settings.ollama_api_url
    config["ollama_model"] = settings.ollama_model
    config["gemini_model"] = settings.gemini_model
    if settings.gemini_api_key and settings.gemini_api_key != "configured":
        config["gemini_api_key"] = settings.gemini_api_key

    _save_config(config)
    _apply_runtime_config(config)
    return {"message": "Integrations updated successfully"}
