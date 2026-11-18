from fastapi import APIRouter, Depends, HTTPException, Request
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/refresh-all", dependencies=[Depends(get_current_user)])

@router.post("", status_code=202)
def refresh_all(request: Request):
    return request.app.state.refresh_service.trigger()

@router.get("/{job_id}")
def refresh_status(job_id: str, request: Request):
    result = request.app.state.refresh_service.status(job_id)
    if result is None:
        raise HTTPException(404, "刷新任务不存在或已过期，请重新刷新")
    return result
