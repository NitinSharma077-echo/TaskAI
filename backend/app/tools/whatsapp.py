import os

def send_whatsapp_message_tool(phone_number: str, message: str) -> dict:
    """
    Sends a message via WhatsApp.
    If WhatsApp keys are configured, it could call an API, otherwise it simulates.
    """
    # Mock fallback
    return {
        "status": "simulated",
        "message": f"Simulated sending WhatsApp message to '{phone_number}': '{message}'",
        "phone_number": phone_number
    }
