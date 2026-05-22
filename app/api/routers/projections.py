from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_db_pool, get_tenant_id

router = APIRouter(prefix="/api/v1/projections", tags=["Projections"])


@router.get("/nodes/{node_id}")
async def get_node_projection(
    node_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    pool: Any = Depends(get_db_pool),
):
    query = """
        SELECT node_id, lifecycle_state, cpu_cores, memory_gb, last_sequence_id
        FROM read_model_nodes
        WHERE tenant_id = $1 AND node_id = $2
    """
    async with pool.acquire() as conn:
        record = await conn.fetchrow(query, tenant_id, node_id)

    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node projection not found")

    return dict(record)
