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

Both services run with hot reload (source is bind-mounted, `uvicorn --reload`, `next dev`):

```
docker compose up --build
```

After changing `requirements.txt` or `package.json`, rebuild. For the frontend, use `docker compose up --build -V` so the container's `node_modules` volume is refreshed.

## Status

Phases 1 (scaffold) and 2 (classifier and Post-click flow) are implemented. `/chat` returns 501 until Phase 3, so the modal still uses a static first message.
