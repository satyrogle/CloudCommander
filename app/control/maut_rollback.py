from __future__ import annotations

from typing import Dict, List, Optional


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, value) for value in weights.values())
    if total <= 0:
        return dict(weights)
    return {key: max(0.0, value) / total for key, value in weights.items()}


class RollbackDecisionEngine:
    def __init__(
        self,
        weights: Dict[str, float],
        *,
        adaptive_enabled: bool = True,
        prior_infra_risk: float = 0.35,
        risk_weight_scale: float = 0.45,
    ):
        self.base_weights = _normalize_weights(weights)
        self.weights = dict(self.base_weights)
        self.adaptive_enabled = adaptive_enabled
        self.prior_infra_risk = max(0.0, min(1.0, prior_infra_risk))
        self.posterior_infra_risk = self.prior_infra_risk
        self.risk_weight_scale = max(0.0, risk_weight_scale)

        # Likelihoods for P(evidence | infra_risk_hypothesis).
        self._likelihoods = {
            "timeout": {"high": 0.85, "low": 0.25},
            "partial_failure": {"high": 0.75, "low": 0.35},
            "throttled": {"high": 0.70, "low": 0.40},
            "success": {"high": 0.20, "low": 0.80},
        }

        self._recompute_effective_weights()

    def score_strategy(self, strategy_id: str, attributes: Dict[str, float]) -> float:
        _ = strategy_id
        score = 0.0
        for attr, value in attributes.items():
            score += self.weights.get(attr, 0.0) * value
        return score

    def observe_evidence(self, status: str) -> None:
        if not self.adaptive_enabled:
            return

        likelihood = self._likelihoods.get(status)
        if likelihood is None:
            return

        high_prior = self.posterior_infra_risk
        low_prior = 1.0 - high_prior
        high_likelihood = likelihood["high"]
        low_likelihood = likelihood["low"]
        denominator = (high_likelihood * high_prior) + (low_likelihood * low_prior)
        if denominator <= 0:
            return

        self.posterior_infra_risk = (high_likelihood * high_prior) / denominator
        self._recompute_effective_weights()

    def get_effective_weights(self) -> Dict[str, float]:
        return dict(self.weights)

    def reset_beliefs(self) -> None:
        self.posterior_infra_risk = self.prior_infra_risk
        self._recompute_effective_weights()

    def _recompute_effective_weights(self) -> None:
        weights = dict(self.base_weights)
        operational_key = "operational_risk_normalized"
        donors = ("restore_time_normalized", "infrastructure_cost_normalized")

        risk_delta = max(0.0, self.posterior_infra_risk - self.prior_infra_risk)
        requested_shift = risk_delta * self.risk_weight_scale
        transferable = sum(weights.get(key, 0.0) for key in donors)
        actual_shift = min(requested_shift, transferable)

        if actual_shift > 0 and transferable > 0:
            for key in donors:
                current = weights.get(key, 0.0)
                deduction = actual_shift * (current / transferable)
                weights[key] = max(0.0, current - deduction)
            weights[operational_key] = weights.get(operational_key, 0.0) + actual_shift

        self.weights = _normalize_weights(weights)

    def evaluate_rollback_paths(self, paths: List[Dict]) -> Optional[str]:
        best_score = float("-inf")
        best_strategy: Optional[str] = None
        for path in paths:
            score = self.score_strategy(path["strategy_id"], path["attributes"])
            if score > best_score:
                best_score = score
                best_strategy = path["strategy_id"]
        return best_strategy
