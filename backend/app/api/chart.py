"""
차트 데이터 — 선그래프용 종가/손익 시계열
- 개별종목: 네이버 fchart (분 native·집계 / 일·주·월 native / 년 집계)
- 지수: 코스피·코스닥(fchart), 다우·나스닥·나스닥100(foreign chart API), 미국USD(marketindex prices) — 일 계열만
- 손익합계: 보유종목 일봉 시계열 합산(총/일반주/ETF) — 일 계열만
"""
import re
import json
import urllib.request
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Stock
from app.api.auth import get_current_user

router = APIRouter(prefix="/chart", tags=["차트"], dependencies=[Depends(get_current_user)])

_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://m.stock.naver.com/"}


# ─────────────────────────────────────────────
# 네이버 fchart (개별종목·국내지수)
# ─────────────────────────────────────────────
def _fetch(symbol: str, timeframe: str, count: int):
    """네이버 fchart → [{'t','c'}] (오름차순)"""
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
            out.append({"t": p[0], "c": float(close)})
        except ValueError:
            continue
    return out


# ─────────────────────────────────────────────
# 일 → 주/월/년 집계 (기간 마지막 종가)
# ─────────────────────────────────────────────
def _aggregate(daily, unit: str, limit: int = 200):
    if unit == "day" or not daily:
        return [{"t": d["t"], "c": d["c"]} for d in daily][-limit:]

    def period(t: str) -> str:
        if unit == "month":
            return t[:6]
        if unit == "year":
            return t[:4]
        # week
        dt = datetime.strptime(t[:8], "%Y%m%d")
        iy, iw, _ = dt.isocalendar()
        return "%04d-W%02d" % (iy, iw)

    order, last = [], {}
    for it in daily:                 # 오름차순 → 첫 등장 순서가 곧 시간순
        p = period(it["t"])
        if p not in last:
            order.append(p)
        last[p] = it["c"]
    return [{"t": p, "c": last[p]} for p in order][-limit:]


# ─────────────────────────────────────────────
# 지수·환율 일봉 소스
# ─────────────────────────────────────────────
def _foreign_daily(sym: str):
    """다우/나스닥/나스닥100 (api.stock.naver.com foreign chart)"""
    url = ("https://api.stock.naver.com/chart/foreign/index/%s/day"
           "?startDateTime=20180101&endDateTime=20301231&interval=day" % sym)
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as r:
            arr = json.load(r)
    except Exception as e:
        print("[chart foreign 오류] %s: %s" % (sym, e))
        return []
    out = []
    for it in arr:
        d = str(it.get("localDate", ""))
        c = it.get("closePrice")
        if d and c is not None:
            try:
                out.append({"t": d, "c": float(c)})
            except (ValueError, TypeError):
                pass
    out.sort(key=lambda x: x["t"])
    return out


def _usd_daily():
    """미국USD 환율 (marketindex prices, 페이지 병렬)"""
    def one(page):
        url = ("https://api.stock.naver.com/marketindex/exchange/FX_USDKRW/prices"
               "?page=%d&pageSize=60" % page)
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=6) as r:
                return json.load(r)
        except Exception as e:
            print("[chart usd 오류] p%d: %s" % (page, e))
            return []
    out = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        for arr in ex.map(one, range(1, 11)):   # 10페이지 = 약 600영업일
            for it in arr or []:
                d = str(it.get("localTradedAt", "")).replace("-", "")
                c = it.get("closePrice")
                if d and c is not None:
                    try:
                        out.append({"t": d, "c": float(str(c).replace(",", ""))})
                    except (ValueError, TypeError):
                        pass
    out.sort(key=lambda x: x["t"])
    return out


_INDEX_SRC = {"KOSPI": "KOSPI", "KOSDAQ": "KOSDAQ",
              "DJI": ".DJI", "IXIC": ".IXIC", "NDX": ".NDX"}


def _index_daily(key: str):
    if key in ("KOSPI", "KOSDAQ"):
        return _fetch(key, "day", 2500)
    if key == "USD":
        return _usd_daily()
    sym = _INDEX_SRC.get(key)
    return _foreign_daily(sym) if sym else []


# ─────────────────────────────────────────────
# 라우트 (정적 경로를 /{code} 보다 먼저 정의)
# ─────────────────────────────────────────────
@router.get("/index/{key}")
def get_index_chart(key: str, unit: str = "day"):
    """지수·환율 차트 (일/주/월/년). key=KOSPI|KOSDAQ|DJI|IXIC|NDX|USD"""
    if key not in _INDEX_SRC and key != "USD":
        return {"key": key, "unit": unit, "points": []}
    return {"key": key, "unit": unit, "points": _aggregate(_index_daily(key), unit)}


@router.get("/portfolio")
def get_portfolio_chart(group: str = "total", unit: str = "day", db: Session = Depends(get_db)):
    """손익합계 차트 (일/주/월/년). group=total|normal|etf"""
    stocks = db.query(Stock).filter(Stock.is_active == True).all()
    if group == "normal":
        stocks = [s for s in stocks if s.stock_type != "ETF"]
    elif group == "etf":
        stocks = [s for s in stocks if s.stock_type == "ETF"]
    if not stocks:
        return {"group": group, "unit": unit, "points": []}

    codes = list({s.code for s in stocks})

    def fetch_one(code):
        return code, {it["t"]: it["c"] for it in _fetch(code, "day", 2500)}

    series = {}
    with ThreadPoolExecutor(max_workers=min(10, len(codes))) as ex:
        for code, m in ex.map(fetch_one, codes):
            series[code] = m

    total_buy = sum(s.buy_price * s.quantity for s in stocks)
    all_dates = sorted({d for m in series.values() for d in m})
    daily = []
    for d in all_dates:
        val, ok = 0.0, True
        for s in stocks:
            close = series.get(s.code, {}).get(d)
            if close is None:            # 전 종목 데이터가 있는 날만 (겹치는 구간)
                ok = False
                break
            val += close * s.quantity
        if ok:
            daily.append({"t": d, "c": int(val - total_buy)})

    return {"group": group, "unit": unit, "points": _aggregate(daily, unit)}


@router.get("/{code}")
def get_chart(code: str, type: str = "minute", unit: str = "1"):
    """개별종목 차트. type=minute|day, unit=1/3/5/10/20/30 또는 day/week/month/year"""
    if type == "minute":
        data = _fetch(code, "minute", 3000)
        try:
            n = int(unit)
        except ValueError:
            n = 1
        if n > 1 and data:
            data = [data[i] for i in range(n - 1, len(data), n)]
        data = data[-200:]
    else:
        if unit == "year":
            data = _aggregate(_fetch(code, "month", 600), "year")
        elif unit in ("week", "month"):
            data = _fetch(code, unit, 250)[-200:]
        else:
            data = _fetch(code, "day", 250)[-200:]

    return {"code": code, "type": type, "unit": unit, "points": data}
