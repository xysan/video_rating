from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from app.scoring.task import sync_and_calculate
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.config import get_settings
from app.api.sync import router as sync_router
from app.api.configs import router as configs_router
from app.database import SessionLocal
from app.api.scores import router as scores_router
from app.api.management import router as management_router
from app.sync.bilibili_crawler import BilibiliCacheService
from app.sync.task import SyncService
from app.sync.refresh_all import RefreshService
from app.api.refresh import router as refresh_router

settings = get_settings()
@asynccontextmanager
async def lifespan(app):
    service = SyncService(settings, SessionLocal)
    app.state.sync_service = service
    service.start()
    cache_service = BilibiliCacheService(SessionLocal)
    refresh_service = RefreshService(service, cache_service, SessionLocal)
    app.state.refresh_service = refresh_service
    if settings.BILIBILI_CACHE_ENABLED:
        cache_service.start()
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    def daily_score():
        try:
            sync_and_calculate(SessionLocal)
        except Exception:
            logging.getLogger(__name__).exception("每日评分失败")
    scheduler.add_job(daily_score, "cron", hour=2, minute=30, id="daily_scoring", max_instances=1, coalesce=True)
    def refresh_highlights():
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from app.api.scores import weekly_highlights
        try:
            with SessionLocal() as session:
                weekly_highlights(session, datetime.now(ZoneInfo("Asia/Shanghai")).date())
        except Exception:
            logging.getLogger(__name__).exception("每周高光刷新失败")
    scheduler.add_job(refresh_highlights, "cron", day_of_week="mon", hour=3, id="weekly_highlights", max_instances=1, coalesce=True)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=True)
        refresh_service.close()
        cache_service.close()
        service.close()


app = FastAPI(title="视频评分看板", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sync_router)
app.include_router(refresh_router)
app.include_router(configs_router)
app.include_router(scores_router)
app.include_router(management_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

from app.api.score_management import router as score_management_router
app.include_router(score_management_router)
