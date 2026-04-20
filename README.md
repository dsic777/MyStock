# MyStock — 트레일링 스탑 기반 주식 매도 알리미

키움증권 실계좌와 연동하여 보유종목을 자동 모니터링하고,
트레일링 스탑 기준 도달 시 Claude AI 매도 의견과 함께 알림을 주는 개인용 투자 보조 도구입니다.

---

## 주요 기능

- 키움증권 실계좌 연동 — 보유종목 자동 동기화
- 트레일링 스탑 자동 계산 — 매수일 이후 최고가 기준
- 1분 자동 현재가 갱신
- Claude AI 매도 의견 제공
- **DART 공시 알림 — 보유 종목 공시 발생 시 즉시 알림 (30분 간격 모니터링)**
- 알림 소리 (매도/주의/완료/공시 4종)
- 모바일 접속 지원 (Cloudflare Tunnel + React 반응형 UI)

## 매도 모드

| 모드 | 동작 |
|------|------|
| 알림 | 손절가 도달 시 화면 알림만 표시 — 매도는 사용자가 직접 |
| 확인 | 손절가 도달 시 확인 팝업 + Claude AI 의견 — 버튼 클릭 후 매도 실행 |
| 자동 | 손절가 도달 시 즉시 키움 주문 전송 (무확인) |

> 기본값: **확인** 모드 권장 (실수 방지)

## 기술 스택

| 구분 | 내용 |
|------|------|
| 백엔드 | FastAPI + SQLAlchemy + SQLite |
| 키움 연동 | 32비트 Python + pykiwoom + PyQt5 |
| 프론트엔드 | React (Vite + JSX) |
| 인증 | JWT |
| 외부 접속 | Cloudflare Tunnel |
| AI | Claude Haiku (Anthropic) |
| 공시 | DART 금융감독원 OpenAPI |

## 실행 방법

```
.\start.bat
```

또는 수동:

```powershell
# 터미널 1 — 키움 서버 (32비트)
C:\Python311-32\python.exe c:\MyStock\kiwoom_server\kiwoom_server.py

# 터미널 2 — FastAPI 서버
cd backend
..\myEnv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 환경변수 설정 (.env)

```
SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=your-claude-api-key
DART_API_KEY=your-dart-api-key        # dart.fss.or.kr 에서 발급
KIWOOM_MODE=real                       # mock | real
```

## 주의사항

- 키움 OpenAPI는 Windows 전용 — PC가 항상 켜져 있어야 함
- `.env` 파일은 절대 외부 공개 금지
