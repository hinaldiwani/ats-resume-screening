"""
app/api/v1/endpoints/auth.py

Authentication routes: register, login, refresh, logout, and a protected
"me" endpoint used to prove protected-route access works.

All routes return the standard JSON envelope:
    { "success": bool, "data": {...} | null, "message": str }

Endpoints themselves stay thin — they validate input via Pydantic schemas,
delegate to app/services/auth_service.py, and shape the response. No DB
queries or password/JWT logic live directly in this file.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.dependencies.auth_dependency import get_current_recruiter, oauth2_scheme
from app.models.models import Recruiter
from app.schemas.schemas import (
    RecruiterRegisterRequest,
    RecruiterResponse,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    LogoutRequest,
    APIResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RecruiterRegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new recruiter account.

    - Validates the request body against RecruiterRegisterRequest (email format,
      password length, etc. — enforced automatically by Pydantic before this
      function body even runs).
    - Rejects duplicate emails with 409 Conflict (handled in auth_service).
    - Hashes the password with bcrypt before storage — plaintext passwords
      are never written to the database.
    - Returns the created recruiter's public fields (never the password hash).
    """
    recruiter = auth_service.register_recruiter(db, payload)
    return APIResponse(
        success=True,
        data=RecruiterResponse.model_validate(recruiter).model_dump(mode="json"),
        message="Recruiter registered successfully.",
    )


@router.post("/login", response_model=APIResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates a recruiter by email + password and issues a JWT token pair.

    - Verifies the submitted password against the stored bcrypt hash.
    - On success, issues a short-lived access token (used on every request)
      and a longer-lived refresh token (used only to mint new access tokens).
    - Returns 401 for any invalid credentials, deliberately without
      distinguishing "wrong password" from "no such account".
    """
    recruiter = auth_service.authenticate_recruiter(db, payload)
    tokens = auth_service.issue_tokens(recruiter)
    return APIResponse(success=True, data=tokens, message="Login successful.")


@router.post("/refresh", response_model=APIResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchanges a valid, unexpired refresh token for a new access token.

    - Lets the frontend keep a user "logged in" without re-entering a
      password every hour (ACCESS_TOKEN_EXPIRE_MINUTES), while the longer-lived
      refresh token is the only credential stored for an extended session.
    - Rejects access tokens submitted here (checked via the `type` claim) —
      a refresh token is a distinct credential, not interchangeable with
      an access token.
    """
    result = auth_service.refresh_access_token(db, payload.refresh_token)
    return APIResponse(success=True, data=result, message="Access token refreshed.")


@router.post("/logout", response_model=APIResponse)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    """
    Logs out a recruiter by revoking their access token.

    JWTs are stateless and normally can't be "cancelled" — this endpoint
    records the submitted token in a blacklist table, and get_current_recruiter
    checks that table on every protected request, so a revoked token is
    rejected immediately rather than remaining valid until it naturally expires.
    """
    auth_service.logout_recruiter(db, payload.access_token)
    return APIResponse(success=True, data=None, message="Logged out successfully.")


@router.get("/me", response_model=APIResponse)
def get_me(current_recruiter: Recruiter = Depends(get_current_recruiter)):
    """
    Protected route — returns the currently authenticated recruiter's profile.

    Demonstrates route protection: `Depends(get_current_recruiter)` runs
    before this function body. It extracts the Bearer token from the
    Authorization header, validates its signature and expiry, checks it
    isn't blacklisted (logged out), and loads the matching Recruiter row.
    Any failure short-circuits with 401 before this line ever executes.
    """
    return APIResponse(
        success=True,
        data=RecruiterResponse.model_validate(current_recruiter).model_dump(mode="json"),
        message="Current recruiter profile.",
    )
