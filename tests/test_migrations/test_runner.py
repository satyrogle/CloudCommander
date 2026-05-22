from __future__ import annotations

import pytest

from migrations.run import apply_migrations, migration_checksum


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, applied: dict[str, str] | None = None):
        self.applied = applied or {}
        self.executed_sql: list[str] = []

    async def execute(self, sql: str, *args):
        if "INSERT INTO schema_migrations" in sql:
            filename, checksum = args
            self.applied[filename] = checksum
            return
        if "CREATE TABLE IF NOT EXISTS schema_migrations" not in sql:
            self.executed_sql.append(sql)

    async def fetchrow(self, query: str, filename: str):
        _ = query
        checksum = self.applied.get(filename)
        if checksum is None:
            return None
        return {"checksum": checksum}

    def transaction(self):
        return _Tx()


@pytest.mark.asyncio
async def test_apply_migrations_tracks_files_and_skips_second_run(tmp_path):
    migration_file = tmp_path / "001_initial.sql"
    migration_file.write_text("CREATE TABLE example(id INTEGER);", encoding="utf-8")
    conn = _FakeConn()

    first = await apply_migrations(conn, tmp_path)
    second = await apply_migrations(conn, tmp_path)

    assert first == ["001_initial.sql"]
    assert second == []
    assert len(conn.executed_sql) == 1


@pytest.mark.asyncio
async def test_apply_migrations_rejects_checksum_drift(tmp_path):
    migration_file = tmp_path / "001_initial.sql"
    original_sql = "CREATE TABLE example(id INTEGER);"
    migration_file.write_text(original_sql, encoding="utf-8")
    conn = _FakeConn({"001_initial.sql": migration_checksum(original_sql)})

    migration_file.write_text("CREATE TABLE changed(id INTEGER);", encoding="utf-8")

    with pytest.raises(RuntimeError, match="different checksum"):
        await apply_migrations(conn, tmp_path)
