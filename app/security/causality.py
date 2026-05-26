from __future__ import annotations

from enum import Enum


class CausalRelation(str, Enum):
    STALE = "stale"
    NEXT_EXPECTED = "next_expected"
    CONCURRENT = "concurrent"
    GAP = "gap"


def compare_vector_clocks(
    v_incoming: dict[str, int], v_current: dict[str, int], sender_id: str
) -> CausalRelation:
    """
    Compare incoming and current vector clocks.

    Rules:
    - STALE: incoming is identical to or dominated by current
    - NEXT_EXPECTED: sender advanced by exactly one tick, all others not ahead
    - GAP: incoming dominates current but is not the direct next expected step
    - CONCURRENT: mixed advancement where neither clock dominates
    """
    all_keys = set(v_incoming.keys()).union(v_current.keys()).union({sender_id})
    inc = {k: int(v_incoming.get(k, 0)) for k in all_keys}
    cur = {k: int(v_current.get(k, 0)) for k in all_keys}

    less_or_equal = all(inc[k] <= cur[k] for k in all_keys)
    greater_or_equal = all(inc[k] >= cur[k] for k in all_keys)

    if inc == cur or less_or_equal:
        return CausalRelation.STALE

    sender_is_next = inc[sender_id] == cur[sender_id] + 1
    others_equal = all(inc[k] == cur[k] for k in all_keys if k != sender_id)
    if sender_is_next and others_equal:
        return CausalRelation.NEXT_EXPECTED

    if greater_or_equal and not less_or_equal:
        return CausalRelation.GAP

    return CausalRelation.CONCURRENT
