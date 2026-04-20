"""
데모 버전 kiwoom_bridge stub
- 키움 서버 연결 없이 동작하도록 모든 함수를 무해하게 대체
- get_current_price는 yfinance로 위임
"""
from app.services.price_fetcher import get_current_price as yf_get_price


def get_status() -> dict:
    return {"logged_in": False, "message": "데모 버전 — 키움 미연결"}


def get_accounts() -> list:
    return []


def get_holdings(account_no: str) -> list:
    return []


def get_current_price(code: str) -> int:
    return yf_get_price(code)


def is_connected() -> bool:
    return False


def get_high_price_since_buy(code: str, avg_buy_price: int) -> int:
    return 0


def sell_stock(account_no: str, code: str, quantity: int) -> dict:
    return {"success": False, "message": "데모 버전에서는 실제 매도가 실행되지 않습니다."}
