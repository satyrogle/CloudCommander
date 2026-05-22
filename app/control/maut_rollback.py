from __future__ import annotations

from typing import Dict, List, Optional


class RollbackDecisionEngine:
    def __init__(self, weights: Dict[str, float]):
        self.weights = weights

    def score_strategy(self, strategy_id: str, attributes: Dict[str, float]) -> float:
        _ = strategy_id
        score = 0.0
        for attr, value in attributes.items():
            score += self.weights.get(attr, 0.0) * value
        return score

    def evaluate_rollback_paths(self, paths: List[Dict]) -> Optional[str]:
        best_score = float("-inf")
        best_strategy: Optional[str] = None
        for path in paths:
            score = self.score_strategy(path["strategy_id"], path["attributes"])
            if score > best_score:
                best_score = score
                best_strategy = path["strategy_id"]
        return best_strategy
