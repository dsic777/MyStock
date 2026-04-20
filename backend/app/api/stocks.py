from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Stock, Settings, SellHistory
from app.schemas.schemas import StockCreate, StockUpdate, StockResponse
from app.api.auth import get_current_user
from app.services.price_fetcher import get_current_price

router = APIRouter(prefix="/stocks", tags=["종목"], dependencies=[Depends(get_current_user)])


def get_settings(db: Session) -> Settings:
    """설정값 조회 (없으면 기본값으로 생성)"""
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def calc_stop_price(stock: Stock, settings: Settings) -> int:
    """손절가 계산: 고점가 × (1 + 트레일링비율/100)"""
    if stock.high_price == 0:
        return 0
    # 개별 설정이 없으면 기본값 사용 (ETF는 etf_trailing_rate)
    if stock.trailing_rate is not None:
        rate = stock.trailing_rate
    elif stock.stock_type == "ETF":
        rate = settings.etf_trailing_rate
    else:
        rate = settings.default_trailing_rate
    return int(stock.high_price * (1 + rate / 100))


def get_stock_status(stock: Stock, stop_price: int, settings: Settings) -> str:
    """상태 판단: 정상 / 주의 / 매도"""
    if stock.current_price == 0 or stop_price == 0:
        return "정상"
    if stock.current_price <= stop_price:
        return "매도"
    # 종목 유형별 주의 기준 적용
    if stock.stock_type == "ETF":
        warn = abs(getattr(settings, 'etf_warning_rate', settings.warning_rate))
    else:
        warn = abs(settings.warning_rate)
    gap_rate = (stock.current_price - stop_price) / stop_price * 100
    if gap_rate <= warn:
        return "주의"
    return "정상"


@router.get("/", response_model=list[dict])
def get_stocks(account_id: int = None, db: Session = Depends(get_db)):
    """보유 종목 목록 조회 — DB 값 그대로 반환 (가격 갱신 없음)"""
    settings = get_settings(db)
    query = db.query(Stock).filter(Stock.is_active == True)
    if account_id:
        query = query.filter(Stock.account_id == account_id)
    stocks = query.all()

    result = []
    for s in stocks:
        stop_price = calc_stop_price(s, settings)
        # 실제 적용 트레일링 비율
        if s.trailing_rate is not None:
            applied_rate = s.trailing_rate
        elif s.stock_type == "ETF":
            applied_rate = settings.etf_trailing_rate
        else:
            applied_rate = settings.default_trailing_rate

        result.append({
            "id": s.id,
            "account_id": s.account_id,
            "code": s.code,
            "name": s.name,
            "stock_type": s.stock_type,
            "buy_price": s.buy_price,
            "quantity": s.quantity,
            "high_price": s.high_price,
            "current_price": s.current_price,
            "trailing_rate": applied_rate,
            "sell_mode": s.sell_mode or settings.default_sell_mode,
            "buy_amount": s.buy_price * s.quantity,
            "eval_amount": s.current_price * s.quantity,
            "profit_loss": (s.current_price - s.buy_price) * s.quantity,
            "profit_rate": round((s.current_price - s.buy_price) / s.buy_price * 100, 2) if s.buy_price else 0,
            "stop_price": stop_price,
            "status": get_stock_status(s, stop_price, settings),
            "is_active": s.is_active,
        })
    return result


@router.post("/", response_model=dict)
def create_stock(data: StockCreate, db: Session = Depends(get_db)):
    """종목 수동 등록"""
    stock_data = data.model_dump()
    # 고점가 초기값 = 매입가 (별도 지정 없을 때)
    if not stock_data.get("high_price"):
        stock_data["high_price"] = stock_data["buy_price"]
    stock = Stock(**stock_data)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return {"message": "종목이 등록되었습니다", "id": stock.id}


@router.put("/{stock_id}", response_model=dict)
def update_stock(stock_id: int, data: StockUpdate, db: Session = Depends(get_db)):
    """종목 정보 수정"""
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(stock, field, value)
    db.commit()
    return {"message": "종목 정보가 수정되었습니다"}


@router.post("/{stock_id}/sell", response_model=dict)
def sell_stock_manual(stock_id: int, ai_opinion: str = "", db: Session = Depends(get_db)):
    """확인 모드 매도 실행 — 매도이력 저장 + 종목 비활성화 + 키움 주문"""
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")

    # 최신 현재가 (yfinance)
    current_price = stock.current_price
    price = get_current_price(stock.code)
    if price > 0:
        current_price = price

    profit_loss = (current_price - stock.buy_price) * stock.quantity
    profit_rate = round((current_price - stock.buy_price) / stock.buy_price * 100, 2) if stock.buy_price else 0

    # 매도 이력 저장
    history = SellHistory(
        account_id=stock.account_id,
        code=stock.code,
        name=stock.name,
        stock_type=stock.stock_type,
        sell_price=current_price,
        buy_price=stock.buy_price,
        quantity=stock.quantity,
        profit_loss=profit_loss,
        profit_rate=profit_rate,
        sell_type="수동",
        ai_opinion=ai_opinion or None,
    )
    db.add(history)

    # 종목 비활성화
    stock.is_active = False
    db.commit()

    return {
        "message": "데모 버전에서는 실제 매도가 실행되지 않습니다.",
        "sell_price": current_price,
        "profit_loss": profit_loss,
        "profit_rate": profit_rate,
    }


@router.delete("/{stock_id}")
def delete_stock(stock_id: int, db: Session = Depends(get_db)):
    """종목 모니터링 중단 (비활성화)"""
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")
    stock.is_active = False
    db.commit()
    return {"message": "종목 모니터링이 중단되었습니다"}
