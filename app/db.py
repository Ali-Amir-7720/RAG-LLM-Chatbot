from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


async def check_database() -> dict[str, str]:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                """
                SELECT
                    current_database() AS database_name,
                    current_user AS user_name,
                    EXISTS (
                        SELECT 1
                        FROM pg_extension
                        WHERE extname = 'vector'
                    ) AS vector_enabled
                """
            )
        )
        row = result.mappings().one()

    return {
        "database": str(row["database_name"]),
        "user": str(row["user_name"]),
        "vector_enabled": str(row["vector_enabled"]).lower(),
    }


async def ensure_user_sessions_table() -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    refresh_token TEXT NOT NULL UNIQUE,
                    device VARCHAR(255),
                    ip_address VARCHAR(100),
                    is_revoked BOOLEAN NOT NULL DEFAULT false,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        await connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh ON user_sessions(refresh_token)"
            )
        )


async def close_database() -> None:
    await engine.dispose()