"""
알림 API
- GET /alerts          : 최근 알림 목록
- GET /alerts/stream   : SSE 실시간 스트림
"""
import asyncio
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.services.trailing_stop import get_alerts
from app.api.auth import get_current_user, verify_token_str

router = APIRouter(prefix="/alerts", tags=["알림"])


@router.get("/", dependencies=[Depends(get_current_user)])
def list_alerts(after_id: int = 0):
    """최근 알림 조회 (after_id 이후 항목만)"""
    return {"alerts": get_alerts(after_id)}


@router.get("/stream")
async def alert_stream(after_id: int = 0, token: str = Query(...)):
    """SSE — 새 알림이 생기면 즉시 전달 (token 쿼리파라미터로 인증)"""
    verify_token_str(token)

    async def event_generator():
        last_id = after_id
        while True:
            new_alerts = get_alerts(last_id)
            if new_alerts:
                import json
                for alert in new_alerts:
                    last_id = alert["id"]
                    data = json.dumps(alert, ensure_ascii=False)
                    yield f"data: {data}\n\n"
            await asyncio.sleep(3)  # 3초마다 확인

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
