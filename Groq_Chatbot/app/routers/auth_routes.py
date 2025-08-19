from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.authentication import get_current_user
from jose import jwt, JWTError
import uuid
from app.auth.schemas import UserCreate, UserLogin, UserOut
from app.auth.models import User
from app.auth.authentication import (
    hash_password,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)
from app.db.dependencies import get_db
from app.services.email import send_verification_email  # Gmail sender

router = APIRouter()


# ------------------------
# Register new user
# ------------------------
@router.post("/register", response_model=UserOut)
async def register(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create unverified user
    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create a short-lived verification token (1 hour)
    token = create_access_token(
        {"sub": str(user.id), "purpose": "verify"},
        expires_delta=timedelta(hours=1),
    )

    # Send email in background (non-blocking)
    background_tasks.add_task(send_verification_email, user.email, token)

    return user
    # return {"msg": "User registered. Please verify your email."}


# ------------------------
# Verify email
# ------------------------
@router.get("/verify")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        purpose: str = payload.get("purpose")
        if user_id is None or purpose != "verify":
            raise HTTPException(status_code=400, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Fetch user
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        return {"msg": "Email already verified"}

    # Mark user as verified
    user.is_verified = True
    db.add(user)
    await db.commit()

    return {"msg": "Email verified successfully"}


# ------------------------
# Login
# ------------------------
@router.post("/login")
async def login(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    user = result.scalars().first()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    print(current_user.email)
    return current_user
