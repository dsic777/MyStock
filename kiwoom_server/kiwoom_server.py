"""
키움 OpenAPI 전용 서버 (32비트 Python으로 실행)
캐시 방식: 데이터를 미리 가져와 메모리에 저장, HTTP는 캐시 반환

실행방법: C:\Python311-32\python.exe kiwoom_server.py
"""
import sys
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from pykiwoom.kiwoom import Kiwoom
    KIWOOM_AVAILABLE = True
except Exception as e:
    print(f"[경고] pykiwoom 로드 실패: {e}")
    KIWOOM_AVAILABLE = False

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# ─────────────────────────────────────────────
# 캐시 저장소
# ─────────────────────────────────────────────
cache = {
    "accounts": [],
    "holdings": {},   # { account_no: [종목목록] }
    "prices": {},     # { code: price }
    "logged_in": False
}

kiwoom = None
app_qt = None


# ─────────────────────────────────────────────
# 키움 API 함수 (Qt 메인 스레드에서 실행)
# ─────────────────────────────────────────────

def fetch_accounts():
    """계좌 목록 조회 및 캐시 저장"""
    global cache
    if not kiwoom:
        return
    accounts = kiwoom.GetLoginInfo("ACCNO")
    if isinstance(accounts, str):
        cache["accounts"] = [a.strip() for a in accounts.split(';') if a.strip()]
    elif isinstance(accounts, list):
        cache["accounts"] = [a.strip() for a in accounts if a.strip()]
    print(f"[키움] 계좌 조회 완료: {cache['accounts']}")


def fetch_holdings(account_no):
    """보유종목 조회 및 캐시 저장 (OPW00018)"""
    global cache
    if not kiwoom:
        return
    try:
        print(f"[키움] 보유종목 조회 중: {account_no}")
        df = kiwoom.block_request(
            "OPW00018",
            계좌번호=account_no,
            비밀번호="",
            비밀번호입력매체구분="00",
            조회구분="1",
            output="잔고",
            next=0
        )
        if df is None or len(df) == 0:
            cache["holdings"][account_no] = []
            print(f"[키움] {account_no} 보유종목 없음")
            return

        def clean(val):
            v = str(val).replace(',','').replace('+','').replace(' ','').strip()
            negative = v.startswith('-')
            v = v.replace('-','')
            result = int(v) if v.isdigit() else 0
            return -result if negative else result

        result = []
        for _, row in df.iterrows():
            name = str(row.get('종목명', '')).strip()
            if not name or name == '0':
                continue
            code = str(row.get('종목번호', row.get('종목코드', ''))).strip().lstrip('A')
            result.append({
                "code": code,
                "name": name,
                "quantity": clean(row.get('보유수량', 0)),
                "buy_price": clean(row.get('매입가', 0)),
                "current_price": clean(row.get('현재가', 0)),
                "eval_amount": clean(row.get('평가금액', 0)),
                "profit_loss": clean(row.get('평가손익', 0)),
            })

        cache["holdings"][account_no] = result
        # 보유종목 현재가를 prices 캐시에도 저장
        for item in result:
            if item["code"] and item["current_price"] > 0:
                cache["prices"][item["code"]] = item["current_price"]
                print(f"[현재가] {item['name']}({item['code']}) = {item['current_price']:,}원")
            elif item["code"]:
                print(f"[현재가0] {item['name']}({item['code']}) = 0 ← OPW00018이 0 반환")
        print(f"[키움] {account_no} 보유종목 {len(result)}개 조회 완료")

    except Exception as e:
        import traceback
        print(f"[오류] 보유종목 조회 실패 ({account_no}): {e}")
        print(traceback.format_exc())
        cache["holdings"][account_no] = []


def fetch_price(code):
    """현재가 조회 및 캐시 저장"""
    global cache
    if not kiwoom:
        return
    try:
        df = kiwoom.block_request(
            "opt10001",
            종목코드=code,
            output="주식기본정보",
            next=0
        )
        price_str = str(df['현재가'].iloc[0]).replace(',','').replace('+','').replace('-','')
        cache["prices"][code] = abs(int(price_str))
    except Exception as e:
        print(f"[경고] 현재가 조회 실패 ({code}): {e}")


