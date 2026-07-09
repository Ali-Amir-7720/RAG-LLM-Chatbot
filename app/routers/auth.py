from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db_session
from app.schemas import (
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthResponse,
    AuthSignupRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenPair,
    UserRead,
)
from app.security import create_access_token, generate_refresh_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


async def _issue_session_tokens(
    *,
    session: AsyncSession,
    user: UserRead,
    request: Request,
    device: str | None,
) -> TokenPair:
    settings = get_settings()
    refresh_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_ttl_days)
    ip = request.client.host if request.client else None

    await session.execute(
        text(
            """
            INSERT INTO user_sessions (user_id, refresh_token, device, ip_address, expires_at)
            VALUES (:user_id, :refresh_token, :device, :ip_address, :expires_at)
            """
        ),
        {
            "user_id": user.id,
            "refresh_token": refresh_token,
            "device": device,
            "ip_address": ip,
            "expires_at": expires_at,
        },
    )
    await session.commit()

    access_token = create_access_token(user_id=user.id)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: AuthSignupRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    query = text(
        """
        INSERT INTO users (username, email, password_hash)
        VALUES (:username, :email, :password_hash)
        RETURNING id, username, email, profile_picture, created_at, updated_at
        """
    )

    try:
        result = await session.execute(
            query,
            {
                "username": payload.username,
                "email": payload.email,
                "password_hash": hash_password(payload.password),
            },
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that username or email already exists.",
        ) from exc

    user = UserRead.model_validate(result.mappings().one())
    tokens = await _issue_session_tokens(session=session, user=user, request=request, device=None)
    return AuthResponse(user=user, tokens=tokens)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: AuthLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    result = await session.execute(
        text(
            """
            SELECT id, username, email, profile_picture, password_hash, created_at, updated_at
            FROM users
            WHERE LOWER(email) = LOWER(:email)
            """
        ),
        {"email": payload.email},
    )
    row = result.mappings().one_or_none()
    if row is None or not verify_password(payload.password, str(row["password_hash"])):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    user = UserRead.model_validate(
        {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "profile_picture": row["profile_picture"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    )

    tokens = await _issue_session_tokens(session=session, user=user, request=request, device=payload.device)
    return AuthResponse(user=user, tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: AuthRefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPair:
    settings = get_settings()
    now = datetime.now(timezone.utc)

    result = await session.execute(
        text(
            """
            SELECT id, user_id, is_revoked, expires_at
            FROM user_sessions
            WHERE refresh_token = :refresh_token
            """
        ),
        {"refresh_token": payload.refresh_token},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    if bool(row["is_revoked"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked.")
    if row["expires_at"] <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")

    # Rotate refresh token (simple rotation: update in-place).
    new_refresh = generate_refresh_token()
    new_expires_at = now + timedelta(days=settings.refresh_token_ttl_days)
    ip = request.client.host if request.client else None

    await session.execute(
        text(
            """
            UPDATE user_sessions
            SET refresh_token = :new_refresh_token,
                expires_at = :new_expires_at,
                ip_address = COALESCE(:ip_address, ip_address)
            WHERE id = :session_id
            """
        ),
        {
            "new_refresh_token": new_refresh,
            "new_expires_at": new_expires_at,
            "ip_address": ip,
            "session_id": row["id"],
        },
    )
    await session.commit()

    access = create_access_token(user_id=row["user_id"])
    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.post("/logout")
async def logout(
    payload: AuthLogoutRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    await session.execute(
        text(
            """
            UPDATE user_sessions
            SET is_revoked = true
            WHERE refresh_token = :refresh_token
            """
        ),
        {"refresh_token": payload.refresh_token},
    )
    await session.commit()
    return {"status": "ok"}


@router.post("/logout_all")
async def logout_all(
    payload: AuthLogoutRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    # Resolve user_id from refresh token, then revoke all sessions for that user.
    result = await session.execute(
        text(
            """
            SELECT user_id
            FROM user_sessions
            WHERE refresh_token = :refresh_token
            """
        ),
        {"refresh_token": payload.refresh_token},
    )
    row = result.mappings().one_or_none()
    if row is None:
        # Idempotent: treat unknown token as already logged out.
        return {"status": "ok"}

    await session.execute(
        text(
            """
            UPDATE user_sessions
            SET is_revoked = true
            WHERE user_id = :user_id
            """
        ),
        {"user_id": row["user_id"]},
    )
    await session.commit()
    return {"status": "ok"}


@router.post("/password-reset/request")
async def request_password_reset(
    payload: PasswordResetRequest,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    # Look up user by lowercase email
    result = await session.execute(
        text("SELECT id FROM users WHERE LOWER(email) = LOWER(:email)"),
        {"email": payload.email},
    )
    row = result.mappings().one_or_none()
    
    if row is not None:
        user_id = row["id"]
        # Generate raw secure token
        token = secrets.token_urlsafe(32)
        # Store only the SHA-256 hash of the token
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        await session.execute(
            text(
                """
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                VALUES (:user_id, :token_hash, :expires_at)
                """
            ),
            {"user_id": user_id, "token_hash": token_hash, "expires_at": expires_at},
        )
        await session.commit()
        
        # Log/Print token link for local developer visibility
        print(f"--- PASSWORD RESET TOKEN CREATED FOR {payload.email} ---")
        print(f"Link: http://localhost:8000/api/v1/auth/password-reset/confirm?token={token}")
        print("---------------------------------------------------------")
        
    # Return generic success response regardless of email existence to prevent user enumeration
    return {"status": "ok"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    # Hash the submitted token
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    
    # Query token details
    result = await session.execute(
        text(
            """
            SELECT id, user_id, expires_at, is_used
            FROM password_reset_tokens
            WHERE token_hash = :token_hash
            """
        ),
        {"token_hash": token_hash},
    )
    row = result.mappings().one_or_none()
    
    if row is None or bool(row["is_used"]) or row["expires_at"] <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is invalid, expired, or already used."
        )
        
    user_id = row["user_id"]
    token_id = row["id"]
    
    # 1. Update the user's password_hash
    await session.execute(
        text(
            """
            UPDATE users
            SET password_hash = :password_hash,
                updated_at = now()
            WHERE id = :user_id
            """
        ),
        {"user_id": user_id, "password_hash": hash_password(payload.new_password)},
    )
    
    # 2. Mark the token as used
    await session.execute(
        text(
            """
            UPDATE password_reset_tokens
            SET is_used = true
            WHERE id = :token_id
            """
        ),
        {"token_id": token_id},
    )
    
    # 3. Revoke all existing sessions for the user to force re-login
    await session.execute(
        text(
            """
            UPDATE user_sessions
            SET is_revoked = true
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    
    await session.commit()
    return {"status": "ok"}


