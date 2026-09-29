# TikkunTech

A social-feed demo that screens a post before it is published. If an LLM classifies the draft as harmful, an in-page modal opens with a second, supportive LLM conversation. From there the user can delete the post or publish it anyway.

## Architecture

- `frontend/`: Next.js (TypeScript, Tailwind). UI only. `/api/*` is rewritten to the backend, so the browser never sees the API key.
- `backend/`: FastAPI with LangChain, calling Claude models through OpenRouter.
  - `POST /classify` returns `{harmful, category, severity, reason}`.
  - `POST /chat` streams supportive replies.
  - `GET /health`
- `docker-compose.yml`: runs both services. Only `frontend` is published (port 3000).

## Configuration

Set these in the container environment (see `.env.example`):

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter token, used by the backend only |
| `CLASSIFIER_MODEL` | Model ID for the harm classifier |
| `CHAT_MODEL` | Model ID for the supportive chat |

## Run

```
docker compose up --build
```

## Status

Phase 1 (scaffold and frontend conversion) is done. `/classify` and `/chat` return 501 until Phases 2 and 3.
