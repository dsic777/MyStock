import threading
from fastapi import APIRouter
from app.core.database import SessionLocal
from app.models.models import Account, Stock, SellHistory, Settings
from seed import run_seed

router = APIRouter(prefix="/demo", tags=["데모"])

# 초기화를 여러 번 눌러도 한 번에 하나씩 (동시에 돌면 종목이 여러 벌 생긴다)
_reset_lock = threading.Lock()


@router.post("/reset")
def reset_demo():
    """데모 데이터 초기화 — 기존 종목/계좌 삭제 후 seed 재실행"""
    with _reset_lock:
        return _reset()


def _reset():
    db = SessionLocal()
    try:
        db.query(SellHistory).delete()
        db.query(Stock).delete()
        db.query(Account).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}
    finally:
        db.close()

    run_seed()

    # 초기화 후 현재가 · 고점가(지난주 금요일부터 최고가) 1회 갱신
    from app.services.trailing_stop import refresh_highs_job
    refresh_highs_job(force=True)

    return {"success": True, "message": "데모 데이터가 초기화되었습니다."}
