from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Settings, Stock
from app.schemas.schemas import SettingsUpdate, SettingsResponse
from app.api.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["설정"], dependencies=[Depends(get_current_user)])


def get_or_create_settings(db: Session) -> Settings:
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """현재 설정값 조회"""
    return get_or_create_settings(db)


@router.put("/", response_model=SettingsResponse)
def update_settings(data: SettingsUpdate, db: Session = Depends(get_db)):
    """
    설정값 변경 + 전체 종목 손절가 즉시 재계산
    - 트레일링 비율 변경 시 개별 설정이 없는 종목들에 새 기준가 자동 반영
    """
    settings = get_or_create_settings(db)

    # 변경된 값만 업데이트
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)

    # 트레일링 비율이 변경된 경우 → high_price 재계산은 필요 없음
    # (stop_price는 조회 시점에 실시간 계산되므로 자동 반영)
    # 단, 개별 trailing_rate가 없는 종목들은 다음 조회 때 새 비율 적용됨

    return settings
