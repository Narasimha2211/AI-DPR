# ============================================
# Auth Service for RBAC
# Handles passwords, JWT, and user persistence
# PostgreSQL-backed implementation
# ============================================

import datetime
from typing import Optional, Dict
import bcrypt

from jose import jwt, JWTError
from loguru import logger

from config.settings import settings
from config.postgres_config import SessionLocal
from app.models.postgres_models import User

ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    try:
        if not plain_password or not hashed_password:
            return False
        # Bcrypt has a 72-byte limit, truncate if necessary
        truncated_password = plain_password[:72].encode('utf-8')
        # Ensure hashed_password is bytes
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(truncated_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    if not password:
        raise ValueError("Password cannot be empty")
    # Bcrypt has a 72-byte limit, truncate if necessary
    truncated_password = password[:72].encode('utf-8')
    # Use a salt rounds of 12 (secure but still fast)
    hashed = bcrypt.hashpw(truncated_password, bcrypt.gensalt(rounds=12))
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ─── User Database Operations (PostgreSQL) ───

async def get_user_by_email(email: str) -> Optional[Dict]:
    """Get a user by email from PostgreSQL."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return {
                "id": user.id,
                "email": user.email,
                "hashed_password": user.hashed_password,
                "name": user.name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching user by email: {e}")
        return None
    finally:
        db.close()


async def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get a user by ID from PostgreSQL."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return {
                "id": user.id,
                "email": user.email,
                "hashed_password": user.hashed_password,
                "name": user.name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching user by id: {e}")
        return None
    finally:
        db.close()


async def create_user(email: str, password: str, name: str, role: str = "Viewer") -> Dict:
    """Create a new user in PostgreSQL."""
    # Check if user exists
    existing = await get_user_by_email(email)
    if existing:
        raise ValueError("User with this email already exists")

    hashed_password = get_password_hash(password)

    db = SessionLocal()
    try:
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            name=name,
            role=role,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "id": new_user.id,
            "email": new_user.email,
            "name": new_user.name,
            "role": new_user.role,
            "is_active": new_user.is_active,
            "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {e}")
        raise
    finally:
        db.close()
