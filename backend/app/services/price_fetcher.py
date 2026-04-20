"""
yfinance를 이용한 한국 주식 현재가 조회
- 종목코드(6자리) → {코드}.KS 형식으로 조회
- 1분 캐시 적용 (중복 호출 방지)
- 장 마감 후에도 당일 종가 반환
"""
import yfinance as yf
from datetime import datetime, timedelta

# 캐시: {종목코드: (가격, 조회시각)}
_cache: dict[str, tuple[int, datetime]] = {}
_CACHE_TTL = timedelta(minutes=1)


def get_current_price(code: str) -> int:
    """
    한국 주식 현재가 조회 (yfinance, 15분 지연)
    code: 6자리 종목코드 (예: "005930")
    반환: 현재가 (int), 실패 시 0
    """
    now = datetime.now()

    # 캐시 확인
    if code in _cache:
        cached_price, cached_at = _cache[code]
        if now - cached_at < _CACHE_TTL:
            return cached_price

    symbol = f"{code}.KS"
    try:
        ticker = yf.Ticker(symbol)
        # fast_info로 빠르게 시도
        price = ticker.fast_info.last_price
        if price and price > 0:
            result = int(price)
            _cache[code] = (result, now)
            print(f"[yfinance] {code}: {result:,}원")
            return result

        # 실패 시 history로 재시도
        hist = ticker.history(period="1d")
        if not hist.empty:
            result = int(hist["Close"].iloc[-1])
            _cache[code] = (result, now)
            print(f"[yfinance-hist] {code}: {result:,}원")
            return result

    except Exception as e:
        print(f"[yfinance 오류] {code}: {e}")

    return 0
