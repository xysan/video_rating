from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import logging
import re
from threading import Lock

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.api.video_data import extract_bv
from app.models import VideoSnapshot

VIDEO_CACHE = {}
_cache_lock = Lock()
logger = logging.getLogger(__name__)


def get_cached_video(bv_id):
    with _cache_lock:
        return deepcopy(VIDEO_CACHE.get(bv_id))


def fetch_video(bv_id, client):
    if not re.fullmatch(r"BV[0-9A-Za-z]{10}", bv_id):
        raise ValueError("无效 BV 号")
    response = client.get("https://api.bilibili.com/x/web-interface/view", params={"bvid": bv_id})
    response.raise_for_status()
    body = response.json()
    if body.get("code") != 0:
        raise ValueError(f"B站错误 code={body.get('code')} message={str(body.get('message'))[:200]}")
    data = body["data"]
    stat = data["stat"]
    result = {"bv_id": bv_id, "cover_url": data.get("pic"), "title": data["title"], "up_name": data["owner"]["name"], "publish_date": datetime.fromtimestamp(data["pubdate"], timezone.utc).isoformat(), "cached_at": datetime.now(timezone.utc).isoformat()}
    for target, source in {"play_count":"view", "like_count":"like", "coin_count":"coin", "favorite_count":"favorite", "comment_count":"reply", "share_count":"share", "danmaku_count":"danmaku"}.items():
        result[target] = stat.get(source)
    # 原样提供官方响应中的当前及历史排名，不将历史上榜伪装为当前热门。
    result["ranking_status"] = {"current_rank": stat.get("now_rank"), "historical_rank": stat.get("his_rank")}
    return result


def crawl_videos(bv_ids, client=None):
    def run(http):
        result = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fetch_video, bv, http): bv for bv in set(bv_ids) if bv}
            for future in as_completed(futures):
                bv = futures[future]
                try:
                    result[bv] = future.result()
                except Exception as exc:
                    logger.warning("B站抓取失败 bv=%s reason=%s", bv, str(exc)[:300])
        return result
    if client is not None:
        return run(client)
    with httpx.Client(timeout=15, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}) as http:
        return run(http)


class BilibiliCacheService:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.refresh_lock = Lock()

    def refresh(self):
        if not self.refresh_lock.acquire(blocking=False):
            return
        try:
            with self.session_factory() as session:
                ids = {extract_bv(raw) for raw in session.scalars(select(VideoSnapshot.raw_payload))}
            ids.discard(None)
            results = crawl_videos(ids)
            # 每轮替换，失败或已删除视频不会无限展示旧缓存。
            with _cache_lock:
                VIDEO_CACHE.clear()
                VIDEO_CACHE.update(results)
            logger.info("B站缓存刷新 requested=%s cached=%s", len(ids), len(results))
        except Exception as exc:
            logger.error("B站缓存刷新失败 type=%s", type(exc).__name__)
        finally:
            self.refresh_lock.release()

    def start(self):
        self.scheduler.add_job(self.refresh, "interval", minutes=15, next_run_time=datetime.now(timezone.utc), max_instances=1, coalesce=True)
        self.scheduler.start()

    def close(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
