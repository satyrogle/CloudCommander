from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import middleware
from app.api.middleware import BackpressureMiddleware


def test_middleware_converts_value_error_to_bad_request():
    app = FastAPI()
    app.add_middleware(BackpressureMiddleware)

    @app.get("/boom")
    async def boom():
        raise ValueError("invalid payload")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/boom")

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid payload"


def test_middleware_converts_type_error_to_bad_request():
    app = FastAPI()
    app.add_middleware(BackpressureMiddleware)

    @app.get("/type-boom")
    async def type_boom():
        raise TypeError("bad type")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/type-boom")

    assert response.status_code == 400
    assert response.json()["detail"] == "bad type"


def test_middleware_returns_429_when_backpressure_is_overloaded(monkeypatch):
    app = FastAPI()
    app.add_middleware(BackpressureMiddleware)

    @app.post("/write")
    async def write():
        return {"ok": True}

    async def _overloaded():
        return True

    monkeypatch.setattr(middleware.backpressure_manager, "is_overloaded", _overloaded)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/write")

    assert response.status_code == 429
    assert "overloaded" in response.json()["detail"]
