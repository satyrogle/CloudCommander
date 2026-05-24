from __future__ import annotations

from typing import Dict, List, Tuple
from uuid import UUID


DEFAULT_BASELINE_SCORE = 0.1
DEFAULT_MAX_ITERS = 50
DEFAULT_EPSILON = 1e-6


def calculate_eigenvector_centrality(
    nodes: List[UUID],
    edges: List[Tuple[UUID, UUID]],
    max_iters: int = DEFAULT_MAX_ITERS,
    epsilon: float = DEFAULT_EPSILON,
    baseline_score: float = DEFAULT_BASELINE_SCORE,
) -> List[Dict]:
    if not nodes:
        return []

    ordered_nodes = sorted(set(nodes), key=str)
    scores = {node: 1.0 for node in ordered_nodes}
    incoming_edges = {node: [] for node in ordered_nodes}

    for source_node_id, target_node_id in edges:
        if source_node_id in incoming_edges and target_node_id in incoming_edges:
            incoming_edges[target_node_id].append(source_node_id)

    for _ in range(max_iters):
        previous_scores = dict(scores)
        max_score = 0.0

        for node in ordered_nodes:
            scores[node] = (
                sum(previous_scores[source] for source in incoming_edges[node])
                + baseline_score
            )
            max_score = max(max_score, scores[node])

        if max_score > 0:
            for node in ordered_nodes:
                scores[node] /= max_score

        diff = sum(abs(scores[node] - previous_scores[node]) for node in ordered_nodes)
        if diff < epsilon:
            break

    results = [
        {"node_id": node, "centrality_score": round(score, 4)}
        for node, score in scores.items()
    ]
    results.sort(key=lambda item: (-item["centrality_score"], str(item["node_id"])))

    for rank, item in enumerate(results, start=1):
        item["rank"] = rank

    return results
