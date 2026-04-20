from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """로그인 인증 계정"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())


class Account(Base):
    """증권 계좌 (일반/ISA 등)"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_no = Column(String, unique=True, nullable=False)   # 계좌번호
    account_name = Column(String, nullable=False)              # 계좌명 (예: 일반계좌)
    account_type = Column(String, default="일반")              # 일반/ISA/연금저축/IRP
    broker = Column(String, default="키움증권")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    stocks = relationship("Stock", back_populates="account")
    sell_histories = relationship("SellHistory", back_populates="account")


class Stock(Base):
    """보유 종목"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    code = Column(String, nullable=False)          # 종목코드 (예: 000660)
    name = Column(String, nullable=False)          # 종목명 (예: SK하이닉스)
    stock_type = Column(String, default="개별주")  # 개별주/ETF
    buy_price = Column(Integer, nullable=False)    # 매입가 (1주당)
    quantity = Column(Integer, nullable=False)     # 보유수량
    high_price = Column(Integer, default=0)        # 최근 고점가 (트레일링 기준)
    current_price = Column(Integer, default=0)     # 현재가 (마지막 조회값)
    trailing_rate = Column(Float, nullable=True)   # 개별 트레일링 비율 (NULL이면 기본값 사용)
    sell_mode = Column(String, nullable=True)      # 자동/확인/알림 (NULL이면 기본값)
    is_active = Column(Boolean, default=True)      # 모니터링 여부
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    account = relationship("Account", back_populates="stocks")

    @property
    def effective_trailing_rate(self):
        """실제 적용되는 트레일링 비율 (개별 설정 우선, 없으면 settings 기본값)"""
        return self.trailing_rate  # None이면 API에서 settings 기본값 적용

    @property
    def stop_price(self):
        """손절가 = 고점가 × (1 + trailing_rate)  — trailing_rate는 음수"""
        if self.high_price and self.trailing_rate is not None:
            return int(self.high_price * (1 + self.trailing_rate / 100))
        return None

    @property
    def buy_amount(self):
        """매입금액 = 매입가 × 수량"""
        return self.buy_price * self.quantity

    @property
    def eval_amount(self):
        """평가금액 = 현재가 × 수량"""
        return self.current_price * self.quantity

    @property
    def profit_loss(self):
        """평가손익 = 평가금액 - 매입금액"""
        return self.eval_amount - self.buy_amount

    @property
    def profit_rate(self):
        """수익률 (%)"""
        if self.buy_amount == 0:
            return 0.0
        return round((self.profit_loss / self.buy_amount) * 100, 2)


class SellHistory(Base):
    """매도 이력"""
    __tablename__ = "sell_history"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    stock_type = Column(String, default="개별주")
    sell_price = Column(Integer, nullable=False)    # 매도가
    buy_price = Column(Integer, nullable=False)     # 매입가
    quantity = Column(Integer, nullable=False)      # 매도수량
    profit_loss = Column(Integer, default=0)        # 손익금액
    profit_rate = Column(Float, default=0.0)        # 손익률 (%)
    sell_type = Column(String, default="수동")      # 자동/수동
    ai_opinion = Column(Text, nullable=True)        # Claude AI 의견
    sold_at = Column(DateTime, default=func.now())

    account = relationship("Account", back_populates="sell_histories")


class Settings(Base):
    """전체 기본 설정 (항상 1개 row만 존재)"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    default_trailing_rate = Column(Float, default=-9.0)   # 개별주 기본 트레일링 비율
    etf_trailing_rate = Column(Float, default=-9.0)       # ETF 기본 트레일링 비율
    warning_rate = Column(Float, default=-7.0)            # 개별주 주의 알림 기준
    etf_warning_rate = Column(Float, default=-5.0)        # ETF 주의 알림 기준
    default_sell_mode = Column(String, default="확인")    # 자동/확인/알림
    claude_ai_enabled = Column(Boolean, default=True)     # Claude AI 의견 사용여부
    sound_enabled = Column(Boolean, default=True)         # 알림 소리 사용여부
