from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.routers import telemetry
from app.main import app


class _AcquireCtx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return _AcquireCtx(self.conn)


class _FakeConn:
    def __init__(self, nodes, edges):
        self.nodes = nodes
        self.edges = edges

    async def fetch(self, query, tenant_id):
        _ = tenant_id
        if "FROM read_model_nodes" in query:
            return [{"node_id": node_id} for node_id in self.nodes]
        if "FROM read_model_service_graph_edges" in query:
            return [
                {"source_node_id": source, "target_node_id": target}
                for source, target in self.edges
            ]
        raise AssertionError(f"Unexpected query: {query}")


NODE_A = UUID("00000000-0000-0000-0000-000000000001")
NODE_B = UUID("00000000-0000-0000-0000-000000000002")
NODE_C = UUID("00000000-0000-0000-0000-000000000003")


def test_graph_centrality_requires_tenant_header():
    app.state.db_pool = _FakePool(_FakeConn([], []))
    client = TestClient(app)

    response = client.get("/api/v1/telemetry/graph/centrality")

    assert response.status_code == 422
    assert "x-tenant-id" in response.text.lower()


def test_graph_centrality_returns_ranked_nodes_from_read_models():
    app.state.db_pool = _FakePool(
        _FakeConn(
            nodes=[NODE_A, NODE_B],
            edges=[(NODE_A, NODE_B), (NODE_B, NODE_C)],
        )
    )
    client = TestClient(app)

    response = client.get(
        "/api/v1/telemetry/graph/centrality",
        headers={"x-tenant-id": str(uuid4())},
    )

    assert response.status_code == 200
    body = response.json()
    assert body[0] == {
        "node_id": str(NODE_C),
        "centrality_score": 1.0,
        "rank": 1,
    }
    assert {item["node_id"] for item in body} == {str(NODE_A), str(NODE_B), str(NODE_C)}


def test_graph_centrality_returns_empty_list_for_empty_graph():
    app.state.db_pool = _FakePool(_FakeConn(nodes=[], edges=[]))
    client = TestClient(app)

    response = client.get(
        "/api/v1/telemetry/graph/centrality",
        headers={"x-tenant-id": str(uuid4())},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_backpressure_telemetry_returns_raw_and_ema_fields(monkeypatch):
    async def _snapshot():
        return {
            "is_overloaded": False,
            "utilization_rho": 0.5,
            "arrival_rate_hz": 2.0,
            "service_rate_hz": 4.0,
            "raw_arrival_rate_hz": 2.0,
            "raw_service_rate_hz": 4.0,
            "raw_utilization_rho": 0.5,
            "ema_arrival_rate_hz": 1.5,
            "ema_service_rate_hz": 3.5,
            "ema_utilization_rho": 0.4,
            "limit_rho": 0.95,
        }

    monkeypatch.setattr(telemetry.backpressure_manager, "get_snapshot", _snapshot)
    client = TestClient(app)

    response = client.get("/api/v1/telemetry/system/backpressure")

    assert response.status_code == 200
    body = response.json()
    assert body["raw_arrival_rate_hz"] == 2.0
    assert body["ema_utilization_rho"] == 0.4


def test_reconciler_telemetry_returns_circuit_breaker_state(monkeypatch):
    async def _snapshot():
        return {
            "state": "open",
            "recent_failure_count": 5,
            "opened_at": 1000.0,
            "next_retry_at": 1120.0,
        }

    monkeypatch.setattr(telemetry.reconciler_circuit_breaker, "get_snapshot", _snapshot)
    client = TestClient(app)

    response = client.get("/api/v1/telemetry/system/reconciler")

    assert response.status_code == 200
    assert response.json() == {
        "state": "open",
        "recent_failure_count": 5,
        "opened_at": 1000.0,
        "next_retry_at": 1120.0,
    }
