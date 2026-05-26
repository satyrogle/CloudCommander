from __future__ import annotations

import pytest

from app.control.kalman_filter import SystemUtilizationFilter
from app.control.pid_guardrail import PIDGuardrailController


def test_kalman_filter_suppresses_transient_spikes():
    filt = SystemUtilizationFilter(process_noise=0.001, measurement_noise=1.0)
    measurements = [0.5, 0.9, 0.1, 0.5, 0.9, 0.1, 0.5, 0.9, 0.1, 0.5]
    estimates = [filt.feed_measurement(m) for m in measurements]

    raw_max_deviation = max(abs(m - 0.5) for m in measurements)
    filtered_max_deviation = max(abs(e - 0.5) for e in estimates)

    assert filtered_max_deviation < raw_max_deviation
    assert filtered_max_deviation < 0.25


def test_pid_with_kalman_converges_on_real_step_change(monkeypatch):
    ticks = iter([float(t) for t in range(1, 40)])
    monkeypatch.setattr("app.control.pid_guardrail.time.time", lambda: next(ticks))

    controller = PIDGuardrailController(
        kp=1.0,
        ki=0.0,
        kd=0.0,
        setpoint=0.7,
        kalman_process_noise=0.005,
        kalman_measurement_noise=0.05,
    )
    aggregate_id = "tenant-a:agg-step"

    for _ in range(5):
        controller.observe_resource_change(current_utilization=0.2, aggregate_id=aggregate_id)

    post_step_estimates = []
    for _ in range(15):
        controller.observe_resource_change(current_utilization=0.8, aggregate_id=aggregate_id)
        state = controller.get_latest_state(aggregate_id)
        post_step_estimates.append(state["filtered_utilization"])

    assert post_step_estimates[-1] > 0.7
    assert post_step_estimates[-1] > post_step_estimates[0]
    assert all(
        later >= earlier for earlier, later in zip(post_step_estimates, post_step_estimates[1:])
    )
