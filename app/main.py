from __future__ import annotations

from fastapi import FastAPI

from app.api.middleware import BackpressureMiddleware
from app.api.routers.commands import router as commands_router
from app.api.routers.projections import router as projections_router
from app.api.routers.telemetry import router as telemetry_router

app = FastAPI(title="CloudCommander API")
app.add_middleware(BackpressureMiddleware)
app.include_router(commands_router)
app.include_router(projections_router)

app.include_router(telemetry_router)
