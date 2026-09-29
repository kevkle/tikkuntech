from fastapi import FastAPI

from app.routers import chat, classify

app = FastAPI(title="TikkunTech backend")

app.include_router(classify.router)
app.include_router(chat.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
