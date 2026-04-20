from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─────────────────────────────────────────────
# 인증
# ─────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─────────────────────────────────────────────
# 계좌
# ─────────────────────────────────────────────

class AccountCreate(BaseModel):
    account_no: str
    account_name: str
    account_type: str = "일반"
    broker: str = "키움증권"

class AccountResponse(BaseModel):
    id: int
    account_no: str
    account_name: str
    account_type: str
    broker: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# 종목
# ─────────────────────────────────────────────

class StockCreate(BaseModel):
    account_id: int
    code: str
    name: str
    stock_type: str = "개별주"
    buy_price: int
    quantity: int
    high_price: Optional[int] = None        # None이면 매입가로 초기화
    current_price: Optional[int] = 0
    trailing_rate: Optional[float] = None   # None이면 기본값 적용
    sell_mode: Optional[str] = None         # None이면 기본값 적용

class StockUpdate(BaseModel):
    buy_price: Optional[int] = None
    quantity: Optional[int] = None
    high_price: Optional[int] = None
    current_price: Optional[int] = None
    trailing_rate: Optional[float] = None
    sell_mode: Optional[str] = None
    is_active: Optional[bool] = None

class StockResponse(BaseModel):
    id: int
    account_id: int
    code: str
    name: str
    stock_type: str
    buy_price: int
    quantity: int
    high_price: int
    current_price: int
    trailing_rate: Optional[float]
    sell_mode: Optional[str]
    is_active: bool
    # 계산값 (model property)
    buy_amount: int
    eval_amount: int
    profit_loss: int
    profit_rate: float
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# 매도 이력
# ─────────────────────────────────────────────

class SellHistoryResponse(BaseModel):
    id: int
    account_id: int
    code: str
    name: str
    stock_type: str
    sell_price: int
    buy_price: int
    quantity: int
    profit_loss: int
    profit_rate: float
    sell_type: str
    ai_opinion: Optional[str]
    sold_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    default_trailing_rate: Optional[float] = None
    etf_trailing_rate: Optional[float] = None
    warning_rate: Optional[float] = None
    etf_warning_rate: Optional[float] = None
    default_sell_mode: Optional[str] = None
    claude_ai_enabled: Optional[bool] = None
    sound_enabled: Optional[bool] = None

class SettingsResponse(BaseModel):
    id: int
    default_trailing_rate: float
    etf_trailing_rate: float
    warning_rate: float
    etf_warning_rate: float
    default_sell_mode: str
    claude_ai_enabled: bool
    sound_enabled: bool

    class Config:
        from_attributes = True
