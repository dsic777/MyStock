"""
차트 데이터 — 네이버 fchart 프록시·파싱 (선그래프용 종가 시계열)
- 일/주/월: 네이버 native
- 년: 월 데이터를 연도별 집계
- 분(1분): 네이버 native(분당 종가). 3/5/10/20/30분: 1분 데이터 버킷 집계
"""
import re
import urllib.request
from fastapi import APIRouter, Depends
from app.api.auth import get_current_user

router = APIRouter(prefix="/chart", tags=["차트"], dependencies=[Depends(get_current_user)])

_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _fetch(symbol: str, timeframe: str, count: int):
    """네이버 fchart → [{'t': 날짜, 'c': 종가}] (시간 오름차순)"""
    url = ("https://fchart.stock.naver.com/sise.nhn"
           "?symbol=%s&timeframe=%s&count=%d&requestType=0" % (symbol, timeframe, count))
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=6) as r:
            raw = r.read().decode("euc-kr", errors="ignore")
    except Exception as e:
        print("[chart 오류] %s %s: %s" % (symbol, timeframe, e))
        return []
    out = []
    for it in re.findall(r'data="([^"]+)"', raw):
        p = it.split("|")
        if len(p) < 5:
            continue
        close = p[4]
        if close in ("", "null", "None"):
            continue
        try:
            out.append({"t": p[0], "c": int(float(close))})
        except ValueError:
            continue
    return out


@router.get("/{code}")
def get_chart(code: str, type: str = "minute", unit: str = "1"):
    """선그래프용 종가 시계열. type=minute|day, unit=1/3/5/10/20/30 또는 day/week/month/year"""
    if type == "minute":
        data = _fetch(code, "minute", 3000)
        try:
            n = int(unit)
        except ValueError:
            n = 1
        if n > 1 and data:
            # N분 버킷의 마지막 종가 = N분봉 종가
            data = [data[i] for i in range(n - 1, len(data), n)]
        data = data[-200:]
    else:  # day 계열
        if unit == "year":
            monthly = _fetch(code, "month", 600)
            by_year = {}
            for it in monthly:              # 오름차순이라 마지막 값이 연말 종가
                by_year[it["t"][:4]] = it["c"]
            data = [{"t": y, "c": c} for y, c in by_year.items()]
        else:
            tf = unit if unit in ("day", "week", "month") else "day"
            data = _fetch(code, tf, 250)
        data = data[-200:]

    return {"code": code, "type": type, "unit": unit, "points": data}
