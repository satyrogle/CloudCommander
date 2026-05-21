from __future__ import annotations

from typing import Optional

from app.security.rbac_policy import verify_permission
from .schemas import (
    AggregateFrozen,
    EventEnvelope,
    ExternalDriftResolved,
    ResourceAllocationRequested,
    ResourceNodeSnapshot,
)


class InvalidStateTransitionError(Exception):
    pass


def reduce_node(
    state: Optional[ResourceNodeSnapshot], envelope: EventEnvelope
) -> ResourceNodeSnapshot:
    """Pure function to transition a ResourceNode state given an event envelope."""
    payload = envelope.payload

    if state is None:
        state = ResourceNodeSnapshot(
            node_id=envelope.aggregate_id,
            lifecycle_state="active",
            cpu_cores=0.0,
            memory_gb=0.0,
            last_sequence_id=0,
        )

    if envelope.sequence_id <= state.last_sequence_id:
        return state

    updates = {"last_sequence_id": envelope.sequence_id}

    if isinstance(payload, ResourceAllocationRequested):
        verify_permission(envelope.actor_claims, "allocate", envelope.aggregate_id)
        if state.lifecycle_state == "frozen":
            raise InvalidStateTransitionError("Cannot allocate resources on a frozen node.")
        updates["cpu_cores"] = payload.target_cpu_cores
        updates["memory_gb"] = payload.target_memory_gb

    elif isinstance(payload, AggregateFrozen):
        verify_permission(envelope.actor_claims, "freeze", envelope.aggregate_id)
        updates["lifecycle_state"] = "frozen"

    elif isinstance(payload, ExternalDriftResolved):
        verify_permission(envelope.actor_claims, "resolve", envelope.aggregate_id)
        if state.lifecycle_state != "frozen":
            raise InvalidStateTransitionError("Cannot resolve drift on an unfrozen node.")
        updates["lifecycle_state"] = "active"

    return state.model_copy(update=updates)
