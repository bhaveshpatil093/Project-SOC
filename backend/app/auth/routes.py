from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.models import USERS_DB, verify_password, User
from app.auth.jwt import create_access_token, get_current_user
from app.logging_config import get_logger
from fastapi import Request
from app.middleware.rate_limiter import limiter

logger = get_logger(__name__)

router = APIRouter()

@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user_data = USERS_DB.get(form_data.username)
    if not user_data or not verify_password(form_data.password, user_data.hashed_password):
        logger.warning("auth_failed", username=form_data.username, reason="invalid_credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user_data.username, "role": user_data.role})
    logger.info("auth_success", username=form_data.username, role=user_data.role)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": user_data.username,
            "role": user_data.role,
            "email": user_data.email
        }
    }

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
async def logout():
    return {"status": "ok", "message": "Successfully logged out client side"}
