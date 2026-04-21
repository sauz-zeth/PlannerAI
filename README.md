# PlannerAI

> An AI-powered calendar assistant that understands natural language. Talk to it like a person — it handles the calendar for you.

PlannerAI connects your Google Calendar to a Telegram bot and exposes a full REST API. At its core sits an LLM agent that interprets free-form user requests ("schedule a meeting with the team tomorrow at 3pm", "what do I have this weekend?") and autonomously executes the necessary calendar operations — no rigid command syntax required.

---

## Features

- **Natural language agent** — An LLM with function-calling resolves user intent and calls the right calendar operations. Supports LM Studio (local) and any OpenAI-compatible endpoint.
- **Full Google Calendar CRUD** — Create, read, update, and delete events. Search by text, list upcoming events, get a daily/weekly summary, find free time slots.
- **Google OAuth 2.0** — Secure delegated access to users' calendars. Tokens are stored server-side; users never share credentials with the bot.
- **JWT authentication** — The backend issues signed JWT access tokens. The Telegram bot uses them for all subsequent API calls.
- **Telegram interface** — A fully functional bot with commands for every calendar operation, inline keyboards, and deep-link OAuth initiation.
- **Async from top to bottom** — FastAPI + SQLAlchemy async + asyncpg. No blocking I/O anywhere in the request path.
- **Docker-first** — One `docker-compose up` brings up PostgreSQL and the backend. The bot runs separately and only needs `BACKEND_API_URL`.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Telegram Bot                             │
│  python-telegram-bot  ·  httpx async client               │
│                                                            │
│  /login  /events  /create_event  /search  /free_slots     │
│  /upcoming  /summary  /check  /help  …                     │
└──────────────────────┬─────────────────────────────────────┘
                       │  HTTP  ·  Bearer JWT
                       ▼
┌────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                          │
│                                                            │
│  /auth/*          Google OAuth flow + JWT issuance        │
│  /calendar/*      CRUD, search, free-slots, summary       │
│  /agent/prompt    Natural language → LLM → tool calls     │
│  /public/health   Liveness probe                          │
│                                                            │
│  SQLAlchemy async  ·  asyncpg  ·  google-api-python-client│
└──────┬───────────────────────┬───────────────────────────┘
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

The agent lives in `backend/app/api/agent/`. When a user sends a natural language prompt to `POST /agent/prompt`, the following happens:

1. The prompt is sent to the LLM together with a set of 7 pre-defined tool schemas (`get_events`, `create_event`, `update_event`, `delete_event`, `find_free_slots`, `search_events`, `get_upcoming_events`, `get_calendar_summary`).
2. The LLM decides which tool(s) to call and returns structured arguments (e.g. `{"summary": "Team sync", "start_time": "2026-04-22T15:00:00Z", "end_time": "2026-04-22T16:00:00Z"}`).
3. The backend executes each tool call against the user's Google Calendar.
4. A final human-readable response is assembled from the tool outputs and returned to the caller.

The system prompt injects today's date so the model can correctly resolve relative expressions like "tomorrow", "this Friday", or "in two weeks".

### Authentication flow

```
User in Telegram
      │
      │  /login
      ▼
Bot sends:  GET /auth/login?tg_id=<id>
      │
      │  302 → Google OAuth consent screen
      ▼
User grants access in browser
      │
      │  Google redirects to /auth/callback?code=…&state=…
      ▼
Backend exchanges code → Google access + refresh tokens
Backend saves tokens to DB, mints a JWT, stores it in telegram_status table
      │
      │  User returns to Telegram, sends /check
      ▼
Bot calls:  GET /auth/telegram-status?telegram_user_id=<id>
      │
      │  Backend returns JWT
      ▼
Bot stores JWT in memory → uses it as Bearer token for all future requests
```

Google access tokens are refreshed automatically before every Calendar API call if they have expired.

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
| LLM client | openai SDK (pointed at LM Studio or OpenAI) |
| Authentication | PyJWT, Google OAuth 2.0 |
| Telegram bot | python-telegram-bot 21+ |
| HTTP client (bot) | httpx |
| Package manager | uv (workspace) |
| Containerization | Docker + Docker Compose |

---

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker & Docker Compose (for PostgreSQL)
- A Google Cloud project with the Calendar API enabled and OAuth 2.0 credentials
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- LM Studio running locally **or** an OpenAI API key

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
TELEGRAM_BOT_USERNAME=your_bot_username

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

The API will be available at `http://localhost:8000`. Interactive docs: [`/docs`](http://localhost:8000/docs).

### 4. Start the Telegram bot

In a separate terminal:

```bash
cd telegram_bot
uv sync
./run.sh
```

### Running everything with Docker

```bash
docker-compose up -d
```

This starts PostgreSQL and the backend. The Telegram bot is designed to run outside Docker (it only makes HTTP calls to the backend).

> **Note:** When running the LLM locally in LM Studio and the backend inside Docker, `LM_STUDIO_BASE_URL` is automatically rewritten to `http://host.docker.internal:1234/v1` by the compose file.

### Database migrations

If you need to apply additive schema changes after pulling updates:

```bash
uv run python migration.py
```

---

## API Reference

All protected endpoints require `Authorization: Bearer <jwt>` header.

### Auth — `/auth`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/auth/login?tg_id=` | Initiates Google OAuth flow (redirect) |
| `GET` | `/auth/callback` | OAuth callback — saves tokens, mints JWT |
| `GET` | `/auth/telegram-status?telegram_user_id=` | Returns JWT for the bot after OAuth completes |
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
| `GET` | `/calendar/free-slots` | Available time slots for a given date and duration |
| `GET` | `/calendar/search?q=` | Full-text search across events |
| `GET` | `/calendar/summary` | Today/tomorrow event counts and next upcoming event |

### Agent — `/agent` 🔒

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/agent/prompt` | Send a natural language request; get a calendar action + human-readable reply |

**Example request:**

```bash
curl -X POST http://localhost:8000/agent/prompt \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Schedule a dentist appointment next Monday at 10am for an hour"}'
```

**Example response:**

```json
{
  "type": "text",
  "content": "✅ Event created: Dentist appointment\n📅 Monday, 27 April at 10:00"
}
```

### Public — `/public`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/public/health` | Liveness check |

---

## Telegram Bot Commands

### Authentication
| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/login` | Begin Google Calendar authorization |
| `/check` | Confirm authorization and retrieve JWT |

### Calendar
| Command | Description |
|---|---|
| `/events [n]` | Show the next N events (default: 5) |
| `/upcoming [hours]` | Events in the next N hours |
| `/summary` | Today and tomorrow at a glance |
| `/create_event <title> <start> <end> [description]` | Create an event (`2026-04-22T14:00:00`) |
| `/search <query>` | Find events by keyword |
| `/free_slots [date] [duration_min]` | Find open slots on a given day |

### Misc
| Command | Description |
|---|---|
| `/status` | Show connection status |
| `/help` | List all commands |

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
│   ├── handlers.py         # Command implementations
│   ├── api_client.py       # Async HTTP client for the backend
│   └── pyproject.toml
├── migration.py            # Additive schema migrations
├── docker-compose.yml      # PostgreSQL + backend
├── pyproject.toml          # uv workspace root
└── .env.example
```

---

## Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Library**
2. Enable **Google Calendar API**
3. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
4. Application type: **Web application**
5. Add `http://localhost:8000/auth/callback` to **Authorized redirect URIs**
6. Copy the **Client ID** and **Client Secret** into `.env`

---

## License

MIT
