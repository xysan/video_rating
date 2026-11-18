from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import logging
from threading import Lock
import time
from uuid import uuid4
from app.scoring.task import sync_and_calculate

logger = logging.getLogger(__name__)

class RefreshService:
    """串行刷新，对外仅返回不含算法信息的任务状态。"""
    def __init__(self, sync, cache, session_factory):
        self.sync, self.cache, self.session_factory = sync, cache, session_factory
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.lock = Lock()
        self.jobs = {}
        self.current = None

    def trigger(self):
        with self.lock:
            if self.current and self.jobs[self.current]["status"] == "running":
                return deepcopy(self.jobs[self.current])
            job_id = uuid4().hex
            self.current = job_id
            self.jobs[job_id] = {"id": job_id, "status": "running"}
            while len(self.jobs) > 20:
                del self.jobs[next(iter(self.jobs))]
            self.executor.submit(self.run, job_id)
            return deepcopy(self.jobs[job_id])

    def status(self, job_id):
        with self.lock:
            return deepcopy(self.jobs.get(job_id))

    def run(self, job_id):
        try:
            # 等待已有同步，随后执行本次请求，避免并发重复写入。
            while not self.sync.trigger():
                time.sleep(.2)
            while self.sync.status()["running"]:
                time.sleep(.2)
            if not self.sync.status()["success"]:
                raise RuntimeError("飞书同步失败")
            while True:
                cache = self.cache.refresh()
                if cache["status"] != "busy":
                    break
                time.sleep(.2)
            if cache["status"] == "failed":
                raise RuntimeError("B站抓取失败")
            while True:
                scoring = sync_and_calculate(self.session_factory, force_daily=True)
                if scoring["status"] != "busy":
                    break
                time.sleep(.2)
            from datetime import datetime
            from zoneinfo import ZoneInfo
            from app.api.scores import weekly_highlights
            with self.session_factory() as session:
                weekly_highlights(session, datetime.now(ZoneInfo("Asia/Shanghai")).date(), force=True)
            partial = cache["status"] != "success" or scoring["status"] != "success"
            result = {"status": "partial_success" if partial else "success", "message": "数据已更新，部分视频抓取失败或缺少算分指标" if partial else "数据已同步并更新"}
        except Exception:
            logger.exception("完整刷新失败 job_id=%s", job_id)
            result = {"status": "failed", "message": "数据同步或计算失败，请联系管理员查看日志"}
        with self.lock:
            self.jobs[job_id].update(result)

    def close(self):
        self.executor.shutdown(wait=True)
