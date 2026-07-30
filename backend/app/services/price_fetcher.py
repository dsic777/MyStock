"""
네이버 금융 실시간 시세 (장중 당일 데이터, 코스피/코스닥 코드로 자동 판별)
- m.stock.naver.com basic API 에서 현재가 + 전일종가를 한 번에 조회
- KRX 소스라 증권사 값과 일치. 캐시로 과호출 방지. 실패 시 DEMO_PRICES 폴백.
- (yfinance는 한국 장중 데이터를 못 줘서 폐기)
"""
import json
import urllib.request
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# 캐시: code -> ((current, prev_close), time)
_cache: dict[str, tuple[tuple[int, int], datetime]] = {}
_CACHE_TTL = timedelta(seconds=30)

_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"}

# 네이버 조회 실패 시에만 쓰는 폴백 시세 (직전 스냅샷)
DEMO_PRICES = {
    "000660": 1764000,  # SK하이닉스
    "005490": 302500,   # POSCO홀딩스
    "005930": 244000,   # 삼성전자
    "034020": 64800,    # 두산에너빌리티
    "042700": 222000,   # 한미반도체
    "058470": 69100,    # 리노공업
    "086520": 73500,    # 에코프로
    "196170": 269500,   # 알테오젠
    "133690": 187360,   # TIGER나스닥100 ISA
}


def _naver_quote(code: str):
    """네이버에서 (현재가, 전일종가) 반환. 실패 시 None"""
    url = "https://m.stock.naver.com/api/stock/%s/basic" % code
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=5) as r:
            d = json.load(r)
        cur = int(str(d["closePrice"]).replace(",", ""))
        diff = int(str(d["compareToPreviousClosePrice"]).replace(",", ""))  # 전일대비(1주, 부호포함)
        if cur > 0:
            return cur, cur - diff  # (현재가, 전일종가)
    except Exception as e:
        print("[naver 오류] %s: %s" % (code, e))
    return None


def _quote(code: str):
    now = datetime.now()
    if code in _cache:
        v, t = _cache[code]
        if now - t < _CACHE_TTL:
            return v
    q = _naver_quote(code)
    if q:
        _cache[code] = (q, now)
    return q


def prefetch(codes) -> None:
    """여러 종목 시세를 병렬로 미리 조회해 캐시에 채운다 (순차 호출 병목 제거).
    이미 캐시에 있는 종목은 _quote 내부에서 네트워크 없이 통과."""
    uniq = list({c for c in codes if c})
    if not uniq:
        return
    with ThreadPoolExecutor(max_workers=min(10, len(uniq))) as ex:
        list(ex.map(_quote, uniq))


def get_current_price(code: str) -> int:
    """현재가 (네이버 실시간). 실패 시 DEMO_PRICES, 없으면 0"""
    q = _quote(code)
    if q:
        return q[0]
    return DEMO_PRICES.get(code, 0)


def get_prev_close(code: str) -> int:
    """전일종가 (네이버, 증권사와 일치). 실패 시 0"""
    q = _quote(code)
    if q:
        return q[1]
    return 0
