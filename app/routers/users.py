from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db_session
from app.schemas import UserCreate, UserRead
from app.security import hash_password


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db_session),
) -> UserRead:
    query = text(
        """
        INSERT INTO users (username, email, password_hash, profile_picture)
        VALUES (:username, :email, :password_hash, :profile_picture)
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
                "profile_picture": payload.profile_picture,
            },
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that username or email already exists.",
        ) from exc

    return UserRead.model_validate(result.mappings().one())


@router.get("", response_model=list[UserRead])
async def list_users(
    session: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[UserRead]:
    result = await session.execute(
        text(
            """
            SELECT id, username, email, profile_picture, created_at, updated_at
            FROM users
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": limit, "offset": offset},
    )
    return [UserRead.model_validate(row) for row in result.mappings().all()]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> UserRead:
    result = await session.execute(
        text(
            """
            SELECT id, username, email, profile_picture, created_at, updated_at
            FROM users
            WHERE id = :user_id
            """
        ),
        {"user_id": user_id},
    )
    row = result.mappings().one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return UserRead.model_validate(row)
