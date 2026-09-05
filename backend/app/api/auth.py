import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

def hash_password(password: str, salt: str) -> str:
    return hashlib.scrypt(
        password.encode(),
        salt=bytes.fromhex(salt),
        n=2**14,
        r=8,
        p=1,
    ).hex()

@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    org = Organization(name=payload.organization_name)
    db.add(org)
    await db.flush()

    salt = secrets.token_hex(16)
    user = User(
        organization_id=org.id,
        email=payload.email,
        role="admin",
        password_hash=hash_password(payload.password if hasattr(payload, "password") else "temporary", salt),
        password_salt=salt,
    )
    db.add(user)
    await db.commit()

    token = create_access_token(str(user.id), str(org.id), user.role)
    return TokenResponse(access_token=token)

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == payload.email))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if hash_password(payload.password, user.password_salt) != user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        str(user.id), str(user.organization_id), user.role
    )
    return TokenResponse(access_token=token)
