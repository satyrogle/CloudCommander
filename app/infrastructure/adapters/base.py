from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict


class EgressBucketSaturated(Exception):
    """Raised when the leaky bucket burst capacity is exceeded."""


class LeakyBucketAdapter:
    def __init__(self, dispatch_rate_hz: float, burst_capacity: int):
        if dispatch_rate_hz <= 0:
            raise ValueError("dispatch_rate_hz must be greater than 0")
        if burst_capacity <= 0:
            raise ValueError("burst_capacity must be greater than 0")

        self.dispatch_rate_hz = dispatch_rate_hz
        self.capacity = burst_capacity
        self.queue: asyncio.Queue[
            tuple[asyncio.Future[Any], Callable[..., Awaitable[Any]], tuple[Any, ...], dict[str, Any]]
        ] = asyncio.Queue(maxsize=burst_capacity)
        self._leak_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._leak_task is not None and not self._leak_task.done():
            return
        self._leak_task = asyncio.create_task(self._leak())

    async def stop(self) -> None:
        leak_task = self._leak_task
        if leak_task is None:
            return

        leak_task.cancel()
        try:
            await leak_task
        except asyncio.CancelledError:
            pass
        finally:
            self._leak_task = None

        while not self.queue.empty():
            future, _, _, _ = self.queue.get_nowait()
            if not future.done():
                future.set_exception(asyncio.CancelledError())
            self.queue.task_done()

    async def _leak(self) -> None:
        interval = 1.0 / self.dispatch_rate_hz
        next_dispatch_at = time.monotonic() + interval

        while True:
            future: asyncio.Future[Any] | None = None
            dequeued = False
            try:
                now = time.monotonic()
                if now < next_dispatch_at:
                    await asyncio.sleep(next_dispatch_at - now)

                future, func, args, kwargs = await self.queue.get()
                dequeued = True
                result = await func(*args, **kwargs)
                if not future.done():
                    future.set_result(result)
            except asyncio.CancelledError:
                if dequeued and future is not None and not future.done():
                    future.set_exception(asyncio.CancelledError())
                raise
            except Exception as exc:
                if dequeued and future is not None and not future.done():
                    future.set_exception(exc)
            finally:
                if dequeued:
                    self.queue.task_done()
                    next_dispatch_at = max(next_dispatch_at + interval, time.monotonic())

    async def execute(
        self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        if self._leak_task is None or self._leak_task.done():
            raise RuntimeError("Leaky bucket dispatcher is not running. Call start() first.")

        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()

        try:
            self.queue.put_nowait((future, func, args, kwargs))
        except asyncio.QueueFull as exc:
            raise EgressBucketSaturated(
                f"External API adapter saturated. Dropping request. Max capacity: {self.capacity}"
            ) from exc

        return await future


class CloudAdapter(ABC):
    async def start(self) -> None:
        """Optional lifecycle hook for adapters with background resources."""

    async def stop(self) -> None:
        """Optional lifecycle hook for adapters with background resources."""

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
