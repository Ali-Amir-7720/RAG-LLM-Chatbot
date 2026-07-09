from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException

from app.config import get_settings
from app.db import check_database, close_database
from app.routers import auth, conversations, documents, messages, users


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_database()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(users.router)
api_router.include_router(auth.router)
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(messages.messages_action_router)
api_router.include_router(documents.router)

app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "environment": settings.app_env,
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def database_health() -> dict[str, Any]:
    try:
        database = await check_database()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database check failed: {exc}",
        ) from exc

    return {
        "status": "ok",
        "database": database,
    }
