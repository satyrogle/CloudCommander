from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_db_pool, get_tenant_id
from app.api.middleware import backpressure_manager
from app.control.graph_centrality import calculate_eigenvector_centrality
from app.domain.telemetry_schemas import EventSeverity, EventSource, TelemetryEvent
from app.domain.schemas import BackpressureTelemetry, GraphCentralityNode, ReconcilerTelemetry
from app.infrastructure.telemetry.normalizer import normalize_control_plane_event
from app.worker.reconciler import reconciler_circuit_breaker

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.get("/system/backpressure", response_model=BackpressureTelemetry)
async def get_system_backpressure():
    snapshot = await backpressure_manager.get_snapshot()

    return {
        "status": "overloaded" if snapshot["is_overloaded"] else "healthy",
        "utilization_rho": round(snapshot["utilization_rho"], 4),
        "arrival_rate_hz": round(snapshot["arrival_rate_hz"], 2),
        "service_rate_hz": round(snapshot["service_rate_hz"], 2),
        "raw_arrival_rate_hz": round(snapshot["raw_arrival_rate_hz"], 2),
        "raw_service_rate_hz": round(snapshot["raw_service_rate_hz"], 2),
        "raw_utilization_rho": round(snapshot["raw_utilization_rho"], 4),
        "ema_arrival_rate_hz": round(snapshot["ema_arrival_rate_hz"], 2),
        "ema_service_rate_hz": round(snapshot["ema_service_rate_hz"], 2),
        "ema_utilization_rho": round(snapshot["ema_utilization_rho"], 4),
        "limit_rho": snapshot["limit_rho"],
    }


@router.get("/system/reconciler", response_model=ReconcilerTelemetry)
async def get_system_reconciler():
    return await reconciler_circuit_breaker.get_snapshot()


@router.get("/graph/centrality", response_model=list[GraphCentralityNode])
async def get_graph_centrality(
    tenant_id: UUID = Depends(get_tenant_id),
    pool: Any = Depends(get_db_pool),
):
    nodes_query = """
        SELECT node_id
        FROM read_model_nodes
        WHERE tenant_id = $1 AND lifecycle_state != 'tombstoned'
    """
    edges_query = """
        SELECT source_node_id, target_node_id
        FROM read_model_service_graph_edges
        WHERE tenant_id = $1
    """

    async with pool.acquire() as conn:
        node_records = await conn.fetch(nodes_query, tenant_id)
        edge_records = await conn.fetch(edges_query, tenant_id)

    nodes = {record["node_id"] for record in node_records}
    edges = [
        (record["source_node_id"], record["target_node_id"])
        for record in edge_records
    ]
    for source_node_id, target_node_id in edges:
        nodes.add(source_node_id)
        nodes.add(target_node_id)

    return await asyncio.to_thread(
        calculate_eigenvector_centrality,
        nodes=list(nodes),
        edges=edges,
    )


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


@router.get("/events", response_model=list[TelemetryEvent])
async def get_telemetry_events(
    limit: int = Query(default=50, ge=1, le=200),
    source: EventSource | None = Query(default=None),
    severity: EventSeverity | None = Query(default=None),
    tenant_id: UUID = Depends(get_tenant_id),
    pool: Any = Depends(get_db_pool),
):
    query = """
        SELECT event_id, event_type, payload, timestamp_utc_ms
        FROM events
        WHERE tenant_id = $1
          AND event_type IN (
            'CompensationStrategySelected',
            'GuardrailThresholdBreached',
            'ExternalDriftResolved',
            'RollbackInitiated'
          )
        ORDER BY sequence_id DESC
        LIMIT 200
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(query, tenant_id)

    normalized_events = [normalize_control_plane_event(dict(record)) for record in records]

    if source is not None:
        normalized_events = [event for event in normalized_events if event.source == source]
    if severity is not None:
        normalized_events = [event for event in normalized_events if event.severity == severity]

    normalized_events.sort(key=lambda event: event.timestamp, reverse=True)
    return normalized_events[:limit]
