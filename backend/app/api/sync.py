from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.dependencies import require_admin

router = APIRouter(prefix="/api/admin/sync", dependencies=[Depends(require_admin)])


@router.get("/status")
def sync_status(request: Request):
    return request.app.state.sync_service.status()


@router.post("/run", status_code=202)
def sync_run(request: Request):
    if not request.app.state.sync_service.trigger():
        raise HTTPException(status_code=409, detail="同步正在运行或服务已关闭")
    return {"accepted": True}
