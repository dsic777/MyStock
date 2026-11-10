"""
트레일링 스탑 상태/알림 헬퍼 (데모)
- 손절가·상태(정상/주의/매도) 계산 (표시용)
- 알림 큐(SSE 전달용) — 데모 버전에서는 채워지지 않음
- 시세·고점가 갱신 (목록 조회·로그인·초기화·장중 10분 스케줄러가 같이 씀)
- 자동매도·실주문 기능은 데모에서 제거됨
"""
from datetime import datetime, timedelta, timezone
from app.core.database import SessionLocal
from app.models.models import Stock, Settings
from app.services.price_fetcher import get_current_price, get_prev_close, prefetch

KST = timezone(timedelta(hours=9))


# ─────────────────────────────────────────────
# 시세 · 고점가 갱신
# ─────────────────────────────────────────────
def update_quotes(db, stocks) -> None:
    """현재가·전일가 갱신, 현재가가 고점가보다 높으면 고점가로 올린다"""
    prefetch([s.code for s in stocks])   # 병렬로 캐시에 미리 채움(30초)
    changed = False
    for s in stocks:
        cur = get_current_price(s.code)
        if cur:
            s.current_price = cur
            if cur > s.high_price:
                s.high_price = cur
            changed = True
        pc = get_prev_close(s.code)
        if pc:
            s.prev_close = pc
            changed = True
    if changed:
        db.commit()


def last_friday() -> str:
    """지난주 금요일 (한국 날짜, YYYYMMDD)"""
    today = datetime.now(KST).date()
    monday = today - timedelta(days=today.weekday())
    return (monday - timedelta(days=3)).strftime("%Y%m%d")


def high_since_last_friday(code: str) -> int:
    """지난주 금요일부터 오늘까지 일봉 고가 중 최고. 실패 시 0"""
    from app.api.chart import _fetch   # chart → auth 순환 import 피함
    start = last_friday()
    days = [d for d in _fetch(code, "day", 10) if d["t"][:8] >= start]
    return int(max(d["h"] for d in days)) if days else 0


def refresh_highs(db) -> None:
    """현재가 갱신 + 고점가 = 지난주 금요일부터의 최고가"""
    stocks = db.query(Stock).filter(Stock.is_active == True).all()
    update_quotes(db, stocks)
    for s in stocks:
        h = high_since_last_friday(s.code)
        if h:
            s.high_price = max(h, s.current_price)
    db.commit()
    print("[고점가] 지난주 금요일(%s)부터 최고가 갱신 (%d개 종목)" % (last_friday(), len(stocks)))


def is_market_open() -> bool:
    """평일 09:00 ~ 15:30 (한국 시각)"""
    now = datetime.now(KST)
    return now.weekday() < 5 and "09:00" <= now.strftime("%H:%M") <= "15:30"


def refresh_highs_job(force: bool = False) -> None:
    """스케줄러용 — 장중에만(force 면 언제나) 자체 세션으로 갱신"""
    if not force and not is_market_open():
        return
    db = SessionLocal()
    try:
        refresh_highs(db)
    except Exception as e:
        db.rollback()
        print("[고점가] 갱신 실패: %s" % e)
    finally:
        db.close()

# ─────────────────────────────────────────────
# 알림 큐 (SSE로 프론트에 전달)
# ─────────────────────────────────────────────
alert_queue: list[dict] = []


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
# 트레일링 스탑 상태 계산 (표시용)
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