def fetch_high_price_since_buy(code, avg_buy_price):
    """
    평균 매입가 기준으로 추정 매수일을 찾고,
    그 날짜부터 오늘까지의 최고 고가를 반환
    - 일봉 역순 정렬 → 평균 매입가와 가장 근접한 종가 날짜 = 추정 매수일
    """
    if not kiwoom:
        return 0
    try:
        from datetime import datetime
        today = datetime.now().strftime("%Y%m%d")
        df = kiwoom.block_request(
            "opt10086",
            종목코드=code,
            기준일자=today,
            수정주가구분="1",
            output="주식일봉차트조회",
            next=0
        )
        if df is None or len(df) == 0:
            return 0

        def clean(val):
            v = str(val).replace(',','').replace('+','').replace(' ','').strip()
            v = v.lstrip('-')
            return int(v) if v.isdigit() else 0

        # 날짜 역순(최신→과거) 정렬
        df = df.sort_values('일자', ascending=False).reset_index(drop=True)

        # 평균 매입가와 가장 근접한 종가 날짜 찾기 (역순이므로 가장 최근 날짜)
        buy_idx = 0
        min_diff = float('inf')
        for i, row in df.iterrows():
            close = clean(row.get('현재가', row.get('종가', 0)))
            if close <= 0:
                continue
            diff = abs(close - avg_buy_price)
            if diff < min_diff:
                min_diff = diff
                buy_idx = i

        # 추정 매수일 이후 데이터만 (인덱스 0 ~ buy_idx)
        subset = df.iloc[:buy_idx + 1]
        high = 0
        for _, row in subset.iterrows():
            c = clean(row.get('현재가', row.get('종가', 0)))
            if c > high:
                high = c

        buy_date = df.iloc[buy_idx]['일자'] if len(df) > buy_idx else '?'
        print(f"[고점가] {code} 추정매수일={buy_date} 고점가={high:,}")
        return high

    except Exception as e:
        print(f"[경고] 고점가 조회 실패 ({code}): {e}")
        return 0


def refresh_all():
    """전체 데이터 갱신 (1분마다 자동 실행) — OPW00018 현재가 사용"""
    print("[키움] 데이터 갱신 중...")
    fetch_accounts()
    for account_no in cache["accounts"]:
        fetch_holdings(account_no)  # OPW00018 현재가가 prices 캐시에 저장됨
    print("[키움] 데이터 갱신 완료")


# 조회 시작 플래그
do_fetch = False


def on_login_complete():
    """로그인 완료 후 계좌 비밀번호 등록창 띄우기"""
    global do_fetch
    cache["logged_in"] = True

    print("[키움] ★★★ 계좌 비밀번호 등록창이 뜹니다 ★★★")
    print("[키움] 전체계좌에 등록 → 닫기 하시면 자동으로 조회됩니다!")
    kiwoom.ocx.dynamicCall("KOA_Functions(QString, QString)", ["ShowAccountWindow", ""])

    # ShowAccountWindow 닫힌 후 자동으로 조회 시작 (3초 후)
    QTimer.singleShot(3000, start_fetch)


refresh_timer = None  # 전역 유지 (가비지컬렉션 방지)


def start_fetch():
    """Qt 메인 스레드에서 보유종목 조회 (비밀번호 등록 후 실행)"""
    global refresh_timer
    print("[키움] 보유종목 조회 시작...")
    fetch_accounts()
    print(f"[키움] 조회할 계좌: {cache['accounts']}")
    for account_no in cache["accounts"]:
        fetch_holdings(account_no)
    print("[키움] ★ 초기 데이터 로드 완료! ★")

    # 1분마다 자동 갱신 (전역 참조로 GC 방지)
    refresh_timer = QTimer()
    refresh_timer.timeout.connect(refresh_all)
    refresh_timer.start(30000)  # 30초


# ─────────────────────────────────────────────
# HTTP 서버 (캐시 데이터 반환)
# ─────────────────────────────────────────────

class KiwoomHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            if self.path == '/sell':
                content_length = int(self.headers.get('Content-Length', 0))
                body = json.loads(self.rfile.read(content_length).decode('utf-8'))
                account_no = body.get("account_no", "")
                code = body.get("code", "")
                quantity = int(body.get("quantity", 0))

                if not kiwoom or not KIWOOM_AVAILABLE:
                    print(f"[키움] Mock 매도: {code} {quantity}주")
                    self.send_json({"success": True, "message": f"Mock 매도 완료: {code} {quantity}주"})
                    return

                import threading
                result_event = threading.Event()
                result_holder = {}

                def do_sell():
                    try:
                        ret = kiwoom.SendOrder(
                            "시장가매도", "0101", account_no, 2, code, quantity, 0, "03", ""
                        )
                        result_holder["result"] = {"success": True, "message": f"매도 주문 전송 (ret={ret})"}
                        print(f"[키움] 매도 주문: {code} {quantity}주 계좌={account_no} ret={ret}")
                    except Exception as e:
                        result_holder["result"] = {"success": False, "error": str(e)}
                        print(f"[키움] 매도 오류: {e}")
                    finally:
                        result_event.set()

                QTimer.singleShot(0, do_sell)
                result_event.wait(timeout=10)

                if result_holder.get("result"):
                    self.send_json(result_holder["result"])
                else:
                    self.send_json({"success": False, "error": "타임아웃"}, 500)
            else:
                self.send_json({"error": "not found"}, 404)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def do_GET(self):
        try:
            if self.path == '/status':
                self.send_json({
                    "status": "ok",
                    "kiwoom_available": KIWOOM_AVAILABLE,
                    "logged_in": cache["logged_in"],
                    "accounts": cache["accounts"]
                })

            elif self.path == '/accounts':
                self.send_json({"accounts": cache["accounts"]})

            elif self.path.startswith('/holdings/'):
                account_no = self.path.split('/')[-1]
                holdings = cache["holdings"].get(account_no, [])
                self.send_json({"holdings": holdings})

            elif self.path.startswith('/price/'):
                code = self.path.split('/')[-1]
                price = cache["prices"].get(code, 0)
                self.send_json({"code": code, "price": price})

            elif self.path.startswith('/high_price/'):
                # /high_price/{code}/{avg_buy_price}
                parts = self.path.split('/')
                code = parts[2] if len(parts) > 2 else ''
                avg_buy_price = int(parts[3]) if len(parts) > 3 else 0
                high = fetch_high_price_since_buy(code, avg_buy_price)
                self.send_json({"code": code, "high_price": high})

            elif self.path == '/refresh':
                # 수동 갱신 트리거 (캐시만 반환하고 실제 갱신은 Qt에서)
                self.send_json({"message": "갱신 요청됨 (10초 후 완료)"})

            else:
                self.send_json({"error": "not found"}, 404)

        except Exception as e:
            self.send_json({"error": str(e)}, 500)


def run_http_server():
    server = HTTPServer(('127.0.0.1', 9000), KiwoomHandler)
    print("[키움서버] HTTP 서버 시작: http://127.0.0.1:9000")
    server.serve_forever()


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

if __name__ == '__main__':
    print("[키움서버] 시작 중...")

    app_qt = QApplication(sys.argv)

    if not KIWOOM_AVAILABLE:
        print("[키움서버] Mock 모드 (pykiwoom 없음)")
        t = threading.Thread(target=run_http_server, daemon=True)
        t.start()
        app_qt.exec_()
    else:
        kiwoom = Kiwoom()
        kiwoom.CommConnect(block=True)
        print("[키움] 로그인 완료")

        # HTTP 서버 별도 스레드
        t = threading.Thread(target=run_http_server, daemon=True)
        t.start()

        # 로그인 후 초기 데이터 로드 (Qt 이벤트 루프 시작 후 실행)
        QTimer.singleShot(1000, on_login_complete)

        print("[키움서버] 준비 완료! 잠시 후 보유종목 자동 로드됩니다...")
        sys.exit(app_qt.exec_())
