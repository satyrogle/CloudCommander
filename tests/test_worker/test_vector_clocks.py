from __future__ import annotations

from app.security.causality import CausalRelation, compare_vector_clocks


def test_ordered_replay_allowed():
    relation = compare_vector_clocks(
        v_incoming={"node_1": 2, "node_2": 1},
        v_current={"node_1": 1, "node_2": 1},
        sender_id="node_1",
    )
    assert relation == CausalRelation.NEXT_EXPECTED


def test_stale_event_dropped():
    relation = compare_vector_clocks(
        v_incoming={"node_1": 1, "node_2": 1},
        v_current={"node_1": 2, "node_2": 1},
        sender_id="node_1",
    )
    assert relation == CausalRelation.STALE


def test_concurrent_clocks_quarantined():
    relation = compare_vector_clocks(
        v_incoming={"node_1": 2, "node_2": 1},
        v_current={"node_1": 1, "node_2": 2},
        sender_id="node_1",
    )
    assert relation == CausalRelation.CONCURRENT


def test_causal_gap_detected():
    relation = compare_vector_clocks(
        v_incoming={"node_1": 4, "node_2": 1},
        v_current={"node_1": 1, "node_2": 1},
        sender_id="node_1",
    )
    assert relation == CausalRelation.GAP
