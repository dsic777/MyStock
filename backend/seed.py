"""
데모용 초기 데이터 생성 (오라클 테스트모드)
- 앱 시작 시 호출 (main.py lifespan)
- 실제 거래가 스냅샷 고정: 매입가/전일가(전영업일 종가)/현재가
- 현재가는 price_fetcher.DEMO_PRICES 에서 (스케줄러/로그인 갱신에도 고정 유지)
- 이미 데이터가 있으면 건너뜀 (중복 방지)
"""
from app.core.database import SessionLocal
from app.models.models import Account, Stock, Settings
from app.services.price_fetcher import get_current_price, get_prev_close


# name, code, 유형, 수량, 매입가, 전일가(전영업일 종가)
DEMO_STOCKS = [
    {"name": "SK하이닉스",         "code": "000660", "stock_type": "주식", "quantity": 2,  "buy_price": 306111, "prev_close": 1812000},
    {"name": "POSCO홀딩스",        "code": "005490", "stock_type": "주식", "quantity": 3,  "buy_price": 375333, "prev_close": 309000},
    {"name": "삼성전자",           "code": "005930", "stock_type": "주식", "quantity": 5,  "buy_price": 62350,  "prev_close": 253500},
    {"name": "두산에너빌리티",      "code": "034020", "stock_type": "주식", "quantity": 5,  "buy_price": 85500,  "prev_close": 69300},
    {"name": "한미반도체",         "code": "042700", "stock_type": "주식", "quantity": 10, "buy_price": 298250, "prev_close": 239500},
    {"name": "리노공업",           "code": "058470", "stock_type": "주식", "quantity": 7,  "buy_price": 76400,  "prev_close": 71500},
    {"name": "에코프로",           "code": "086520", "stock_type": "주식", "quantity": 2,  "buy_price": 95000,  "prev_close": 79600},
    {"name": "알테오젠",           "code": "196170", "stock_type": "주식", "quantity": 2,  "buy_price": 408500, "prev_close": 276500},
    {"name": "TIGER나스닥100 ISA", "code": "133690", "stock_type": "ETF",  "quantity": 32, "buy_price": 158480, "prev_close": 193610},
]


def run_seed():
    """데모 데이터 초기화 (이미 있으면 건너뜀)"""
    db = SessionLocal()
    try:
        if db.query(Account).first():
            print("[seed] 데이터 이미 존재 — 건너뜀")
            return

        print("[seed] 데모 데이터 생성 시작...")

        if not db.query(Settings).first():
            db.add(Settings())
            db.commit()

        account = Account(account_no="0000000000", account_name="데모 계좌", is_active=True)
        db.add(account)
        db.commit()
        db.refresh(account)
        print(f"[seed] 계좌 생성: {account.account_name} (id={account.id})")

        for item in DEMO_STOCKS:
            buy_price = item["buy_price"]
            prev_close = get_prev_close(item["code"]) or item["prev_close"]   # 실시간 전영업일 종가
            current = get_current_price(item["code"]) or item["prev_close"]    # 실시간 현재가
            high_price = max(buy_price, current, prev_close)
            stock = Stock(
                account_id=account.id,
                code=item["code"],
                name=item["name"],
                stock_type=item["stock_type"],
                quantity=item["quantity"],
                buy_price=buy_price,
                high_price=high_price,
                current_price=current,
                prev_close=prev_close,
                is_active=True,
            )
            db.add(stock)
            print(f"  [{item['code']}] {item['name']} 매입={buy_price:,} 전일={prev_close:,} 현재={current:,}")

        db.commit()
        print("[seed] 데모 데이터 생성 완료!")

    except Exception as e:
        print(f"[seed] 오류: {e}")
        db.rollback()
    finally:
        db.close()
