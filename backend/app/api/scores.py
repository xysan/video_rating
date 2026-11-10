from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_session
from app.models import Score, VideoSnapshot
from app.api.video_data import field, decode_field, flatten, extract_bv
from app.scoring.calculator import parse_metric_value
from app.sync.bilibili_crawler import get_cached_video

router = APIRouter()
PUBLIC_FIELDS = ("BV号", "标题", "编导", "播放量", "3s跳出率", "播转粉率", "互动率", "平均播放进度")


def query_scores(admin=False):
    # 多算法版本仅选择最近一次计算结果，避免同一视频重复展示。
    latest = select(Score.id.label("score_id"), Score.video_snapshot_id.label("snapshot_id"), func.row_number().over(partition_by=Score.video_snapshot_id, order_by=(Score.calculated_at.desc(), Score.id.desc())).label("rn")).subquery()
    columns = [VideoSnapshot.id, VideoSnapshot.up_name, VideoSnapshot.video_title, VideoSnapshot.publish_date, Score.score.label("total_score"), Score.algorithm_version]
    columns.extend(field(name) for name in PUBLIC_FIELDS)
    if admin:
        columns.extend([Score.score_detail, VideoSnapshot.raw_payload])
    return select(*columns).select_from(VideoSnapshot).outerjoin(latest, (latest.c.rn == 1) & (latest.c.snapshot_id == VideoSnapshot.id)).outerjoin(Score, Score.id == latest.c.score_id)


def filtered_rows(session, admin=False, up_name=None, date_from=None, date_to=None, director=None):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "开始日期不能晚于结束日期")
    query = query_scores(admin)
    if up_name:
        query = query.where(VideoSnapshot.up_name == up_name)
    if date_from:
        query = query.where(VideoSnapshot.publish_date >= date_from)
    if date_to:
        query = query.where(VideoSnapshot.publish_date < date_to + timedelta(days=1))
    rows = session.execute(query.order_by(VideoSnapshot.publish_date.desc(), VideoSnapshot.id.desc())).mappings().all()
    # 编导在嵌套 JSON 中，准确解析后筛选再分页，避免误匹配其它原始字段。
    if director:
        rows = [row for row in rows if director == flatten(decode_field(row["编导"]))]
    return rows


def public_video(row):
    raw = {"fields": {name: decode_field(row[name]) for name in PUBLIC_FIELDS}}
    bv = extract_bv(raw)
    cache = get_cached_video(bv) or {}
    result = {key: row[key] for key in ("id", "up_name", "video_title", "publish_date", "total_score", "algorithm_version")}
    result.update(bv_id=bv, cover_url=cache.get("cover_url"), title=cache.get("title") or row["video_title"], director=flatten(raw["fields"].get("编导")) or None)
    for key in ("play_count", "like_count", "coin_count", "favorite_count", "comment_count", "share_count", "danmaku_count", "ranking_status"):
        result[key] = cache.get(key)
    for target, name in {"snapshot_play_count":"播放量", "jump_3s":"3s跳出率", "convert_rate":"播转粉率", "interact_rate":"互动率", "progress":"平均播放进度"}.items():
        try:
            result[target] = parse_metric_value(flatten(raw["fields"].get(name)))
        except (ValueError, TypeError):
            result[target] = None
    result["score"] = result["total_score"]
    result["is_high_score"] = row["total_score"] is not None and row["total_score"] > 85
    return result


def pagination(rows, page, page_size, admin=False):
    items=[]
    for row in rows[(page-1)*page_size:page*page_size]:
        item=public_video(row)
        if admin:
            item.update(score_detail=row["score_detail"],raw_payload=row["raw_payload"])
        items.append(item)
    return {"items":items,"total":len(rows),"page":page,"page_size":page_size}


@router.get("/api/member/scores", dependencies=[Depends(get_current_user)])
def member_scores(page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=100), up_name: str|None=None, date_from: date|None=None, date_to: date|None=None, director: str|None=None, session: Session=Depends(get_session)):
    return pagination(filtered_rows(session,False,up_name,date_from,date_to,director),page,page_size)


@router.get("/api/admin/scores", dependencies=[Depends(require_admin)])
def admin_scores(page: int=Query(1,ge=1), page_size: int=Query(20,ge=1,le=100), up_name: str|None=None, date_from: date|None=None, date_to: date|None=None, director: str|None=None, session: Session=Depends(get_session)):
    return pagination(filtered_rows(session,True,up_name,date_from,date_to,director),page,page_size,True)


@router.get("/api/member/dashboard", dependencies=[Depends(get_current_user)])
def dashboard(session: Session=Depends(get_session)):
    today=datetime.now(timezone(timedelta(hours=8))).date()
    rows=filtered_rows(session,date_from=today-timedelta(days=29),date_to=today)
    cards=[public_video(row) for row in rows]
    top=sorted((v for v in cards if v["score"] is not None),key=lambda v:(v["score"],v["id"]),reverse=True)[:5]
    return {"top_videos":[{k:v[k] for k in ("score","up_name","video_title","cover_url","title")} for v in top],"videos":cards}
