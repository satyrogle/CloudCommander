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
