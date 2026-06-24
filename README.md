# TaskPilot AI

TaskPilot is a FastAPI + React agent workspace. The backend runs a bounded
observe–decide–act loop: after every tool call the model receives the result,
chooses the next action, can recover or select another tool, and decides when
the user’s goal is complete.

Ollama is the default local-only inference provider. The workspace checks the
running Ollama service, lists installed generation models, and lets the user
switch models without restarting the API. `qwen2.5:1.5b` is the default because
it offers reliable structured output at an interactive size.

## Agent behavior

- Dynamic next-action selection from a runtime-generated tool catalog
- Strict argument validation before any tool executes
- Replanning after both successful and failed observations
- Human approval for bookings and outbound Telegram/WhatsApp messages
- Exact, one-time execution of the action that was approved
- Pausing and resuming when essential user input is missing
- Persistent plans, observations, task progress, conversation memory, and audit logs
- Configurable iteration and memory limits to prevent runaway loops
- Deterministic degraded behavior when no model is reachable

Available tools cover exact timezone-aware time, web search, browser booking,
Telegram, WhatsApp, calendar events, and task management. Some integrations are simulated when
credentials are not configured; the tool result explicitly reports that state.

## Run locally

Create a virtual environment, install `backend/requirements.txt`, then run:

```powershell
cd backend
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

The UI expects the API at `http://127.0.0.1:8000/api`.

## Model configuration

Configuration can be changed in the UI or with environment variables:

```text
LLM_PROVIDER=ollama|gemini|fallback
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
AGENT_MAX_ITERATIONS=8
AGENT_MEMORY_MESSAGES=12
```

`GEMINI_MODEL` is deliberately configurable so deployments can select a model
available to their account without a code change.

## Tests

From the repository root:

```powershell
$env:PYTHONPATH='backend'
python -m unittest discover -s backend/tests -v
```

The tests cover multi-action adaptation, approval binding/idempotency, and
pause/resume behavior.
