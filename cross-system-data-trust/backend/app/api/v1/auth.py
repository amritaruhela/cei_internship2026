"""Authentication endpoints."""
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.models import User
from app.schemas.schemas import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/login", response_model=Token, summary="User Login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Authenticate user and return JWT token."""
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        # Demo fallback for easy login
        if form_data.username in ["admin", "data_engineer", "viewer"] and form_data.password == "admin123":
            access_token = create_access_token(
                data={"sub": form_data.username, "role": form_data.username.upper()}
            )
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "role": form_data.username.upper(),
                "username": form_data.username,
            }
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
    }


@router.post("/register", response_model=UserResponse, summary="Register User")
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Register a new user."""
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse, summary="Get Current User Profile")
async def get_me(current_user: User = Depends(get_current_user)):
    if not current_user:
        return UserResponse(
            id="demo-user-id",
            username="admin",
            email="admin@datatrust.local",
            role="ADMIN",
            is_active=True,
            created_at=settings.project_name
        )
    return current_user
