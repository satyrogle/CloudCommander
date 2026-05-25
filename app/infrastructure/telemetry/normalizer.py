from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.telemetry_schemas import (
    EventSeverity,
    EventSource,
    TelemetryEvent,
)


def _from_timestamp_ms(value: int | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def normalize_control_plane_event(raw_event: dict) -> TelemetryEvent:
    event_type = str(raw_event.get("event_type") or raw_event.get("type") or "unknown")
    payload = raw_event.get("payload") or {}

    source = EventSource.SYSTEM
    severity = EventSeverity.INFO
    message = raw_event.get("detail") or "System event recorded."

    if event_type == "GuardrailThresholdBreached":
        source = EventSource.PID
        severity_name = str(payload.get("severity", "warning")).upper()
        if severity_name in {"FROZEN", "APPROVAL_REQUIRED"}:
            severity = EventSeverity.CRITICAL
        elif severity_name == "WARNING":
            severity = EventSeverity.WARNING
        message = payload.get("reason") or "PID guardrail threshold breached."
    elif event_type in {"CompensationStrategySelected", "RollbackInitiated"}:
        source = EventSource.CIRCUIT_BREAKER
        severity = EventSeverity.CRITICAL
        strategy = payload.get("selected_strategy")
        if event_type == "CompensationStrategySelected" and strategy:
            message = f"Compensation strategy selected: {strategy}"
        elif event_type == "RollbackInitiated":
            reason = payload.get("reason_code", "unknown")
            message = f"Rollback initiated: {reason}"
    elif event_type == "ExternalDriftResolved":
        source = EventSource.SYSTEM
        severity = EventSeverity.INFO
        mode = payload.get("resolution_mode", "unknown")
        message = f"External drift resolved via {mode}"

    return TelemetryEvent(
        id=str(raw_event.get("event_id") or raw_event.get("id") or uuid4()),
        timestamp=_from_timestamp_ms(raw_event.get("timestamp_utc_ms")),
        source=source,
        severity=severity,
        type=event_type,
        message=str(message),
        metadata=payload if isinstance(payload, dict) else {},
    )
