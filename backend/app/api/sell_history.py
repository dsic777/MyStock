from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import SellHistory
from app.schemas.schemas import SellHistoryResponse
from app.api.auth import get_current_user

router = APIRouter(prefix="/sell-history", tags=["매도이력"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[SellHistoryResponse])
def get_sell_history(account_id: int = None, db: Session = Depends(get_db)):
    """매도 이력 조회 (최신순)"""
    query = db.query(SellHistory)
    if account_id:
        query = query.filter(SellHistory.account_id == account_id)
    return query.order_by(SellHistory.sold_at.desc()).all()
