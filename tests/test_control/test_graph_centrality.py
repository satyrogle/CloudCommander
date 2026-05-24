from uuid import UUID

from app.control.graph_centrality import calculate_eigenvector_centrality


NODE_A = UUID("00000000-0000-0000-0000-000000000001")
NODE_B = UUID("00000000-0000-0000-0000-000000000002")
NODE_C = UUID("00000000-0000-0000-0000-000000000003")


def test_empty_graph_returns_empty_result():
    assert calculate_eigenvector_centrality([], []) == []


def test_disconnected_nodes_are_deterministic_and_normalized():
    results = calculate_eigenvector_centrality([NODE_B, NODE_A], [])

    assert [item["node_id"] for item in results] == [NODE_A, NODE_B]
    assert [item["rank"] for item in results] == [1, 2]
    assert all(item["centrality_score"] == 1.0 for item in results)


def test_dependency_chain_ranks_most_depended_on_node_highest():
    results = calculate_eigenvector_centrality(
        nodes=[NODE_A, NODE_B, NODE_C],
        edges=[(NODE_A, NODE_B), (NODE_B, NODE_C)],
    )

    assert results[0]["node_id"] == NODE_C
    assert results[0]["centrality_score"] == 1.0
    assert results[0]["rank"] == 1


def test_equal_scores_sort_by_node_id():
    results = calculate_eigenvector_centrality(
        nodes=[NODE_C, NODE_A, NODE_B],
        edges=[],
    )

    assert [item["node_id"] for item in results] == [NODE_A, NODE_B, NODE_C]


def test_unknown_edges_are_ignored():
    unknown = UUID("00000000-0000-0000-0000-000000000099")

    results = calculate_eigenvector_centrality(
        nodes=[NODE_A],
        edges=[(unknown, NODE_A), (NODE_A, unknown)],
    )

    assert results == [{"node_id": NODE_A, "centrality_score": 1.0, "rank": 1}]
