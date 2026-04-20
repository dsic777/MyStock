"""
트레일링 스탑 서비스
- 1분마다 현재가 갱신 + 고점가 업데이트
- 매도/주의 상태 감지 → 알림 큐에 추가
- 자동 모드: 즉시 키움 매도 주문
"""
from datetime import datetime
from app.core.database import SessionLocal
from app.models.models import Stock, Settings, Account, SellHistory

from app.services.price_fetcher import get_current_price
from app.kiwoom.kiwoom_bridge import is_connected, sell_stock

# ─────────────────────────────────────────────
# 알림 큐 (SSE로 프론트에 전달)
# ─────────────────────────────────────────────
alert_queue: list[dict] = []
_seen_rcept_nos: set = set()  # 중복 공시 방지


def add_alert(stock: Stock, status: str, stop_price: int, sell_mode: str, applied_rate: float, auto_sold: bool = False):
    """알림 큐에 추가"""
    profit_rate = round((stock.current_price - stock.buy_price) / stock.buy_price * 100, 2) if stock.buy_price else 0
    alert_queue.append({
        "id": len(alert_queue) + 1,
        "stock_id": stock.id,
        "account_id": stock.account_id,
        "code": stock.code,
        "name": stock.name,
        "stock_type": stock.stock_type,
        "status": status,
        "sell_mode": sell_mode,
        "current_price": stock.current_price,
        "stop_price": stop_price,
        "high_price": stock.high_price,
        "buy_price": stock.buy_price,
        "quantity": stock.quantity,
        "profit_rate": profit_rate,
        "trailing_rate": applied_rate,
        "auto_sold": auto_sold,
        "timestamp": datetime.now().isoformat(),
    })
    if len(alert_queue) > 100:
        alert_queue.pop(0)


def get_alerts(after_id: int = 0) -> list[dict]:
    """after_id 이후 알림만 반환"""
    return [a for a in alert_queue if a["id"] > after_id]


# ─────────────────────────────────────────────
# 트레일링 스탑 로직
# ─────────────────────────────────────────────

def calc_stop_price(stock: Stock, settings: Settings) -> int:
    """손절가 = 고점가 × (1 + rate/100)  — rate는 음수(-9.0)"""
    if stock.high_price == 0:
        return 0
    if stock.trailing_rate is not None:
        rate = stock.trailing_rate
    elif stock.stock_type == "ETF":
        rate = settings.etf_trailing_rate
    else:
        rate = settings.default_trailing_rate
    return int(stock.high_price * (1 + rate / 100))


def get_applied_rate(stock: Stock, settings: Settings) -> float:
    if stock.trailing_rate is not None:
        return stock.trailing_rate
    elif stock.stock_type == "ETF":
        return settings.etf_trailing_rate
    return settings.default_trailing_rate


def get_stock_status(stock: Stock, stop_price: int, settings: Settings) -> str:
    if stock.current_price == 0 or stop_price == 0:
        return "정상"
    if stock.current_price <= stop_price:
        return "매도"
    gap_rate = (stock.current_price - stop_price) / stop_price * 100
    warn = abs(settings.etf_warning_rate if stock.stock_type == "ETF" else settings.warning_rate)
    if gap_rate <= warn:
        return "주의"
    return "정상"


# ─────────────────────────────────────────────
# 자동 매도 실행
# ─────────────────────────────────────────────

