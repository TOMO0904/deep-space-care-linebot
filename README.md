**English** | [日本語](README.ja.md)

# Deep Space Care — LINE Bot Prototype

A first-line mental-care chatbot for LINE, designed for a hypothetical scenario: crews in isolated, high-latency environments such as deep-space missions. It is a **prototype / demo**, not a medical product and not a substitute for diagnosis or treatment.

## Problem

When a crew cannot rely on a constant link to ground support, first-line emotional support has to work on board. A bot in that setting must also be safe: it must never let a generative model improvise when someone expresses a crisis.

## Solution

- Normal messages get an **empathy → small self-care step → follow-up question** reply, generated with Google Gemini.
- Crisis expressions are detected **before** any text reaches the generative model, and the user is guided to human on-board support instead.
- Mission-specific "on-board mode" commands: status check, communication status, on-board support contacts, and a send-to-ground queue stored in SQLite for sync after the link recovers.
- Falls back to fixed fail-safe replies if Gemini is slow or unavailable (configurable timeout).
- Runs in a keyless demo mode (fixed replies) so it can be tried without any API key.

## Features

- LINE Messaging API webhook with **HMAC-SHA256 signature verification** on the raw request body
- Crisis-expression pre-filter and human-support handoff
- Conversation history kept in SQLite
- Mission parameters (`MISSION_NAME`, `COMM_DELAY_MINUTES`, `MEDICAL_ROLE`, `SAFE_MODULE`, `GEMINI_TIMEOUT_MS`) set via environment variables
- `/demo` HTTP endpoint for testing without LINE
- Automated tests (`pytest`), Dockerfile and `render.yaml` for deployment

## Tech stack

Python · FastAPI · Uvicorn · httpx · LINE Messaging API · Google Gemini API · SQLite · pytest · Docker / Render

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env             # fill in keys; leave GEMINI_API_KEY empty for demo mode
uvicorn app:app --reload --port 8000
```

Try the demo endpoint:

```bash
curl -X POST http://localhost:8000/demo -H "Content-Type: application/json" \
  -d '{"text":"I cannot sleep and Earth feels far away"}'
```

To connect LINE: create a Messaging API channel, set the channel secret and access token in `.env`, expose the app over HTTPS, and set the webhook URL to `https://<your-host>/callback`. Never commit tokens or API keys.

Run the tests with `pytest -q`.

## Scope and safety

- Does: listening, naming emotions, short breathing/grounding suggestions, escalation to human support.
- Does not: diagnose, treat, give medication advice, or replace emergency services.
- A real deployment would need research consent, log anonymisation, retention rules and expert review.

## Status

Prototype built as a concept demo. Detailed on-board mode notes, setup guide and a 5-minute presentation script (Japanese) are in [docs/DETAILS.ja.md](docs/DETAILS.ja.md).
