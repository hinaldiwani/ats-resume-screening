import bcrypt
import jwt
import datetime
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import get_db
from backend.models import User

security = HTTPBearer()

def hash_password(password: str) -> str:
    # Ensure bytes and truncate to max 72 bytes for bcrypt safety
    pw_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pw_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pw_bytes, hash_bytes)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    to_encode = data.copy()
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if expires_delta:
        expire = now_utc + expires_delta
    else:
        expire = now_utc + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except Exception:
        raise credentials_exception

    sub = payload.get("sub")
    user_id_claim = payload.get("user_id")
    email_claim = payload.get("email")

    user = None
    # 1. Try resolving by explicit user_id claim
    if user_id_claim is not None:
        try:
            user = db.query(User).filter(User.id == int(user_id_claim)).first()
        except (ValueError, TypeError):
            pass

    # 2. Try resolving by sub (could be integer id string or email)
    if not user and sub is not None:
        sub_str = str(sub).strip()
        if sub_str.isdigit():
            user = db.query(User).filter(User.id == int(sub_str)).first()
        elif "@" in sub_str:
            user = db.query(User).filter(User.email == sub_str.lower()).first()

    # 3. Try resolving by email claim
    if not user and email_claim:
        user = db.query(User).filter(User.email == str(email_claim).lower().strip()).first()

    if user is None:
        raise credentials_exception
    return user

