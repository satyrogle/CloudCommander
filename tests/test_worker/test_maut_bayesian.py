from app.control.maut_rollback import RollbackDecisionEngine
from app.worker.reconciler import DEFAULT_MAUT_WEIGHTS


def test_bayesian_failures_raise_operational_risk_weight():
    engine = RollbackDecisionEngine(
        DEFAULT_MAUT_WEIGHTS,
        prior_infra_risk=0.35,
        risk_weight_scale=0.6,
    )
    before = engine.get_effective_weights()["operational_risk_normalized"]

    engine.observe_evidence("partial_failure")
    engine.observe_evidence("timeout")
    engine.observe_evidence("timeout")

    after = engine.get_effective_weights()["operational_risk_normalized"]
    assert after > before
    assert engine.posterior_infra_risk > engine.prior_infra_risk


def test_bayesian_successes_reduce_elevated_risk_posterior():
    engine = RollbackDecisionEngine(DEFAULT_MAUT_WEIGHTS)

    engine.observe_evidence("timeout")
    engine.observe_evidence("timeout")
    elevated = engine.posterior_infra_risk

    engine.observe_evidence("success")
    engine.observe_evidence("success")
    engine.observe_evidence("success")

    assert engine.posterior_infra_risk < elevated


def test_maut_strict_mathematical_determinism():
    """
    Proves that identical starting states and evidence streams produce
    identical posterior risks and effective weights down to the float limit.
    """
    engine1 = RollbackDecisionEngine(DEFAULT_MAUT_WEIGHTS)
    engine2 = RollbackDecisionEngine(DEFAULT_MAUT_WEIGHTS)

    evidence_stream = ["timeout", "partial_failure", "success", "timeout", "throttled"]

    for evidence in evidence_stream:
        engine1.observe_evidence(evidence)
        engine2.observe_evidence(evidence)

    assert engine1.posterior_infra_risk == engine2.posterior_infra_risk
    assert engine1.get_effective_weights() == engine2.get_effective_weights()


def test_bayesian_path_selection_shift_is_deterministic():
    """
    Proves that accumulating infrastructure risk deterministically shifts the engine's
    preferred compensation path from a cost-optimized strategy to a risk-averse strategy.
    """
    engine = RollbackDecisionEngine(
        DEFAULT_MAUT_WEIGHTS,
        prior_infra_risk=0.1,
        risk_weight_scale=1.0,
    )

    available_paths = [
        {
            "strategy_id": "full_revert",
            "attributes": {
                "restore_time_normalized": 0.1,
                "operational_risk_normalized": 0.9,
                "infrastructure_cost_normalized": 0.1,
            },
        },
        {
            "strategy_id": "forward_fix_retry",
            "attributes": {
                "restore_time_normalized": 0.3,
                "operational_risk_normalized": 0.2,
                "infrastructure_cost_normalized": 0.9,
            },
        },
    ]

    initial_choice = engine.evaluate_rollback_paths(available_paths)
    assert initial_choice == "forward_fix_retry"

    for _ in range(6):
        engine.observe_evidence("timeout")

    shifted_choice = engine.evaluate_rollback_paths(available_paths)
    assert shifted_choice == "full_revert"


def test_engine_state_reset_determinism():
    """
    Proves that resetting beliefs reliably returns the mathematical state
    to exact initial conditions, preventing cross-aggregate contamination.
    """
    engine = RollbackDecisionEngine(DEFAULT_MAUT_WEIGHTS)
    initial_weights = engine.get_effective_weights()
    initial_risk = engine.prior_infra_risk

    engine.observe_evidence("timeout")
    engine.observe_evidence("partial_failure")

    assert engine.posterior_infra_risk != initial_risk
    assert engine.get_effective_weights() != initial_weights

    engine.reset_beliefs()

    assert engine.posterior_infra_risk == initial_risk
    assert engine.get_effective_weights() == initial_weights
