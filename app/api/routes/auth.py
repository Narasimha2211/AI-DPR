# ============================================
# Authentication API Routes
# ============================================

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.services import auth_service
from app.api.dependencies import get_current_user
from config.settings import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/login", response_model=Token)
async def login_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await auth_service.get_user_by_email(email=form_data.username)
    if not user or not auth_service.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.get("is_active"):
        raise HTTPException(status_code=400, detail="Inactive user")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Exclude hashed password from token user dict
    user_out = {k: v for k, v in user.items() if k != "hashed_password"}
    
    return {
        "access_token": auth_service.create_access_token(
            data={"sub": user["email"]}, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "user": user_out
    }

@router.post("/register", response_model=dict)
async def register_user(user_in: UserCreate) -> Any:
    """
    Register a new user (defaults to Viewer role)
    """
    try:
        user = await auth_service.create_user(
            email=user_in.email,
            password=user_in.password,
            name=user_in.name,
            role="Viewer" # Default role
        )
        return {"status": "success", "user": user}
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

@router.get("/me", response_model=dict)
async def read_current_user(current_user: dict = Depends(get_current_user)) -> Any:
    """
    Get current user information
    """
    # Exclude hashed password
    return {k: v for k, v in current_user.items() if k != "hashed_password"}


@router.post("/init-admin", response_model=dict)
@router.get("/init-admin", response_model=dict)
async def init_admin_user() -> Any:
    """
    Initialize/verify admin user exists. Creates if missing.
    """
    try:
        existing = await auth_service.get_user_by_email(email="admin@aidpr.gov.in")
        if existing:
            return {"status": "success", "message": "Admin user already exists"}
        
        user = await auth_service.create_user(
            email="admin@aidpr.gov.in",
            password=settings.ADMIN_PASSWORD,
            name="System Administrator",
            role="Admin"
        )
        return {"status": "success", "message": "Admin user created", "user": user}
    except Exception as e:
        return {"status": "error", "message": str(e)}