def execute_auto_sell(stock: Stock, stop_price: int, applied_rate: float, db):
    """자동 모드: 키움 주문 + 매도이력 저장 + 종목 비활성화"""
    current_price = stock.current_price
    profit_loss = (current_price - stock.buy_price) * stock.quantity
    profit_rate = round((current_price - stock.buy_price) / stock.buy_price * 100, 2) if stock.buy_price else 0

    # Claude AI 의견 (자동매도 이력에 기록)
    ai_opinion = ""
    try:
        from app.api.ai import fetch_claude_opinion, OpinionRequest
        req = OpinionRequest(
            name=stock.name, code=stock.code, stock_type=stock.stock_type,
            current_price=current_price, stop_price=stop_price,
            high_price=stock.high_price, buy_price=stock.buy_price,
            profit_rate=profit_rate, trailing_rate=applied_rate,
        )
        ai_opinion, _, _ = fetch_claude_opinion(req)
    except Exception as e:
        print(f"[자동매도] AI 의견 조회 실패: {e}")

    # 키움 주문
    kiwoom_ok = False
    if is_connected():
        account = db.query(Account).filter(Account.id == stock.account_id).first()
        if account:
            result = sell_stock(account.account_no, stock.code, stock.quantity)
            kiwoom_ok = result.get("success", False)
            print(f"[자동매도] {stock.name} 키움 주문: {result}")

    # 매도이력 저장
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
        sell_type="자동",
        ai_opinion=ai_opinion or None,
    )
    db.add(history)
    stock.is_active = False

    add_alert(stock, "매도", stop_price, "자동", applied_rate, auto_sold=True)
    print(f"[자동매도] {stock.name} 완료 (키움={'성공' if kiwoom_ok else '미연결/실패'})")


# ─────────────────────────────────────────────
# 스케줄러 작업
# ─────────────────────────────────────────────

def update_prices_job():
    """1분마다 실행: 현재가 갱신 + 트레일링 스탑 체크 (yfinance)"""
    db = SessionLocal()
    try:
        settings = db.query(Settings).first()
        if not settings:
            settings = Settings()
            db.add(settings)
            db.commit()

        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        updated = 0
        alerts = []

        for stock in stocks:
            price = get_current_price(stock.code)
            if price <= 0:
                continue

            prev_status = get_stock_status(stock, calc_stop_price(stock, settings), settings)

            stock.current_price = price
            if price > stock.high_price:
                stock.high_price = price

            stop_price = calc_stop_price(stock, settings)
            new_status = get_stock_status(stock, stop_price, settings)
            applied_rate = get_applied_rate(stock, settings)
            sell_mode = stock.sell_mode or settings.default_sell_mode

            # 상태 변화 감지
            if new_status != "정상" and new_status != prev_status:
                if new_status == "매도" and sell_mode == "자동":
                    execute_auto_sell(stock, stop_price, applied_rate, db)
                else:
                    add_alert(stock, new_status, stop_price, sell_mode, applied_rate)
                alerts.append(f"{stock.name}({new_status}/{sell_mode})")

            updated += 1

        db.commit()
        now = datetime.now().strftime("%H:%M:%S")
        msg = f"[스케줄러] {now} — {updated}개 종목 갱신"
        if alerts:
            msg += f" | 알림: {', '.join(alerts)}"
        print(msg)

    except Exception as e:
        print(f"[스케줄러 오류] {e}")
        db.rollback()
    finally:
        db.close()


# ─────────────────────────────────────────────
# DART 공시 알림
# ─────────────────────────────────────────────

def check_dart_job():
    """30분마다 실행: 보유 종목 공시 조회 → 신규 공시 알림"""
    from app.core.config import DART_API_KEY
    from app.kiwoom.dart_bridge import get_recent_disclosures

    if not DART_API_KEY:
        print("[DART] API 키 미설정 — 건너뜀")
        return

    db = SessionLocal()
    try:
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        if not stocks:
            return

        new_count = 0
        for stock in stocks:
            disclosures = get_recent_disclosures(DART_API_KEY, stock.code, count=3)
            for d in disclosures:
                rcept_no = d.get("rcept_no", "")
                if not rcept_no or rcept_no in _seen_rcept_nos:
                    continue
                _seen_rcept_nos.add(rcept_no)
                alert_queue.append({
                    "id": len(alert_queue) + 1,
                    "type": "dart",
                    "code": stock.code,
                    "name": stock.name,
                    "status": "공시",
                    "title": d.get("title", ""),
                    "date": d.get("date", ""),
                    "rcept_no": rcept_no,
                    "timestamp": datetime.now().isoformat(),
                })
                if len(alert_queue) > 100:
                    alert_queue.pop(0)
                new_count += 1
                print(f"[DART] 공시 알림: {stock.name} — {d.get('title', '')}")

        now = datetime.now().strftime("%H:%M:%S")
        print(f"[DART] {now} — {len(stocks)}개 종목 확인, 신규 공시 {new_count}건")

    except Exception as e:
        print(f"[DART 오류] {e}")
    finally:
        db.close()
