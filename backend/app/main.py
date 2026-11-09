from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.config import get_settings
from app.api.sync import router as sync_router
from app.database import SessionLocal
from app.sync.task import SyncService

settings = get_settings()
@asynccontextmanager
async def lifespan(app):
    service = SyncService(settings, SessionLocal)
    app.state.sync_service = service
    service.start()
    try:
        yield
    finally:
        service.close()


app = FastAPI(title="视频评分看板", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sync_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
