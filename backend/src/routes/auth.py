from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from src.database import get_sync_session
from src.models.user import User, UserPreferences
from src.services.auth import verify_password, get_password_hash, create_access_token, decode_access_token
from src.core import logger

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[User]:
    """Get current user from JWT token."""
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    with get_sync_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        return user


async def require_auth(user: Optional[User] = Depends(get_current_user)) -> User:
    """Require authentication - raises 401 if not authenticated."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Register a new user."""
    try:
        with get_sync_session() as db:
            existing_user = db.query(User).filter(
                (User.email == request.email) | (User.username == request.username)
            ).first()
            
            if existing_user:
                if existing_user.email == request.email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken"
                    )
            
            user = User(
                id=str(uuid4()),
                email=request.email,
                username=request.username,
                hashed_password=get_password_hash(request.password),
                full_name=request.full_name,
                is_active=True,
                is_verified=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(user)
            db.flush()
            
            preferences = UserPreferences(
                id=str(uuid4()),
                user_id=user.id,
                preferred_categories=[],
                theme="light",
                items_per_page="10",
                email_notifications=True,
                default_search_limit="10",
                default_context_strategy="trimming",
                custom_settings={},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(preferences)
            db.commit()
            db.refresh(user)
            
            access_token = create_access_token(data={"sub": str(user.id)})
            
            logger.info(f"New user registered: {user.email}")
            
            return TokenResponse(
                access_token=access_token,
                user=UserResponse(
                    id=str(user.id),
                    email=user.email,
                    username=user.username,
                    full_name=user.full_name,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    created_at=user.created_at,
                    last_login=user.last_login
                )
            )
            
    except IntegrityError as e:
        logger.error(f"Database integrity error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login user."""
    try:
        with get_sync_session() as db:
            user = db.query(User).filter(User.email == request.email).first()
            
            if not user or not verify_password(request.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password"
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is inactive"
                )
            
            user.last_login = datetime.utcnow()
            db.commit()
            
            access_token = create_access_token(data={"sub": str(user.id)})
            
            logger.info(f"User logged in: {user.email}")
            
            return TokenResponse(
                access_token=access_token,
                user=UserResponse(
                    id=str(user.id),
                    email=user.email,
                    username=user.username,
                    full_name=user.full_name,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    created_at=user.created_at,
                    last_login=user.last_login
                )
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """Get current authenticated user info."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.post("/logout")
async def logout(current_user: User = Depends(require_auth)):
    """Logout user (client should delete token)."""
    logger.info(f"User logged out: {current_user.email}")
    return {"status": "success", "message": "Logged out successfully"}
