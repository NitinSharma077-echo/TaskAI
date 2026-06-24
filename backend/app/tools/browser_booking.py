import time

def book_appointment_tool(service_name: str, date: str, time_slot: str, name: str, email: str) -> dict:
    """
    Simulates a browser-based booking automation flow.
    Logs step-by-step navigation and returns booking status and confirmation.
    """
    steps = [
        "Opening booking portal...",
        f"Searching for service: {service_name} on {date} at {time_slot}",
        "Selecting available slot...",
        f"Entering guest details: Name={name}, Email={email}",
        "Navigating to confirmation page...",
        "Solving booking captcha (mock)...",
        "Booking successful!"
    ]
    
    # Simulate a small delay for realistic logging
    execution_steps = []
    for step in steps:
        execution_steps.append({"step": step, "timestamp": time.time()})
    
    confirmation_code = f"BK-{int(time.time()) % 1000000:06d}"
    
    return {
        "status": "success",
        "service": service_name,
        "date": date,
        "time": time_slot,
        "confirmation_code": confirmation_code,
        "execution_steps": execution_steps
    }
