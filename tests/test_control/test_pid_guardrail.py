from app.control.pid_guardrail import PIDGuardrailController


def test_pid_fuzzy_instability_bands_are_distinct():
    controller = PIDGuardrailController(kp=0.5, ki=0.1, kd=0.2, setpoint=0.8)

    stable = controller.classify_instability(0.05)
    drifting = controller.classify_instability(0.60)
    volatile = controller.classify_instability(1.40)

    assert stable["label"] == "stable"
    assert drifting["label"] == "drifting"
    assert volatile["label"] == "volatile"


def test_pid_observe_updates_latest_state():
    controller = PIDGuardrailController(kp=0.5, ki=0.1, kd=0.2, setpoint=0.8)

    controller.observe_resource_change(current_utilization=0.95, aggregate_id="agg-1")
    state = controller.get_latest_state()

    assert state["label"] in {"stable", "drifting", "volatile"}
    assert 0.0 <= state["degree"] <= 1.0
