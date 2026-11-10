import csv
import io
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database import get_session
from app.models import User
from app.api.scores import filtered_rows, public_video

router=APIRouter(prefix="/api/admin",dependencies=[Depends(require_admin)])


class RoleUpdate(BaseModel):
    role: Literal["admin","member"]


@router.get("/users")
def users(session: Session=Depends(get_session)):
    return session.execute(select(User.id,User.username,User.display_name,User.role,User.is_active,User.created_at).order_by(User.id)).mappings().all()


@router.put("/users/{user_id}/role")
def update_role(user_id: int, body: RoleUpdate, session: Session=Depends(get_session)):
    user=session.get(User,user_id)
    if user is None:
        raise HTTPException(404,"用户不存在")
    user.role=body.role
    session.commit()
    return {"id":user.id,"role":user.role}


def csv_safe(value):
    value="" if value is None else str(value)
    return "'"+value if value.lstrip().startswith(("=","+","-","@")) or value.startswith(("\t","\r","\n")) else value


@router.get("/export/csv")
def export_csv(session: Session=Depends(get_session)):
    buffer=io.StringIO(newline="")
    writer=csv.writer(buffer)
    keys=("id","bv_id","up_name","video_title","publish_date","director","total_score","algorithm_version","snapshot_play_count","jump_3s","convert_rate","interact_rate","progress")
    writer.writerow(keys)
    for row in filtered_rows(session):
        item=public_video(row)
        writer.writerow(csv_safe(item[k]) for k in keys)
    return Response(content=("\ufeff"+buffer.getvalue()).encode("utf-8"),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":'attachment; filename="video_scores.csv"'})
