from uuid import uuid4

import pytest

from app.domain.reducers import InvalidStateTransitionError, reduce_node
from app.domain.schemas import (
    AggregateFrozen,
    EventEnvelope,
    ExternalDriftResolved,
    ResourceAllocationRequested,
)


@pytest.fixture
def base_ids():
    return {
        "tenant_id": uuid4(),
        "aggregate_id": uuid4(),
        "event_id": uuid4(),
    }


def test_resource_allocation_transitions_state_correctly(base_ids):
    allocation_event = EventEnvelope(
        event_id=base_ids["event_id"],
        tenant_id=base_ids["tenant_id"],
        aggregate_id=base_ids["aggregate_id"],
        sequence_id=1,
        timestamp_utc_ms=1680000000000,
        idempotency_key="req-1",
        actor_id="user-1",
        expected_version=0,
        payload=ResourceAllocationRequested(
            node_id=base_ids["aggregate_id"],
            target_cpu_cores=2.0,
            target_memory_gb=4.0,
            reason_code="initial scale",
        ),
    )

    state = reduce_node(None, allocation_event)

    assert state.cpu_cores == 2.0
    assert state.memory_gb == 4.0
    assert state.lifecycle_state == "active"
    assert state.last_sequence_id == 1


def test_frozen_aggregate_rejects_allocation(base_ids):
    freeze_event = EventEnvelope(
        event_id=uuid4(),
        tenant_id=base_ids["tenant_id"],
        aggregate_id=base_ids["aggregate_id"],
        sequence_id=1,
        timestamp_utc_ms=1680000000000,
        idempotency_key="freeze-1",
        actor_id="system",
        expected_version=0,
        payload=AggregateFrozen(
            severity="High", drift_details={"reason": "IAM modified externally"}
        ),
    )
    state = reduce_node(None, freeze_event)

    allocation_event = EventEnvelope(
        event_id=uuid4(),
        tenant_id=base_ids["tenant_id"],
        aggregate_id=base_ids["aggregate_id"],
        sequence_id=2,
        timestamp_utc_ms=1680000000100,
        idempotency_key="req-2",
        actor_id="user-1",
        expected_version=1,
        payload=ResourceAllocationRequested(
            node_id=base_ids["aggregate_id"],
            target_cpu_cores=4.0,
            target_memory_gb=8.0,
            reason_code="scale up attempt",
        ),
    )

    with pytest.raises(InvalidStateTransitionError, match="frozen node"):
        reduce_node(state, allocation_event)


def test_replay_ignores_past_sequence_ids(base_ids):
    allocation_1 = EventEnvelope(
        event_id=uuid4(),
        tenant_id=base_ids["tenant_id"],
        aggregate_id=base_ids["aggregate_id"],
        sequence_id=2,
        timestamp_utc_ms=1680000000000,
        idempotency_key="req-1",
        actor_id="user-1",
        expected_version=1,
        payload=ResourceAllocationRequested(
            node_id=base_ids["aggregate_id"],
            target_cpu_cores=2.0,
            target_memory_gb=4.0,
            reason_code="valid scale",
        ),
    )
    state = reduce_node(None, allocation_1)

    stale_event = EventEnvelope(
        event_id=uuid4(),
        tenant_id=base_ids["tenant_id"],
        aggregate_id=base_ids["aggregate_id"],
        sequence_id=1,
        timestamp_utc_ms=1670000000000,
        idempotency_key="req-old",
        actor_id="user-1",
        expected_version=0,
        payload=ResourceAllocationRequested(
            node_id=base_ids["aggregate_id"],
            target_cpu_cores=1.0,
            target_memory_gb=2.0,
            reason_code="stale scale",
        ),
    )

    next_state = reduce_node(state, stale_event)

    assert next_state.cpu_cores == 2.0
    assert next_state.last_sequence_id == 2


def test_drift_resolve_unfreezes_node(base_ids):
    freeze_event = EventEnvelope(
        event_id=uuid4(),
        tenant_id=base_ids["tenant_id"],
        aggregate_id=base_ids["aggregate_id"],
        sequence_id=1,
        timestamp_utc_ms=1680000000000,
        idempotency_key="freeze-1",
        actor_id="system",
        expected_version=0,
        payload=AggregateFrozen(severity="Medium", drift_details={"x": "y"}),
    )
    state = reduce_node(None, freeze_event)

    resolve_event = EventEnvelope(
        event_id=uuid4(),
        tenant_id=base_ids["tenant_id"],
        aggregate_id=base_ids["aggregate_id"],
        sequence_id=2,
        timestamp_utc_ms=1680000000200,
        idempotency_key="resolve-1",
        actor_id="operator-1",
        expected_version=1,
        payload=ExternalDriftResolved(
            resolution_mode="AcceptExternalReality", resolved_by="operator-1"
        ),
    )

    next_state = reduce_node(state, resolve_event)
    assert next_state.lifecycle_state == "active"
