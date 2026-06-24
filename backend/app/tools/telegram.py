import os
import requests

def send_telegram_message_tool(chat_id: str, message: str) -> dict:
    """
    Sends a message via Telegram.
    If TELEGRAM_BOT_TOKEN is set in the environment, it uses the official API.
    Otherwise, it simulates the message sending.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            response = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
            if response.status_code == 200:
                return {"status": "success", "message": "Message sent via Telegram API", "chat_id": chat_id}
            else:
                return {"status": "error", "message": f"Telegram API error: {response.text}", "chat_id": chat_id}
        except Exception as e:
            return {"status": "error", "message": f"Failed to connect to Telegram API: {str(e)}", "chat_id": chat_id}
            
    # Mock fallback
    return {
        "status": "simulated",
        "message": f"Simulated sending Telegram message to '{chat_id}': '{message}'",
        "chat_id": chat_id
    }
