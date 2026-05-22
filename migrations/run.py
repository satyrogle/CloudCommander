from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg


async def run() -> None:
    dsn = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "Missing TEST_DATABASE_URL or DATABASE_URL environment variable for migrations."
        )

    migrations_dir = Path(__file__).resolve().parent
    migration_files = sorted(migrations_dir.glob("[0-9][0-9][0-9]_*.sql"))
    if not migration_files:
        print("No migration files found.")
        return

    print(f"Connecting to database: {dsn}")
    conn = await asyncpg.connect(dsn)
    try:
        for migration_path in migration_files:
            print(f"Applying {migration_path.name} ...")
            sql = migration_path.read_text(encoding="utf-8")
            await conn.execute(sql)
            print(f"Applied {migration_path.name}")
    finally:
        await conn.close()

    print("All migrations applied successfully.")


if __name__ == "__main__":
    asyncio.run(run())
