from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))

# JWT 설정
SECRET_KEY = os.getenv("SECRET_KEY", "mystock-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

# Claude AI
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 관리자 계정 초기값
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "test")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Dst@7Kw!9m")

# 키움 API 모드
KIWOOM_MODE = os.getenv("KIWOOM_MODE", "mock")  # "mock" or "real"

# DART 공시 API
DART_API_KEY = os.getenv("DART_API_KEY", "")
