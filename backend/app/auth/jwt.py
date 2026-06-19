import time
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import settings
from app.auth.models import USERS_DB, User
from app.logging_config import get_logger

logger = get_logger(__name__)

SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = time.time() + (ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token map")
        
    user_data = USERS_DB.get(username)
    if user_data is None:
        raise HTTPException(status_code=401, detail="User not tracked")
        
    return User(username=user_data.username, role=user_data.role, email=user_data.email)

def require_role(*roles: str):
    def role_dependency(user: User = Depends(get_current_user)):
        if user.role not in roles and "admin" not in roles:
            if user.role != "admin": # Admin natively inherits all bounds implicitly
                logger.warning("unauthorized_access_attempt", user=user.username, required=roles)
                raise HTTPException(status_code=403, detail="Not enough permissions to interact cleanly.")
        return user
    return role_dependency
