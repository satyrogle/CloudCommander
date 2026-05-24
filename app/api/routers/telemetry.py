from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_db_pool, get_tenant_id
from app.api.middleware import backpressure_manager

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.get("/system/backpressure")
async def get_system_backpressure():
    snapshot = await backpressure_manager.get_snapshot()

    return {
        "status": "overloaded" if snapshot["is_overloaded"] else "healthy",
        "utilization_rho": round(snapshot["utilization_rho"], 4),
        "arrival_rate_hz": round(snapshot["arrival_rate_hz"], 2),
        "service_rate_hz": round(snapshot["service_rate_hz"], 2),
        "limit_rho": snapshot["limit_rho"],
    }


@router.get("/nodes/{node_id}/guardrail-state")
async def get_node_guardrail_state(
    node_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    pool: Any = Depends(get_db_pool),
):
    query = """
        SELECT severity, metric_value, reason, timestamp_utc_ms
        FROM read_model_guardrail_alerts
        WHERE tenant_id = $1 AND node_id = $2
        ORDER BY timestamp_utc_ms DESC
        LIMIT 1
    """
    async with pool.acquire() as conn:
        record = await conn.fetchrow(query, tenant_id, node_id)

    return dict(record) if record else {"severity": "normal", "metric_value": 0.0, "reason": "No recent anomalies"}


@router.get("/events/recent")
async def get_recent_controller_events(
    limit: int = Query(default=10, ge=1, le=100),
    tenant_id: UUID = Depends(get_tenant_id),
    pool: Any = Depends(get_db_pool),
):
    query = """
        SELECT event_id, event_type, payload, timestamp_utc_ms
        FROM events
        WHERE tenant_id = $1
          AND event_type IN ('CompensationStrategySelected', 'GuardrailThresholdBreached', 'ExternalDriftResolved')
        ORDER BY sequence_id DESC
        LIMIT $2
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(query, tenant_id, limit)

    return [dict(r) for r in records]
