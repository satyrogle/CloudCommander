from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


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
    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self.quarantine = [
            {
                "quarantine_id": 7,
                "tenant_id": tenant_id,
                "aggregate_id": uuid4(),
                "event_id": uuid4(),
                "sender_id": "node_1",
                "relation": "concurrent",
                "incoming_vclock": {"node_1": 2, "node_2": 1},
                "current_vclock": {"node_1": 1, "node_2": 2},
                "reason": "Concurrent split-brain mutation detected.",
                "quarantined_at": "2026-05-26T12:00:00+00:00",
            }
        ]
        self.outbox_updated = False

    def transaction(self):
        return _Tx()

    async def fetch(self, query, tenant_id, limit):
        _ = limit
        if "FROM read_model_causality_quarantine" in query:
            return [row for row in self.quarantine if row["tenant_id"] == tenant_id]
        raise AssertionError(f"Unexpected query: {query}")

    async def fetchrow(self, query, quarantine_id, tenant_id):
        if "FROM read_model_causality_quarantine" in query:
            for row in self.quarantine:
                if row["quarantine_id"] == quarantine_id and row["tenant_id"] == tenant_id:
                    return {
                        "quarantine_id": row["quarantine_id"],
                        "event_id": row["event_id"],
                        "aggregate_id": row["aggregate_id"],
                    }
            return None
        raise AssertionError(f"Unexpected query: {query}")

    async def execute(self, query, *args):
        if "UPDATE outbox" in query:
            self.outbox_updated = True
            return "UPDATE 1"
        if "DELETE FROM read_model_causality_quarantine" in query:
            quarantine_id, tenant_id = args
            self.quarantine = [
                row
                for row in self.quarantine
                if not (
                    row["quarantine_id"] == quarantine_id
                    and row["tenant_id"] == tenant_id
                )
            ]
            return "DELETE 1"
        raise AssertionError(f"Unexpected query: {query}")


@pytest.fixture(autouse=True)
def _disable_backpressure(monkeypatch):
    async def _not_overloaded():
        return False

    async def _record_arrival():
        return None

    class _Limiter:
        async def allow(self, tenant_id):
            _ = tenant_id
            return True

    monkeypatch.setattr("app.api.middleware.backpressure_manager.is_overloaded", _not_overloaded)
    monkeypatch.setattr("app.api.middleware.backpressure_manager.record_arrival", _record_arrival)
    monkeypatch.setattr("app.api.middleware.token_bucket_limiter", _Limiter())


def test_quarantine_telemetry_returns_rows():
    tenant_id = uuid4()
    app.state.db_pool = _FakePool(_FakeConn(tenant_id))
    client = TestClient(app)

    response = client.get(
        "/api/v1/telemetry/quarantine",
        headers={"x-tenant-id": str(tenant_id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["relation"] == "concurrent"
    assert "incoming_vclock" in body[0]
    assert "current_vclock" in body[0]


def test_quarantine_resolution_requires_tenant_admin_claim():
    tenant_id = uuid4()
    app.state.db_pool = _FakePool(_FakeConn(tenant_id))
    client = TestClient(app)

    response = client.post(
        "/api/v1/control/quarantine/7/resolve",
        json={"action": "DISCARD"},
        headers={
            "x-tenant-id": str(tenant_id),
            "x-actor-id": "viewer-1",
            "x-actor-claims": "tenant_viewer",
        },
    )

    assert response.status_code == 403
    assert "tenant admin claim required" in response.text.lower()


def test_quarantine_resolution_allows_tenant_admin_and_requeues():
    tenant_id = uuid4()
    conn = _FakeConn(tenant_id)
    app.state.db_pool = _FakePool(conn)
    client = TestClient(app)

    response = client.post(
        "/api/v1/control/quarantine/7/resolve",
        json={"action": "RETRY_FORCE"},
        headers={
            "x-tenant-id": str(tenant_id),
            "x-actor-id": "admin-1",
            "x-actor-claims": "tenant_admin",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["action"] == "RETRY_FORCE"
    assert body["requeued"] is True
    assert conn.outbox_updated is True
    assert conn.quarantine == []
