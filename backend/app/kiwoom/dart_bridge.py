"""
DART(금융감독원 전자공시) 공시 조회 — API 직접 호출(urllib)
- OpenDartReader 폐기: 초기화 시 CORPCODE 전체(약 3.6MB) 다운로드가 오라클 서버 IP에서
  255초나 걸려 매도판단이 타임아웃/실패하던 원인이었음(로컬은 0.4초 → 서버 IP 스로틀).
- 보유 종목은 고정이라 stock_code→corp_code 매핑을 상수로 두고 list.json 을 직접 호출.
- 타임아웃(8초) — 느리거나 실패하면 공시 없이 진행(매도판단 자체는 Claude가 수행).
"""
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
_TIMEOUT = 8  # 초

# 보유 종목 stock_code → DART corp_code (2026-07-22 CORPCODE 추출)
# ETF(133690 TIGER나스닥100)는 기업공시가 없어 매핑 제외 → 공시 없음 처리
STOCK_TO_CORP = {
    "000660": "00164779",  # SK하이닉스
    "005490": "00155319",  # POSCO홀딩스
    "005930": "00126380",  # 삼성전자
    "034020": "00159616",  # 두산에너빌리티
    "042700": "00161383",  # 한미반도체
    "058470": "00369657",  # 리노공업
    "086520": "00536541",  # 에코프로
    "196170": "00989619",  # 알테오젠
}


def get_recent_disclosures(api_key: str, stock_code: str, count: int = 5) -> list:
    """최근 공시 목록 조회 (최근 60일, count건). DART list.json 직접 호출."""
    if not api_key:
        return []
    corp_code = STOCK_TO_CORP.get(stock_code)
    if not corp_code:
        return []  # 매핑 없는 종목(ETF 등)

    bgn_de = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
    q = urllib.parse.urlencode({
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "page_count": count,
    })
    try:
        with urllib.request.urlopen(_LIST_URL + "?" + q, timeout=_TIMEOUT) as r:
            d = json.load(r)
        if d.get("status") != "000":
            print(f"[DART] {stock_code} status={d.get('status')} {d.get('message')}")
            return []
        result = []
        for it in d.get("list", [])[:count]:
            dt = str(it.get("rcept_dt", "")).strip()
            formatted_date = f"{dt[:4]}-{dt[4:6]}-{dt[6:]}" if len(dt) == 8 else dt
            result.append({
                "date": formatted_date,
                "title": str(it.get("report_nm", "")).strip(),
                "rcept_no": str(it.get("rcept_no", "")).strip(),
            })
        print(f"[DART] {stock_code} 공시 {len(result)}건 조회 완료")
        return result
    except Exception as e:
        print(f"[DART] 조회 오류: {e}")
        return []
