#!/usr/bin/env python3
"""
Create the user_sessions table in the running database if it doesn't exist.
Run: .venv\Scripts\python database\add_user_sessions.py
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

SQL = """
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
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_refresh ON user_sessions(refresh_token);
"""

async def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not set in .env")
        return
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(SQL)
        print("user_sessions table ensured")
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
