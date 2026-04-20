from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Account
from app.schemas.schemas import AccountCreate, AccountResponse
from app.api.auth import get_current_user

router = APIRouter(prefix="/accounts", tags=["계좌"], dependencies=[Depends(get_current_user)])


@router.get("/", response_model=list[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    """전체 계좌 목록 조회"""
    return db.query(Account).filter(Account.is_active == True).all()


@router.post("/", response_model=AccountResponse)
def create_account(data: AccountCreate, db: Session = Depends(get_db)):
    """계좌 등록"""
    existing = db.query(Account).filter(Account.account_no == data.account_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="이미 등록된 계좌번호입니다")
    account = Account(**data.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """계좌 비활성화"""
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="계좌를 찾을 수 없습니다")
    account.is_active = False
    db.commit()
    return {"message": "계좌가 비활성화되었습니다"}
