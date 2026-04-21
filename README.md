# PlannerAI

> An AI-powered calendar assistant that understands natural language. Talk to it like a person — it manages your Google Calendar for you.

PlannerAI connects your Google Calendar to a Telegram bot backed by a FastAPI service. An LLM agent interprets free-form requests and executes calendar operations autonomously — no rigid commands needed.

---

## Usage Examples

All interactions happen through plain text or voice in Telegram.

### Viewing events

```
What do I have tomorrow?
Show my events for this week
What's on my schedule in May?
Do I have anything this Saturday?
Show upcoming events
```

### Creating events

```
Schedule a team meeting tomorrow at 3pm
Add a workout on Friday from 10:00 to 11:30
I need to call the doctor on Thursday at noon
I want to go on a date tomorrow evening
Plan a movie night next Saturday at 7pm
```

> Tap **➕ Add event** first and then write even more casually — the bot already knows you want to create something.

### Editing events

Tap **✏️** next to any event in the list, then describe the change:

```
Move it to Friday at 5pm
Rename it to Team standup
Change the time to 18:00
Add note: bring the report
```

### Deleting events

Tap **🗑️** next to any event and confirm — or write:

```
Delete the gym session on Wednesday
Remove the dentist appointment
```

### Voice messages

Send a voice message — it is transcribed locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (no third-party API key required) and processed the same as text.

---

## Features

- **Natural language agent** — LLM with function-calling resolves user intent and calls the right calendar operation. Supports LM Studio (local) and any OpenAI-compatible endpoint.
- **Full Google Calendar CRUD** — Create, read, update, and delete events. Search by keyword, list upcoming events, find free time slots.
- **Single-window UI** — The bot edits one message in place rather than flooding the chat. User messages are deleted after processing.
- **Voice-to-text** — Local speech recognition via faster-whisper (`small` model, CPU, no API key).
- **Google OAuth 2.0** — Secure delegated access. Tokens are stored server-side; the user never shares credentials with the bot.
- **JWT authentication** — The backend issues signed JWT access tokens used for all subsequent API calls.
- **Async throughout** — FastAPI + SQLAlchemy async + asyncpg. No blocking I/O in the request path.
- **Docker-first** — `docker-compose up` brings up PostgreSQL and the backend.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Telegram Bot                             │
│  python-telegram-bot · httpx async client                  │
│  faster-whisper (local STT)                                │
│                                                            │
│  Inline keyboard UI  ·  Natural language input             │
│  Voice messages → transcription → agent                    │
└──────────────────────┬─────────────────────────────────────┘
                       │  HTTP · Bearer JWT
                       ▼
