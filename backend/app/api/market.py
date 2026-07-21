"""
증시상황 — 네이버 금융 주요 지수 + 환율 (코스피/코스닥/다우/나스닥/나스닥100/미국USD)
- 국내지수: m.stock.naver.com/api/index/{KOSPI|KOSDAQ}/basic
- 해외지수: api.stock.naver.com/index/{.DJI|.IXIC|.NDX}/basic
  → closePrice + compareToPreviousClosePrice(절대값) + compareToPreviousPrice.code(1·2=상승,4·5=하락)
- 환율(USD/KRW): api.stock.naver.com/marketindex/exchange/FX_USDKRW
  → exchangeInfo.closePrice + fluctuations(등락 절대값) + fluctuationsType.code(방향)
  ※ TIGER 나스닥100이 환율 영향을 받아 함께 표시
- price_fetcher와 동일하게 urllib + 캐시(30초) 사용
"""
import json
import urllib.request
from datetime import datetime, timedelta
from fastapi import APIRouter

router = APIRouter(prefix="/market", tags=["증시"])

_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"}
_cache = {"data": None, "at": None}
_TTL = timedelta(seconds=30)

# (표시명, 조회 URL)
_INDICES = [
    ("코스피",     "https://m.stock.naver.com/api/index/KOSPI/basic"),
    ("코스닥",     "https://m.stock.naver.com/api/index/KOSDAQ/basic"),
    ("다우",       "https://api.stock.naver.com/index/.DJI/basic"),
    ("나스닥",     "https://api.stock.naver.com/index/.IXIC/basic"),
    ("나스닥100",  "https://api.stock.naver.com/index/.NDX/basic"),
]

_EXCHANGE_URL = "https://api.stock.naver.com/marketindex/exchange/FX_USDKRW"


def _num(s):
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=6) as r:
        return json.load(r)


def _parse(name: str, d: dict) -> dict:
    close = _num(d.get("closePrice"))
    comp = _num(d.get("compareToPreviousClosePrice"))  # 절대값
    code = str((d.get("compareToPreviousPrice") or {}).get("code", ""))
    sign = -1 if code in ("4", "5") else 1
    change = round(comp * sign, 2)
    prev = round(close - change, 2)
    ratio = round((change / prev * 100), 2) if prev else 0.0
    return {"name": name, "today": close, "prev": prev, "change": change, "ratio": ratio}


def _parse_exchange(d: dict) -> dict:
    """환율(USD/KRW) — exchangeInfo 구조 파싱"""
    ei = d.get("exchangeInfo", {})
    close = _num(ei.get("closePrice"))
    fluc = _num(ei.get("fluctuations"))  # 등락 절대값
    code = str((ei.get("fluctuationsType") or {}).get("code", ""))
    sign = -1 if code in ("4", "5") else 1
    change = round(fluc * sign, 2)
    prev = round(close - change, 2)
    ratio = round((change / prev * 100), 2) if prev else 0.0
    return {"name": "미국USD", "today": close, "prev": prev, "change": change, "ratio": ratio}


@router.get("/indices")
def indices():
    """주요 5개 지수의 금일/전일/등락"""
    now = datetime.now()
    if _cache["data"] and _cache["at"] and now - _cache["at"] < _TTL:
        return _cache["data"]

    out = []
    for name, url in _INDICES:
        try:
            out.append(_parse(name, _fetch(url)))
        except Exception as e:
            print("[market 오류] %s: %s" % (name, e))
            out.append({"name": name, "today": 0, "prev": 0, "change": 0, "ratio": 0})

    # 환율 USD/KRW (나스닥100 다음 줄)
    try:
        out.append(_parse_exchange(_fetch(_EXCHANGE_URL)))
    except Exception as e:
        print("[market 오류] 미국USD: %s" % e)
        out.append({"name": "미국USD", "today": 0, "prev": 0, "change": 0, "ratio": 0})

    _cache["data"] = out
    _cache["at"] = now
    return out
