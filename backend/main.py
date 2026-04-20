from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from app.core.database import engine, Base
from app.api import accounts, stocks, settings, sell_history, auth, alerts, ai, demo
from seed import run_seed
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_seed()
    yield


app = FastAPI(
    title="MyStock Demo API",
    description="트레일링 스탑 기반 주식 매도 알리미 (데모)",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(accounts.router, prefix="/api")
app.include_router(stocks.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(sell_history.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(demo.router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}


DIST_DIR = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(DIST_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

    @app.get("/{full_path:path}")
    def serve_react(full_path: str):
        if full_path.startswith("api/"):
            return {"error": "not found"}
        file_path = os.path.join(DIST_DIR, full_path)
        if os.path.exists(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
else:
    @app.get("/")
    def root():
        return {"message": "MyStock API 정상 동작 중 (React 빌드 없음 — npm run build 실행 필요)"}
