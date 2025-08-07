from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.schemas import UserCreate, UserLogin, UserOut
from app.auth.models import User
from sqlalchemy.future import select
from app.auth.authentication import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.db.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=user_in.email, hashed_password=hash_password(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login")
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    print(current_user.email)
    return current_user
