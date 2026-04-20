from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.kiwoom.kiwoom_bridge import get_accounts, get_holdings, get_current_price, is_connected, get_high_price_since_buy
from app.models.models import Account, Stock, Settings
from app.api.auth import get_current_user

router = APIRouter(prefix="/kiwoom", tags=["키움API"], dependencies=[Depends(get_current_user)])


@router.get("/status")
def kiwoom_status():
    """키움 서버 연결 상태 확인"""
    connected = is_connected()
    return {
        "connected": connected,
        "message": "키움 연결됨" if connected else "키움 서버 미연결 (kiwoom_server.py 실행 필요)"
    }


@router.post("/sync-accounts")
def sync_accounts(db: Session = Depends(get_db)):
    """키움에서 계좌 목록 가져와서 DB에 저장"""
    if not is_connected():
        raise HTTPException(status_code=503, detail="키움 서버에 연결되지 않았습니다")

    accounts = get_accounts()
    if not accounts:
        raise HTTPException(status_code=404, detail="계좌 정보를 가져올 수 없습니다")

    synced = []
    for account_no in accounts:
        account_no = account_no.strip()
        if not account_no:
            continue
        existing = db.query(Account).filter(Account.account_no == account_no).first()
        if not existing:
            account = Account(
                account_no=account_no,
                account_name=f"계좌_{account_no[-4:]}",  # 뒤 4자리로 임시 이름
                account_type="일반",
                broker="키움증권"
            )
            db.add(account)
            synced.append(account_no)

    db.commit()
    return {"message": f"{len(synced)}개 계좌 동기화 완료", "accounts": accounts}


@router.post("/sync-holdings/{account_id}")
def sync_holdings(account_id: int, db: Session = Depends(get_db)):
    """키움에서 보유종목 가져와서 DB에 저장/갱신"""
    if not is_connected():
        raise HTTPException(status_code=503, detail="키움 서버에 연결되지 않았습니다")

    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="계좌를 찾을 수 없습니다")

    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)
        db.commit()

    holdings = get_holdings(account.account_no)
    if not holdings:
        return {"message": "보유 종목 없음", "synced": 0}

    synced = 0
    for h in holdings:
        code = h.get("code", "").strip()
        if not code:
            continue

        existing = db.query(Stock).filter(
            Stock.account_id == account_id,
            Stock.code == code,
            Stock.is_active == True
        ).first()

        current_price = h.get("current_price", 0)
        buy_price = h.get("buy_price", 0)

        if existing:
            # 현재가, 수량 갱신
            existing.current_price = current_price
            existing.quantity = h.get("quantity", existing.quantity)
            # 고점가 갱신 (현재가가 더 높으면 업데이트)
            if current_price > existing.high_price:
                existing.high_price = current_price
        else:
            # 신규 종목 등록
            stock = Stock(
                account_id=account_id,
                code=code,
                name=h.get("name", code),
                stock_type="ETF" if "ETF" in h.get("name", "") or "TIGER" in h.get("name", "") or "KODEX" in h.get("name", "") else "개별주",
                buy_price=buy_price,
                quantity=h.get("quantity", 0),
                high_price=current_price if current_price > buy_price else buy_price,
                current_price=current_price,
            )
            db.add(stock)
        synced += 1

    db.commit()
    return {"message": f"{synced}개 종목 동기화 완료", "holdings": holdings}


@router.post("/update-prices")
def update_prices(db: Session = Depends(get_db)):
    """전체 보유종목 현재가 일괄 갱신"""
    if not is_connected():
        raise HTTPException(status_code=503, detail="키움 서버에 연결되지 않았습니다")

    stocks = db.query(Stock).filter(Stock.is_active == True).all()
    updated = 0
    for stock in stocks:
        price = get_current_price(stock.code)
        if price > 0:
            stock.current_price = price
            if price > stock.high_price:
                stock.high_price = price
            updated += 1

    db.commit()
    return {"message": f"{updated}개 종목 현재가 갱신 완료"}


@router.post("/recalc-high/{stock_id}")
def recalc_high_price(stock_id: int, db: Session = Depends(get_db)):
    """평균 매입가 기준 추정 매수일부터 최고 고가 재계산"""
    if not is_connected():
        raise HTTPException(status_code=503, detail="키움 서버에 연결되지 않았습니다")

    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다")

    high = get_high_price_since_buy(stock.code, stock.buy_price)
    if high <= 0:
        raise HTTPException(status_code=400, detail="고점가 조회 실패")

    stock.high_price = high
    db.commit()
    return {"message": f"{stock.name} 고점가 재계산 완료", "high_price": high}


@router.post("/recalc-high-all")
def recalc_high_price_all(db: Session = Depends(get_db)):
    """전체 종목 고점가 재계산"""
    if not is_connected():
        raise HTTPException(status_code=503, detail="키움 서버에 연결되지 않았습니다")

    stocks = db.query(Stock).filter(Stock.is_active == True).all()
    results = []
    for stock in stocks:
        high = get_high_price_since_buy(stock.code, stock.buy_price)
        if high > 0:
            stock.high_price = high
            results.append(f"{stock.name}={high:,}")

    db.commit()
    return {"message": f"{len(results)}개 종목 고점가 재계산 완료", "results": results}
