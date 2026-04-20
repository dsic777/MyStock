"""
데모용 초기 데이터 생성
- 앱 시작 시 호출 (main.py lifespan)
- 데모 계좌 1개 + 종목 6개 자동 생성
- 이미 데이터가 있으면 건너뜀 (중복 방지)
- 매입가: 랜덤 매입일(1년전~1개월전)의 실제 역사 종가 (yfinance)
- 고점가: 매입일부터 오늘까지의 실제 최고가 (yfinance)
"""
import random
from datetime import datetime, timedelta
import yfinance as yf
from app.core.database import SessionLocal
from app.models.models import Account, Stock, Settings


DEMO_STOCKS = [
    {"name": "삼성전자",      "code": "005930", "stock_type": "주식", "quantity": 15},
    {"name": "SK하이닉스",    "code": "000660", "stock_type": "주식", "quantity": 5},
    {"name": "NAVER",         "code": "035420", "stock_type": "주식", "quantity": 4},
    {"name": "카카오",         "code": "035720", "stock_type": "주식", "quantity": 20},
    {"name": "LG에너지솔루션", "code": "373220", "stock_type": "주식", "quantity": 2},
    {"name": "KODEX 200",     "code": "069500", "stock_type": "ETF",  "quantity": 30},
]


def _get_buy_price_and_high(code: str) -> tuple[int, int]:
    """
    랜덤 매입일(1년전~1개월전) 선택 →
    그 날의 종가를 매입가로, 매입일~오늘 최고가를 고점가로 반환
    """
    today = datetime.now().date()
    date_from = today - timedelta(days=365)
    date_to   = today - timedelta(days=30)

    # 랜덤 매입일 선택
    random_days = random.randint(0, (date_to - date_from).days)
    buy_date = date_from + timedelta(days=random_days)

    symbol = f"{code}.KS"
    try:
        ticker = yf.Ticker(symbol)
        # 매입일 전후 5일치 데이터 (주말/공휴일 보정)
        hist_buy = ticker.history(
            start=(buy_date - timedelta(days=5)).isoformat(),
            end=(buy_date + timedelta(days=5)).isoformat(),
        )
        if hist_buy.empty:
            raise ValueError("매입일 근처 데이터 없음")
        buy_price = int(hist_buy["Close"].iloc[-1])

        # 매입일~오늘 최고가
        hist_high = ticker.history(
            start=buy_date.isoformat(),
            end=today.isoformat(),
        )
        high_price = int(hist_high["High"].max()) if not hist_high.empty else buy_price

        print(f"  [{code}] 매입일={buy_date} 매입가={buy_price:,} 고점가={high_price:,}")
        return buy_price, high_price

    except Exception as e:
        print(f"  [{code}] yfinance 오류: {e} — 현재가로 대체")
        # 실패 시 현재가 조회
        from app.services.price_fetcher import get_current_price
        price = get_current_price(code)
        return price, price


def run_seed():
    """데모 데이터 초기화 (이미 있으면 건너뜀)"""
    db = SessionLocal()
    try:
        # 이미 계좌가 있으면 건너뜀
        if db.query(Account).first():
            print("[seed] 데이터 이미 존재 — 건너뜀")
            return

        print("[seed] 데모 데이터 생성 시작...")

        # 기본 설정값 생성
        if not db.query(Settings).first():
            db.add(Settings())
            db.commit()

        # 데모 계좌 생성
        account = Account(
            account_no="0000000000",
            account_name="데모 계좌",
            is_active=True,
        )
        db.add(account)
        db.commit()
        db.refresh(account)
        print(f"[seed] 계좌 생성: {account.account_name} (id={account.id})")

        # 종목 6개 생성
        for item in DEMO_STOCKS:
            buy_price, high_price = _get_buy_price_and_high(item["code"])
            stock = Stock(
                account_id=account.id,
                code=item["code"],
                name=item["name"],
                stock_type=item["stock_type"],
                quantity=item["quantity"],
                buy_price=buy_price,
                high_price=high_price,
                current_price=high_price,  # 초기값, 스케줄러가 곧 갱신
                is_active=True,
            )
            db.add(stock)

        db.commit()
        print("[seed] 데모 데이터 생성 완료!")

    except Exception as e:
        print(f"[seed] 오류: {e}")
        db.rollback()
    finally:
        db.close()
