"""
트레일링 스탑 상태/알림 헬퍼 (데모)
- 손절가·상태(정상/주의/매도) 계산 (표시용)
- 알림 큐(SSE 전달용) — 데모 버전에서는 채워지지 않음
- 자동매도·실주문·스케줄러 기능은 데모에서 제거됨
"""
from datetime import datetime
from app.models.models import Stock, Settings

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
