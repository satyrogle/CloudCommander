import time

import pytest

from app.control.pid_guardrail import PIDGuardrailController


def test_per_aggregate_isolation():
    """
    Proves state is tracked per aggregate, preventing cross-tenant poisoning.
    """
    controller = PIDGuardrailController(kp=0.5, ki=0.1, kd=0.2, setpoint=0.8)

    for _ in range(5):
        controller.observe_resource_change(current_utilization=0.2, aggregate_id="agg-A")
        time.sleep(0.01)

    controller.observe_resource_change(current_utilization=0.2, aggregate_id="agg-B")

    state_a = controller.get_latest_state("agg-A")
    state_b = controller.get_latest_state("agg-B")

    assert state_a["control_signal_abs"] != state_b["control_signal_abs"]


def test_fuzzy_threshold_transitions():
    """
    Proves the control signal correctly maps to the fuzzy sets: stable, drifting, volatile.
    """
    c_stable = PIDGuardrailController(kp=1.0, ki=0.0, kd=0.0, setpoint=0.8)
    c_stable.observe_resource_change(current_utilization=0.7, aggregate_id="agg-stable")
    assert c_stable.get_latest_state("agg-stable")["label"] == "stable"

    c_drift = PIDGuardrailController(kp=1.0, ki=0.0, kd=0.0, setpoint=0.8)
    c_drift.observe_resource_change(current_utilization=0.2, aggregate_id="agg-drift")
    assert c_drift.get_latest_state("agg-drift")["label"] == "drifting"

    c_volatile = PIDGuardrailController(kp=5.0, ki=0.0, kd=0.0, setpoint=0.8)
    c_volatile.observe_resource_change(current_utilization=0.0, aggregate_id="agg-volatile")
    assert c_volatile.get_latest_state("agg-volatile")["label"] == "volatile"


def test_pid_classify_instability_bands_are_distinct():
    controller = PIDGuardrailController(kp=0.5, ki=0.1, kd=0.2, setpoint=0.8)

    stable = controller.classify_instability(0.05)
    drifting = controller.classify_instability(0.60)
    volatile = controller.classify_instability(1.40)

    assert stable["label"] == "stable"
    assert drifting["label"] == "drifting"
    assert volatile["label"] == "volatile"


def test_pid_same_first_observation_is_identical_for_distinct_aggregates(monkeypatch):
    ticks = iter([100.0, 101.0])
    monkeypatch.setattr("app.control.pid_guardrail.time.time", lambda: next(ticks))

    controller = PIDGuardrailController(kp=0.5, ki=0.1, kd=0.2, setpoint=0.8)

    u_a = controller.observe_resource_change(
        current_utilization=0.9,
        aggregate_id="tenant-a:agg-1",
    )
    u_b = controller.observe_resource_change(
        current_utilization=0.9,
        aggregate_id="tenant-b:agg-1",
    )

    assert u_a == pytest.approx(u_b)
