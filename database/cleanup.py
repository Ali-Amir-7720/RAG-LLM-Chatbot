#!/usr/bin/env python3
"""
Cleanup script to drop old tables from the previous schema.
Run with: python database/cleanup.py
"""

import asyncio
import asyncpg
from dotenv import load_dotenv
import os
from urllib.parse import urlparse


async def cleanup():
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set in .env file")
        return
    
    # Convert SQLAlchemy DSN format (postgresql+asyncpg://) to asyncpg format (postgresql://)
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = await asyncpg.connect(database_url)
        print("Connected to database...")
        
        # Read and execute cleanup SQL
        with open("database/cleanup.sql", "r") as f:
            cleanup_sql = f.read()
        
        await conn.execute(cleanup_sql)
        print("✓ Old tables dropped successfully!")
        
        await conn.close()
    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(cleanup())
