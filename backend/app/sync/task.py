from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import logging
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.sync.feishu_client import FeishuClient, FeishuError
from app.models import VideoSnapshot

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


def utc_now():
    return datetime.now(timezone.utc)


def unwrap(value):
    if isinstance(value, dict) and "value" in value:
        return unwrap(value["value"])
    if isinstance(value, list):
        if len(value) != 1:
            raise ValueError("必填字段必须只有一个值")
        return unwrap(value[0])
    if isinstance(value, dict) and "text" in value:
        return value["text"]
    return value


class MissingRequiredFields(ValueError):
    pass


def parse_record(record, settings):
    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not record_id or len(record_id) > 191:
        raise ValueError("记录 ID 缺失或长度无效")
    modified = record.get("last_modified_time")
    if isinstance(modified, bool) or not isinstance(modified, (int, float)) or modified <= 0:
        raise ValueError("记录缺少有效 last_modified_time")
    fields = record.get("fields", {})
    missing = []
    for name in (settings.FEISHU_UP_NAME_FIELD, settings.FEISHU_TITLE_FIELD, settings.FEISHU_PUBLISH_DATE_FIELD):
        value = fields.get(name)
        if isinstance(value, dict) and "value" in value:
            value = value["value"]
        if value is None or value == [] or value == "":
            missing.append(name)
    if missing:
        raise MissingRequiredFields("缺少必填字段：" + "、".join(missing))
    up_name = unwrap(fields.get(settings.FEISHU_UP_NAME_FIELD))
    title = unwrap(fields.get(settings.FEISHU_TITLE_FIELD))
    published = unwrap(fields.get(settings.FEISHU_PUBLISH_DATE_FIELD))
    if not isinstance(up_name, str) or not up_name.strip() or len(up_name) > 255:
        raise ValueError("UP 主字段缺失或格式无效")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("标题字段缺失或格式无效")
    if isinstance(published, (int, float)) and not isinstance(published, bool):
        publish_date = datetime.fromtimestamp(published / 1000, timezone(timedelta(hours=8))).date()
    elif isinstance(published, str):
        publish_date = date.fromisoformat(published)
    else:
        raise ValueError("发布时间字段缺失或格式无效")
    # MySQL DATETIME 当前为秒精度；同秒更新再比较完整原始记录，避免漏更。
    modified_at = datetime.fromtimestamp(modified / 1000, timezone.utc).replace(tzinfo=None, microsecond=0)
    return dict(feishu_record_id=record_id, up_name=up_name, video_title=title, publish_date=publish_date, last_modified_at=modified_at, raw_payload=record)


class SyncService:
    def __init__(self, settings, session_factory, client_factory=FeishuClient):
        self.settings = settings
        self.session_factory = session_factory
        self.client_factory = client_factory
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="feishu-sync")
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self.closed = False
        self.state = {"running": False, "started_at": None, "finished_at": None, "last_sync_at": None, "success": None, "fetched": 0, "inserted": 0, "updated": 0, "skipped": 0, "error": None}

    def status(self):
        with self.lock:
            return deepcopy(self.state)

    def start(self):
        if self.settings.FEISHU_SYNC_ENABLED:
            self.scheduler.add_job(self.trigger, "interval", minutes=self.settings.SYNC_INTERVAL_MINUTES, id="feishu-sync", max_instances=1, coalesce=True)
            self.scheduler.start()

    def trigger(self):
        with self.lock:
            if self.closed or self.state["running"]:
                return False
            self.state["running"] = True
            self.state["started_at"] = utc_now().isoformat()
            try:
                self.executor.submit(self._run)
            except RuntimeError:
                self.state["running"] = False
                raise
        return True

    def _run(self):
        started = utc_now()
        fetched = inserted = updated = skipped = 0
        error = None
        success = False
        logger.info("飞书同步开始 started_at=%s", started.isoformat())
        try:
            with self.session_factory() as session, session.begin():
                for record in self.client_factory(self.settings).records():
                    fetched += 1
                    try:
                        values = parse_record(record, self.settings)
                    except MissingRequiredFields as exc:
                        skipped += 1
                        logger.warning("飞书记录跳过 record_id=%s reason=%s", record.get("record_id"), exc)
                        continue
                    existing = session.scalar(select(VideoSnapshot).where(VideoSnapshot.feishu_record_id == values["feishu_record_id"]))
                    if existing is None:
                        session.add(VideoSnapshot(**values, synced_at=utc_now().replace(tzinfo=None)))
                        inserted += 1
                    elif values["last_modified_at"] > existing.last_modified_at or (values["last_modified_at"] == existing.last_modified_at and values["raw_payload"] != existing.raw_payload):
                        for key, value in values.items():
                            setattr(existing, key, value)
                        existing.synced_at = utc_now().replace(tzinfo=None)
                        updated += 1
            success = True
        except Exception as exc:
            # 任务边界捕获异常并记录失败，调度线程继续运行；事务自动回滚。
            error = str(exc) if isinstance(exc, FeishuError) else (f"ValueError: {exc}" if isinstance(exc, ValueError) else f"{type(exc).__name__}: 同步解析或数据库写入失败")
            logger.error("飞书同步失败 fetched=%s reason=%s", fetched, error)
            inserted = updated = 0
        finally:
            finished = utc_now().isoformat()
            with self.lock:
                self.state.update(running=False, started_at=started.isoformat(), finished_at=finished, last_sync_at=finished, success=success, fetched=fetched, inserted=inserted, updated=updated, skipped=skipped, error=error)
            logger.info("飞书同步结束 finished_at=%s success=%s fetched=%s inserted=%s updated=%s skipped=%s", finished, success, fetched, inserted, updated, skipped)

    def close(self):
        with self.lock:
            self.closed = True
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        self.executor.shutdown(wait=True)
