from __future__ import annotations

import json
from typing import Any

import asyncpg


def _encode_json(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value)


async def configure_json_codecs(conn: asyncpg.Connection) -> None:
    for type_name in ("json", "jsonb"):
        await conn.set_type_codec(
            type_name,
            schema="pg_catalog",
            encoder=_encode_json,
            decoder=json.loads,
            format="text",
        )
