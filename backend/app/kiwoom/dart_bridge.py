"""
DART(금융감독원 전자공시) API 브리지
OpenDartReader 라이브러리 사용 — stock_code 직접 조회 가능
"""
from datetime import datetime, timedelta

_dart = None


def _get_dart(api_key: str):
    global _dart
    if _dart is None:
        import OpenDartReader
        print("[DART] OpenDartReader 초기화 중...")
        _dart = OpenDartReader(api_key)
        print("[DART] OpenDartReader 준비 완료")
    return _dart


def get_recent_disclosures(api_key: str, stock_code: str, count: int = 5) -> list:
    """최근 공시 목록 조회 (최근 90일, count건)"""
    if not api_key:
        return []
    try:
        dart = _get_dart(api_key)
        start = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        df = dart.list(stock_code, start=start)
        if df is None or len(df) == 0:
            print(f"[DART] {stock_code} 최근 90일 공시 없음")
            return []
        result = []
        for _, row in df.head(count).iterrows():
            dt = str(row.get("rcept_dt", ""))
            formatted_date = f"{dt[:4]}-{dt[4:6]}-{dt[6:]}" if len(dt) == 8 else dt
            result.append({
                "date": formatted_date,
                "title": str(row.get("report_nm", "")).strip(),
                "rcept_no": str(row.get("rcept_no", "")),
            })
        print(f"[DART] {stock_code} 공시 {len(result)}건 조회 완료")
        for d in result:
            print(f"  - {d['date']} {d['title']}")
        return result
    except Exception as e:
        print(f"[DART] 조회 오류: {e}")
        return []
