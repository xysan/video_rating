from datetime import datetime, timedelta, timezone
from copy import deepcopy
from decimal import Decimal
from io import BytesIO, StringIO
import csv
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_session
from app.auth.dependencies import require_admin
from app.models import VideoSnapshot, Score
from app.api.scores import filtered_rows, public_video, score_filters
from app.api.management import csv_safe
from app.scoring.configuration import load_configs
from app.scoring.calculator import calculate_video_score, validate_rules, REQUIRED_KEYS
from app.scoring.task import extract_metrics, fingerprint, calculation_lock

router=APIRouter(dependencies=[Depends(require_admin)])

class Extras(BaseModel):
    difficulty: Literal['S','A','B'] | None = None
    efficiency: Literal['按时','推迟1-2天','推迟2-3天','推迟3-5天','推迟5天以上'] | None = None
    traffic_ratio: float | None = Field(default=None,ge=0,le=1,allow_inf_nan=False)

@router.put('/api/admin/videos/{video_id}/extras')
def update_extras(video_id: int, body: Extras, session: Session=Depends(get_session)):
    # 与定时评分共享锁；字段修改和评分写入处于同一事务，失败全部回滚。
    with calculation_lock:
        try:
            video=session.scalar(select(VideoSnapshot).where(VideoSnapshot.id==video_id).with_for_update())
            if video is None: raise HTTPException(404,'视频不存在')
            configs=load_configs(session)
            validate_rules(configs)
            rules={k:configs[k] for k in REQUIRED_KEYS}
            if video.publish_date > datetime.now(timezone(timedelta(hours=8))).date()-timedelta(days=rules['calculation_age_days']):
                raise HTTPException(409,'尚未达到评分日龄，未保存修改')
            standards=configs.get('up_standards_'+video.up_name)
            if standards is None: raise HTTPException(409,'缺失该 UP 主基线，未保存修改')
            payload=deepcopy(video.raw_payload)
            fields=payload.setdefault('fields',{})
            for key,name in {'difficulty':'制作难度','efficiency':'时效情况','traffic_ratio':'投流情况'}.items():
                fields[rules['metric_fields'].get(key) or name]=getattr(body,key)
                fields[name]=getattr(body,key)
            payload['_admin_extras']=body.model_dump()
            metrics=extract_metrics(payload,rules['metric_fields'])
            metrics.update(body.model_dump())
            result=calculate_video_score(metrics,standards,rules)
            if result['status']=='error': raise HTTPException(409,result['message'])
            video.raw_payload=payload
            score=session.scalar(select(Score).where(Score.video_snapshot_id==video_id,Score.algorithm_version=='v1.0').with_for_update())
            if score is None:
                score=Score(video_snapshot_id=video_id,algorithm_version='v1.0');session.add(score)
            score.score=Decimal(str(result['final_score']))
            score.calculated_at=datetime.now(timezone.utc).replace(tzinfo=None)
            score.score_detail={**result,'calculation':{'rules':rules,'standards':standards,'metrics':metrics,'input_hash':fingerprint({'raw_payload':payload,'publish_date':video.publish_date,'up_name':video.up_name,'last_modified_at':video.last_modified_at}),'config_hash':fingerprint({'rules':rules,'standards':standards})}}
            session.commit()
            return {'id':video.id,'total_score':score.score,'score_detail':score.score_detail,**body.model_dump()}
        except HTTPException:
            session.rollback();raise
        except (ValueError,TypeError) as exc:
            session.rollback();raise HTTPException(422,str(exc)) from None
        except Exception:
            session.rollback();raise

HEADERS=['ID','BV号','UP主','编导','标题','发布日期','总分','播放量','互动率','3s跳出率','平均播放进度','播转粉率','制作难度','效率情况','榜单','投流情况','播放得分','互动得分','跳出得分','进度得分','播转粉得分','难度得分','效率得分','榜单加分','投流扣分']
KEYS=['id','bv_id','up_name','director','video_title','publish_date','total_score','snapshot_play_count','interact_rate','jump_3s','progress','convert_rate','difficulty','efficiency','tags','traffic_ratio']
DETAILS=['play_score','interact_score','jump_score','progress_score','convert_score','difficulty_score','efficiency_score']
@router.get('/api/admin/scores/export')
def export_scores(format: Literal['csv','xlsx']='csv', filters=Depends(score_filters), session: Session=Depends(get_session)):
    rows=[]
    for row in filtered_rows(session,True,**filters):
        item=public_video(row);detail=row['score_detail'] or {}
        rows.append([item.get(k) for k in KEYS]+[detail.get('score_details',{}).get(k) for k in DETAILS]+[detail.get('bonus_and_penalty',{}).get(k) for k in ['ranking_bonus','traffic_penalty']])
    if format=='csv':
        stream=StringIO();writer=csv.writer(stream);writer.writerow(HEADERS)
        writer.writerows([[csv_safe(v) for v in row] for row in rows])
        content=('\ufeff'+stream.getvalue()).encode('utf-8');mime='text/csv; charset=utf-8'
    else:
        from openpyxl import Workbook
        book=Workbook();sheet=book.active;sheet.title='视频得分';sheet.append(HEADERS)
        for row in rows:
            sheet.append([csv_safe(v) if isinstance(v,str) else v for v in row])
        sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
        stream=BytesIO();book.save(stream);content=stream.getvalue();mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return Response(content,media_type=mime,headers={'Content-Disposition':f'attachment; filename="video_scores.{format}"'})
