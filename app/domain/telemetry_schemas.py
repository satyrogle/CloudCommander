from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class EventSource(str, Enum):
    PID = "PID"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    TOKEN_BUCKET = "TOKEN_BUCKET"
    SYSTEM = "SYSTEM"


class TelemetryEvent(BaseModel):
    id: str
    timestamp: datetime
    source: EventSource
    severity: EventSeverity
    type: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
