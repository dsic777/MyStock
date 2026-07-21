# MyStock 협업 규칙

## ⚠️ 작업·배포 절대 순서 (반드시 준수)

> **로컬 작업 → GitHub push → 서버 배포(git pull)** 순서를 항상 지킨다.
> 부득이 서버에서 먼저 손댔더라도, **최종적으로 로컬·GitHub·서버 3곳의 코드는 반드시 싱크가 일치**해야 한다.

- ❌ 서버에서 직접 수정 후 로컬에 반영 안 함 → 다음 세션에 갈라져서 유실 위험 (실제로 발생했음)
- ✅ 기본 흐름:
  1. 로컬 `c:\Portfolio\mystock`에서 수정
  2. **Claude가 git commit + push** (아래 규칙)
  3. 서버 배포: `ssh ubuntu@150.136.15.246 "cd /home/ubuntu/portfolio/mystock && git pull && docker compose up --build -d mystock-demo"`

## ⚠️ git 커밋/푸시는 항상 Claude가 한다

> **git commit / push 는 사용자에게 묻지 않고 Claude가 항상 직접 수행한다.**
> "커밋할까요?" 확인 금지 — 작업 완료 후 바로 커밋·푸시한다.

- 서버엔 GitHub 인증이 없다 → **push 는 반드시 로컬에서** 한다. (서버는 `git pull` 만)
- 커밋 메시지 끝: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## 프로젝트 구조 (2벌 — 작업 대상 혼동 금지)

- `c:\mystock` = **로컬·실모드** (키움 실계좌). 거의 안 건드림.
- `c:\Portfolio\mystock` = **서버·테스트모드**. 실제 개발 대상. → 브랜치 **`main`**, GitHub `dsic777/MyStock`.
- 배포처: 오라클 서버 `150.136.15.246`, 컨테이너 `mystock-demo`, portfolio-nginx → `https://dspro.duckdns.org/mystock/` (로그인 test/test1234)
- Dockerfile이 프론트 `npm run build`까지 수행 → 프론트 변경도 컨테이너 재빌드 필요.

## 데이터·기능 메모

- **시세**: yfinance 폐기 → **네이버 금융** (`price_fetcher.py`). 코스피/코스닥 코드 자동판별(`.KS/.KQ` 불필요).
- **seed.py**: 실보유 9종목 고정(매입가·전일가 스냅샷). `🔁 초기화`(`/api/demo/reset`)=전체삭제+재생성(매도로 사라진 종목 복구용). run_seed는 데이터 있으면 스킵 → seed 바꾼 뒤엔 화면 초기화 1번 눌러야 반영.
- **증시상황**: `/api/market/indices`(`market.py`, 네이버) → 코스피·코스닥·다우·나스닥·나스닥100 금일/전일/등락. Dashboard `📊 증시상황` 버튼 토글표.
- **알림음**: 미사용(무음).
