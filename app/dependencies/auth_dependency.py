"""
app/dependencies/auth_dependency.py

FastAPI dependency that protects routes: extracts the JWT from the
Authorization header, validates it, checks it hasn't been revoked
(logged out), and loads the corresponding Recruiter from the database.

Any route that adds `current_recruiter: Recruiter = Depends(get_current_recruiter)`
to its signature is automatically protected — FastAPI runs this dependency
before the route body executes, and rejects the request with 401 if it fails.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.security import decode_token
from app.db.database import get_db
from app.models.models import Recruiter
from app.models.token_blacklist import TokenBlacklist

# tokenUrl points to the login endpoint — used only so /docs shows the
# "Authorize" button correctly; it doesn't redirect anywhere itself.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_recruiter(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Recruiter:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Reject tokens that were explicitly logged out, even if not yet expired.
    if db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        recruiter_id: str = payload.get("sub")
        if recruiter_id is None:
            raise credentials_exception
        recruiter_id_int = int(recruiter_id)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    recruiter = db.query(Recruiter).filter(Recruiter.id == recruiter_id_int).first()
    if recruiter is None:
        raise credentials_exception
    if not recruiter.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    return recruiter

