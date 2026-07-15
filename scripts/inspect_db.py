import asyncio
from sqlalchemy import text
from app.db import engine


async def main() -> None:
    async with engine.connect() as c:
        tables = await c.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            )
        )
        print("TABLES:")
        for row in tables:
            print("-", row[0])

        for table in ("users", "conversations", "messages", "documents", "document_chunks", "chunk_embeddings"):
            cols = await c.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = :table
                    ORDER BY ordinal_position
                    """
                ),
                {"table": table},
            )
            names = [r[0] for r in cols]
            print(f"{table}: {names}")


if __name__ == "__main__":
    asyncio.run(main())
