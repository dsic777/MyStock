from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, ADMIN_USERNAME, ADMIN_PASSWORD
from app.models.models import User
from app.schemas.schemas import LoginRequest, TokenResponse
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["인증"])

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def create_access_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def ensure_admin_exists(db: Session):
    """앱 최초 실행 시 관리자 계정이 없으면 자동 생성"""
    admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if not admin:
        hashed = pwd_context.hash(ADMIN_PASSWORD)
        db.add(User(username=ADMIN_USERNAME, hashed_password=hashed))
        db.commit()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """JWT 토큰 검증 — 보호된 엔드포인트에서 사용"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰")


def verify_token_str(token: str) -> str:
    """토큰 문자열로 직접 검증 (SSE 쿼리파라미터용)"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰")


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """로그인 → JWT 토큰 발급 + 현재가 1회 갱신"""
    ensure_admin_exists(db)
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 틀렸습니다")
    token = create_access_token(user.username)

    # 로그인 시 현재가 1회 갱신
    try:
        from app.models.models import Stock
        from app.services.price_fetcher import get_current_price
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        for s in stocks:
            price = get_current_price(s.code)
            if price > 0:
                s.current_price = price
                if price > s.high_price:
                    s.high_price = price
        db.commit()
        print(f"[로그인] 현재가 갱신 완료 ({len(stocks)}개 종목)")
    except Exception as e:
        print(f"[로그인] 현재가 갱신 실패: {e}")

    return {"access_token": token, "token_type": "bearer"}
