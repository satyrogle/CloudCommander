from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path

import asyncpg


MIGRATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


def migration_checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


async def apply_migrations(conn: asyncpg.Connection, migrations_dir: Path) -> list[str]:
    await conn.execute(MIGRATIONS_TABLE_SQL)
    applied: list[str] = []

    migration_files = sorted(migrations_dir.glob("[0-9][0-9][0-9]_*.sql"))
    for migration_path in migration_files:
        sql = migration_path.read_text(encoding="utf-8")
        checksum = migration_checksum(sql)
        existing = await conn.fetchrow(
            "SELECT checksum FROM schema_migrations WHERE filename = $1",
            migration_path.name,
        )

        if existing is not None:
            if existing["checksum"] != checksum:
                raise RuntimeError(
                    f"Migration {migration_path.name} was already applied with a different checksum."
                )
            print(f"Skipping {migration_path.name}; already applied.")
            continue

        print(f"Applying {migration_path.name} ...")
        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute(
                """
                INSERT INTO schema_migrations (filename, checksum)
                VALUES ($1, $2)
                """,
                migration_path.name,
                checksum,
            )
        print(f"Applied {migration_path.name}")
        applied.append(migration_path.name)

    return applied


async def run() -> None:
    dsn = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "Missing TEST_DATABASE_URL or DATABASE_URL environment variable for migrations."
        )

    migrations_dir = Path(__file__).resolve().parent
    print(f"Connecting to database: {dsn}")
    conn = await asyncpg.connect(dsn)
    try:
        applied = await apply_migrations(conn, migrations_dir)
    finally:
        await conn.close()

    print(f"All migrations complete. Applied {len(applied)} new migration(s).")


if __name__ == "__main__":
    asyncio.run(run())
