from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import logging
from threading import Lock

from sqlalchemy import select

from app.database import SessionLocal
from app.models import AlgorithmConfig, Score, VideoSnapshot
from app.scoring.calculator import ConfigurationError, REQUIRED_KEYS, calculate_video_score, parse_metric_value, validate_rules, validate_standards
from app.scoring.configuration import load_configs

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
calculation_lock = Lock()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, default=str).encode()).hexdigest()


def unwrap(value, multiple=False):
    if isinstance(value, dict) and "value" in value:
        return unwrap(value["value"], multiple)
    if isinstance(value, list):
        if multiple:
            return [unwrap(item) for item in value]
        if not value:
            return None
        if len(value) != 1:
            raise ValueError("指标包含多个值，无法明确计算")
        return unwrap(value[0])
    if isinstance(value, dict):
        if "text" in value:
            return value["text"]
        raise ValueError("指标结构无效")
    return value


def extract_metrics(raw_payload, fields):
    source = raw_payload.get("fields", {})
    result = {}
    for metric, field in fields.items():
        field = field or {"difficulty":"制作难度", "efficiency":"时效情况", "traffic_ratio":"投流情况"}.get(metric)
        value = unwrap(source.get(field), multiple=metric == "tags") if field else None
        if metric in ("difficulty", "efficiency", "tags"):
            if metric != "tags" and value is not None and not isinstance(value, str):
                raise ValueError("难度或效率格式无效")
            if metric == "tags" and value is not None and not isinstance(value, (str, list)):
                raise ValueError("榜单格式无效")
            result[metric] = value
        else:
            result[metric] = parse_metric_value(value)
    result.update(raw_payload.get("_admin_extras", {}))
    return result


def sync_and_calculate(session_factory=SessionLocal, now=None, algorithm_version="v1.0"):
    # 从已同步快照计算；由同步任务提交成功后调用，不重复请求飞书。
    if not calculation_lock.acquire(blocking=False):
        return {"status": "busy"}
    try:
        now = now or datetime.now(timezone.utc)
        summary = {"status": "success", "calculated": 0, "unchanged": 0, "skipped": 0, "issues": []}
        with session_factory() as session, session.begin():
            configs = load_configs(session)
            validate_rules(configs)
            rules = {key: configs[key] for key in REQUIRED_KEYS}
            cutoff = (now.astimezone(timezone(timedelta(hours=8))) - timedelta(days=rules["calculation_age_days"])).date()
            videos = session.scalars(select(VideoSnapshot).where(VideoSnapshot.publish_date <= cutoff)).all()
            for video in videos:
                key = "up_standards_" + video.up_name
                standards = configs.get(key)
                if standards is None:
                    summary["skipped"] += 1
                    summary["issues"].append({"video_snapshot_id": video.id, "reason": "缺失基线", "config_key": key})
                    continue
                try:
                    validate_standards(standards)
                    input_hash = fingerprint({"raw_payload": video.raw_payload, "publish_date": video.publish_date, "up_name": video.up_name, "last_modified_at": video.last_modified_at})
                    config_hash = fingerprint({"rules": rules, "standards": standards})
                    existing = session.scalar(select(Score).where(Score.video_snapshot_id == video.id, Score.algorithm_version == algorithm_version))
                    meta = (existing.score_detail or {}).get("calculation", {}) if existing else {}
                    if meta.get("input_hash") == input_hash and meta.get("config_hash") == config_hash:
                        summary["unchanged"] += 1
                        continue
                    metrics = extract_metrics(video.raw_payload, rules["metric_fields"])
                    result = calculate_video_score(metrics, standards, rules)
                    if result["status"] == "error":
                        raise ValueError(result["message"] + "：" + ",".join(result["missing_fields"]))
                    if existing is None:
                        existing = Score(video_snapshot_id=video.id, algorithm_version=algorithm_version)
                        session.add(existing)
                    existing.score = Decimal(str(result["final_score"]))
                    existing.score_detail = {**result, "calculation": {"input_hash": input_hash, "config_hash": config_hash, "rules": rules, "standards": standards, "metrics": metrics}}
                    existing.calculated_at = now.astimezone(timezone.utc).replace(tzinfo=None)
                    summary["calculated"] += 1
                except (ValueError, TypeError, OverflowError) as exc:
                    summary["skipped"] += 1
                    summary["issues"].append({"video_snapshot_id": video.id, "reason": str(exc)})
            if summary["skipped"]:
                summary["status"] = "partial_success"
        for issue in summary["issues"]:
            logger.warning("评分跳过 %s", issue)
        logger.info("评分完成 calculated=%s unchanged=%s skipped=%s", summary["calculated"], summary["unchanged"], summary["skipped"])
        return summary
    finally:
        calculation_lock.release()


if __name__ == "__main__":
    print(json.dumps(sync_and_calculate(), ensure_ascii=False))
