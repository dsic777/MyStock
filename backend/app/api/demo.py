from fastapi import APIRouter
from app.core.database import SessionLocal
from app.models.models import Account, Stock, SellHistory, Settings
from seed import run_seed

router = APIRouter(prefix="/demo", tags=["데모"])


@router.post("/reset")
def reset_demo():
    """데모 데이터 초기화 — 기존 종목/계좌 삭제 후 seed 재실행"""
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

    # 초기화 후 현재가 1회 갱신
    db2 = SessionLocal()
    try:
        from app.services.price_fetcher import get_current_price
        stocks = db2.query(Stock).filter(Stock.is_active == True).all()
        for s in stocks:
            price = get_current_price(s.code)
            if price > 0:
                s.current_price = price
                if price > s.high_price:
                    s.high_price = price
        db2.commit()
    except Exception:
        db2.rollback()
    finally:
        db2.close()

    return {"success": True, "message": "데모 데이터가 초기화되었습니다."}
