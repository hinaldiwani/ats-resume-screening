"""
app/services/auth_service.py

Business logic for authentication. Routes in app/api/v1/endpoints/auth.py
call these functions rather than touching the DB or security primitives
directly — keeps endpoints thin and this logic independently testable.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    JWTError,
)
from app.models.models import Recruiter
from app.models.token_blacklist import TokenBlacklist
from app.schemas.schemas import RecruiterRegisterRequest, LoginRequest


def register_recruiter(db: Session, payload: RecruiterRegisterRequest) -> Recruiter:
    """
    Creates a new Recruiter account. Raises 409 if the email is already
    registered. Password is hashed before it ever touches the database.
    """
    existing = db.query(Recruiter).filter(Recruiter.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    recruiter = Recruiter(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        company_name=payload.company_name,
    )
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)
    return recruiter


def authenticate_recruiter(db: Session, payload: LoginRequest) -> Recruiter:
    """
    Verifies email + password. Raises 401 on any mismatch — deliberately
    the same error for "no such email" and "wrong password" so the API
    doesn't leak which emails are registered.
    """
    recruiter = db.query(Recruiter).filter(Recruiter.email == payload.email).first()
    if not recruiter or not verify_password(payload.password, recruiter.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not recruiter.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive.")
    return recruiter


def issue_tokens(recruiter: Recruiter) -> dict:
    """Generates a fresh access + refresh token pair for a recruiter."""
    return {
        "access_token": create_access_token(subject=recruiter.id),
        "refresh_token": create_refresh_token(subject=recruiter.id),
        "token_type": "bearer",
    }


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    """
    Validates a refresh token and issues a new access token. Refresh tokens
    are never accepted where an access token is expected (checked via the
    `type` claim), and vice versa.
    """
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
        recruiter_id = payload.get("sub")
        if recruiter_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
        recruiter_id_int = int(recruiter_id)
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

    recruiter = db.query(Recruiter).filter(Recruiter.id == recruiter_id_int).first()
    if not recruiter or not recruiter.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Recruiter not found or inactive.")

    return {"access_token": create_access_token(subject=recruiter.id), "token_type": "bearer"}



def logout_recruiter(db: Session, access_token: str) -> None:
    """
    Revokes an access token by recording it in the blacklist table.
    Idempotent: logging out an already-blacklisted token is a no-op, not an error.
    """
    already_revoked = db.query(TokenBlacklist).filter(TokenBlacklist.token == access_token).first()
    if already_revoked:
        return
    db.add(TokenBlacklist(token=access_token))
    db.commit()
