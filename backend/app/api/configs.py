import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, JsonValue
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.schemas import CurrentUser
from app.database import get_session
from app.models import AlgorithmConfig
from app.scoring.configuration import load_configs, validate_config_update
from app.scoring.calculator import ConfigurationError

router = APIRouter(prefix="/api/admin/configs", dependencies=[Depends(require_admin)])


class ConfigUpdate(BaseModel):
    config_value: JsonValue
    description: str | None = None


@router.get("")
def list_configs(session: Session = Depends(get_session)):
    rows = session.execute(select(AlgorithmConfig.config_key, AlgorithmConfig.config_value, AlgorithmConfig.description, AlgorithmConfig.updated_by, AlgorithmConfig.updated_at).order_by(AlgorithmConfig.config_key)).mappings()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["config_value"] = json.loads(item["config_value"])
        except ValueError:
            raise HTTPException(409, "配置表包含非 JSON 历史值，请先修正") from None
        result.append(item)
    return result


@router.put("/{config_key}")
def put_config(config_key: str, body: ConfigUpdate, admin: CurrentUser = Depends(require_admin), session: Session = Depends(get_session)):
    if not config_key.strip() or len(config_key) > 191:
        raise HTTPException(422, "配置键长度必须为 1 至 191")
    try:
        serialized = json.dumps(body.config_value, ensure_ascii=False, allow_nan=False)
        # MySQL TEXT 的上限按字节计算。
        if len(serialized.encode("utf-8")) > 65535:
            raise ValueError("配置超过 TEXT 字段容量")
        validate_config_update(config_key, body.config_value, load_configs(session))
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from None
    row = session.scalar(select(AlgorithmConfig).where(AlgorithmConfig.config_key == config_key))
    if row is None:
        row = AlgorithmConfig(config_key=config_key)
        session.add(row)
    row.config_value = serialized
    row.description = body.description
    row.updated_by = admin.id
    row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.commit()
    return {"config_key": config_key, "config_value": body.config_value, "updated_by": admin.id}


@router.post("/import-standards")
def import_standards(body: list[dict[str, JsonValue]], admin: CurrentUser = Depends(require_admin), session: Session = Depends(get_session)):
    from app.scoring.calculator import CORE_METRICS, validate_standards

    prepared = []
    names = set()
    # 整批先校验，任何一项失败均不写入，避免半批更新。
    for item in body:
        name = item.get("up_name")
        if not isinstance(name, str) or not name.strip() or len("up_standards_" + name.strip()) > 191:
            raise HTTPException(422, "UP 主名称无效或过长")
        name = name.strip()
        if name.casefold() in names:
            raise HTTPException(422, "同一批次包含重复 UP 主")
        names.add(name.casefold())
        if set(item) != {"up_name", *CORE_METRICS}:
            raise HTTPException(422, "每项必须包含 up_name 和五个维度")
        values = {metric: item[metric] for metric in CORE_METRICS}
        try:
            validate_standards(values)
        except ConfigurationError as exc:
            raise HTTPException(422, str(exc)) from None
        prepared.append(("up_standards_" + name, json.dumps(values, ensure_ascii=False, allow_nan=False)))
    created = updated = 0
    for key, value in prepared:
        row = session.scalar(select(AlgorithmConfig).where(AlgorithmConfig.config_key == key))
        if row is None:
            row = AlgorithmConfig(config_key=key, description="管理员批量导入的真实基线")
            session.add(row)
            created += 1
        else:
            updated += 1
        row.config_value = value
        row.updated_by = admin.id
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.commit()
    return {"imported": len(prepared), "created": created, "updated": updated}


@router.delete("/{config_key}", status_code=204)
def delete_config(config_key: str, session: Session = Depends(get_session)):
    from app.scoring.calculator import REQUIRED_KEYS
    if config_key in REQUIRED_KEYS:
        raise HTTPException(409, "必要算法配置不能删除，请修改其数值")
    row=session.scalar(select(AlgorithmConfig).where(AlgorithmConfig.config_key==config_key))
    if row is None:
        raise HTTPException(404, "配置不存在")
    session.delete(row)
    session.commit()
