from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.auth import get_current_user
from app.core.database import get_db
from app.core.config import ANTHROPIC_API_KEY, DART_API_KEY
from app.models.models import Settings
from app.kiwoom.dart_bridge import get_recent_disclosures

router = APIRouter(prefix="/ai", tags=["AI"])

# 루틴 공시 (투자 판단과 무관) — 필터링 대상
ROUTINE_DISCLOSURES = [
    '사업보고서', '감사보고서', '반기보고서', '분기보고서',
    '주주총회소집공고', '의결권대리행사', '주주총회결과',
    '주요사항보고서(기타)', '기업설명회',
]


class OpinionRequest(BaseModel):
    name: str
    code: str
    stock_type: str
    current_price: int
    stop_price: int
    high_price: int
    buy_price: int
    profit_rate: float
    trailing_rate: float


def fetch_claude_opinion(data: OpinionRequest) -> tuple[str, list, str]:
    """Claude API 호출 — (opinion, key_disclosures, disclosure_summary) 반환"""
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # DART 최근 공시 조회 후 중요 공시만 필터링
    all_disclosures = get_recent_disclosures(DART_API_KEY, data.code, count=10)
    key_disclosures = [
        d for d in all_disclosures
        if not any(r in d['title'] for r in ROUTINE_DISCLOSURES)
    ][:3]  # 최대 3건

    high_drop = round((data.current_price - data.high_price) / data.high_price * 100, 1)
    stop_gap = round((data.current_price - data.stop_price) / data.stop_price * 100, 1)
    if data.current_price <= data.stop_price:
        stop_status = f"⚠️ 이미 손절가 돌파 (손절가 대비 {abs(stop_gap):.1f}% 하락한 상태)"
    else:
        stop_status = f"손절가까지 {stop_gap:.1f}% 여유"

    # 중요 공시 프롬프트 구성
    if key_disclosures:
        disc_lines = "\n".join([f"  - {d['date']} {d['title']}" for d in key_disclosures])
        disc_section = f"\n중요 공시:\n{disc_lines}\n"
        disc_instruction = (
            "\n마지막에 '---' 구분선을 쓰고, "
            "'공시: [공시일자(월.일)를 포함하여 위 중요 공시가 주가에 미치는 의미를 1~2문장으로 요약]'을 추가해주세요."
        )
    else:
        disc_section = ""
        disc_instruction = ""

    prompt = f"""주식 트레일링 스탑 매도 판단 요청입니다. 마크다운 기호(#, **, -, * 등)는 절대 사용하지 말고 일반 텍스트로만 답해주세요.

종목: {data.name} ({data.code}) [{data.stock_type}]
현재가: {data.current_price:,}원
손절가: {data.stop_price:,}원 (고점 대비 {data.trailing_rate}% 기준) — {stop_status}
고점가: {data.high_price:,}원 (현재 고점 대비 {high_drop:.1f}% 수준)
매입가: {data.buy_price:,}원
수익률: {data.profit_rate:+.2f}%{disc_section}
위 데이터와 종목의 업황·시장 상황을 반영하여 매도/보류를 3~4문장으로 솔직하게 판단해 주세요. 손절가를 이미 돌파한 경우 명확히 언급해주세요.{disc_instruction}"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text

    # 공시 요약 파싱
    if "---" in raw and "공시:" in raw:
        parts = raw.split("---", 1)
        opinion = parts[0].strip()
        disclosure_summary = parts[1].replace("공시:", "").strip()
    else:
        opinion = raw.strip()
        disclosure_summary = ""

    return opinion, key_disclosures, disclosure_summary


@router.post("/opinion", dependencies=[Depends(get_current_user)])
def get_ai_opinion(data: OpinionRequest, db: Session = Depends(get_db)):
    """Claude AI 매도 의견 조회"""
    settings = db.query(Settings).first()
    if settings and not settings.claude_ai_enabled:
        return {"opinion": "", "status": "disabled", "disclosures": [], "disclosure_summary": ""}
    if not ANTHROPIC_API_KEY:
        return {"opinion": "", "status": "no_api_key", "disclosures": [], "disclosure_summary": ""}
    try:
        opinion, key_disclosures, disclosure_summary = fetch_claude_opinion(data)
        return {"opinion": opinion, "status": "ok", "disclosures": key_disclosures, "disclosure_summary": disclosure_summary}
    except Exception as e:
        print(f"[AI] Claude 호출 오류: {e}")
        return {"opinion": "", "status": "error", "detail": str(e), "disclosures": [], "disclosure_summary": ""}
