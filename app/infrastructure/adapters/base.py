from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class CloudAdapter(ABC):
    @abstractmethod
    async def apply_allocation(self, aggregate_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempts to apply infrastructure state.
        Returns standardized status dictionary:
        {
            "status": "success" | "partial_failure" | "throttled" | "timeout",
            "nodes_success": int,
            "nodes_failed": int,
            "provider_message": str,
        }
        """
        raise NotImplementedError

    @abstractmethod
    async def rollback_allocation(self, aggregate_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempts to compensate or revert infrastructure state.
        Returns the same standardized status dictionary as apply_allocation.
        """
        raise NotImplementedError