┌────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                          │
│                                                            │
│  /auth/*          Google OAuth flow + JWT issuance         │
│  /calendar/*      CRUD, search, free-slots, summary        │
│  /agent/prompt    Natural language → LLM → tool calls      │
│  /public/health   Liveness probe                           │
│                                                            │
│  SQLAlchemy async · asyncpg · google-api-python-client     │
└──────┬───────────────────────┬─────────────────────────────┘
       │                       │
       ▼                       ▼
  PostgreSQL 16          Google Calendar API
  (users, tokens,         (via OAuth credentials
   JWT state)              stored in DB)
                                │
                                ▼
                     LM Studio / OpenAI API
                     (LLM with function-calling)
```

### How the AI agent works

The agent lives in `backend/app/api/agent/`. When a user sends a prompt to `POST /agent/prompt`:

1. The prompt is sent to the LLM along with 7 tool schemas: `get_events`, `get_upcoming_events`, `create_event`, `update_event`, `delete_event`, `search_events`, `find_free_slots`.
2. The system prompt injects today's date and an explicit 14-day calendar so the model resolves relative expressions ("tomorrow", "this Friday") without arithmetic errors.
3. The LLM picks a tool and returns structured arguments, e.g. `{"summary": "Dentist", "start_time": "2026-04-28T10:00:00Z", "end_time": "2026-04-28T11:00:00Z"}`.
4. The backend executes the tool call against Google Calendar and returns a human-readable reply.

### Authentication flow

```
User in Telegram
      │  taps "Login with Google"
      ▼
Bot sends URL:  GET /auth/login?tg_id=<id>
      │  302 → Google OAuth consent screen
      ▼
User grants access in browser (tab closes automatically)
      │  Google redirects to /auth/callback?code=…
      ▼
Backend saves tokens to DB, mints JWT, stores in telegram_status
      │  User taps "I've authorized"
      ▼
Bot calls:  GET /auth/telegram-status?telegram_user_id=<id>
      │  Backend returns JWT
      ▼
Bot stores JWT in memory → Bearer token for all future requests
```

Google access tokens are refreshed automatically before every Calendar API call.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI 0.122+ |
| ASGI server | Uvicorn |
| ORM | SQLAlchemy 2.0 (async) |
| Database driver | asyncpg |
| Database | PostgreSQL 16 |
| Google integration | google-api-python-client, google-auth |
| LLM client | openai SDK (LM Studio or OpenAI) |
| Authentication | PyJWT, Google OAuth 2.0 |
| Telegram bot | python-telegram-bot 21+ |
| HTTP client (bot) | httpx |
| Speech-to-text | faster-whisper (local, CPU) |
| Package manager | uv (workspace monorepo) |
| Containerization | Docker + Docker Compose |

---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker & Docker Compose (for PostgreSQL)
- A Google Cloud project with the Calendar API enabled and OAuth 2.0 credentials
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- [LM Studio](https://lmstudio.ai/) running locally **or** an OpenAI API key

### 1. Clone and configure

```bash
git clone git@github.com:sauz-zeth/PlannerAI.git
cd PlannerAI
cp .env.example .env
```

Edit `.env`:

```env
# PostgreSQL
POSTGRES_USER=ai_planner
POSTGRES_PASSWORD=ai_planner_pass
POSTGRES_DB=ai_planner
DATABASE_URL=postgresql+asyncpg://ai_planner:ai_planner_pass@localhost:5432/ai_planner

# Google OAuth — from Google Cloud Console
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# JWT signing key — any long random string
SECRET_KEY=your_secret_key

# LLM — LM Studio (local) or OpenAI
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=qwen/qwen3-4b-2507
LM_STUDIO_API_KEY=lm-studio
# OPENAI_API_KEY=sk-...   # uncomment to use OpenAI instead
```

### 2. Start the database

```bash
docker-compose up -d postgres
```

### 3. Start the backend

```bash
cd backend
uv sync
./run.sh
```

API available at `http://localhost:8000`. Interactive docs at [`/docs`](http://localhost:8000/docs).

### 4. Start the Telegram bot

```bash
cd telegram_bot
uv sync
./run.sh
```

### Running everything with Docker

```bash
docker-compose up -d
```

Starts PostgreSQL and the backend. The bot runs outside Docker and only needs `BACKEND_API_URL`.

> **Note:** When the backend runs inside Docker and LM Studio runs on the host, set `LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1` in your compose environment.

### Database migrations

```bash
uv run python migration.py
```

---

## API Reference

All protected endpoints require `Authorization: Bearer <jwt>`.

### Auth — `/auth`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/auth/login?tg_id=` | Initiates Google OAuth flow |
| `GET` | `/auth/callback` | OAuth callback — saves tokens, mints JWT |
| `GET` | `/auth/telegram-status?telegram_user_id=` | Returns JWT after OAuth completes |
| `GET` | `/auth/validate` | Validates the current Bearer token |
| `POST` | `/auth/refresh` | Issues a new access token from a refresh token |

### Calendar — `/calendar` 🔒

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/calendar/events` | List events with optional date range and limit |
| `POST` | `/calendar/events` | Create a new event |
| `PUT` | `/calendar/events/{event_id}` | Update an existing event |
| `DELETE` | `/calendar/events/{event_id}` | Delete an event |
| `GET` | `/calendar/upcoming` | Events in the next N hours |
| `GET` | `/calendar/free-slots` | Available slots for a given date and duration |
| `GET` | `/calendar/free-blocks` | Continuous free blocks for a given date |
| `GET` | `/calendar/search?q=` | Full-text search across events |
| `GET` | `/calendar/summary` | Today/tomorrow event counts |

### Agent — `/agent` 🔒

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/agent/prompt` | Natural language request → calendar action + reply |

**Example:**

```bash
curl -X POST http://localhost:8000/agent/prompt \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Schedule a dentist appointment next Monday at 10am for an hour"}'
```

```json
{
  "type": "text",
  "content": "✅ Event created: Dentist appointment\n📅 Monday, 27 April at 10:00"
}
```

---

## Project Structure

```
PlannerAI/
├── backend/
│   ├── app/api/
│   │   ├── auth/           # OAuth, JWT, token storage, auth dependency
│   │   ├── calendar/       # Google Calendar service + REST routes
│   │   ├── agent/          # LLM agent: tools, logic, routes
│   │   └── public/         # Health check
│   ├── main.py             # FastAPI app, router registration, DB init
│   ├── Dockerfile
│   └── pyproject.toml
├── telegram_bot/
│   ├── bot.py              # Application setup, handler registration
│   ├── handlers.py         # All bot logic: single-window UI, agent calls, STT
│   ├── api_client.py       # Async HTTP client for the backend
│   └── pyproject.toml
├── migration.py            # Additive schema migrations
├── docker-compose.yml      # PostgreSQL + backend
├── pyproject.toml          # uv workspace root
└── .env.example
```

---

## Google Cloud Setup

1. [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Library** → enable **Google Calendar API**
2. **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID** → **Web application**
3. Add `http://localhost:8000/auth/callback` to **Authorized redirect URIs**
4. Copy **Client ID** and **Client Secret** into `.env`

---

## License

MIT
