from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.control.backpressure_manager import BackpressureManager

backpressure_manager = BackpressureManager(window_seconds=60, limit_rho=0.95)


class BackpressureMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            if request.method in {"POST", "PUT", "DELETE", "PATCH"}:
                is_overloaded = await backpressure_manager.is_overloaded()
                if is_overloaded:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": "System queue overloaded. Retry with exponential backoff."
                        },
                    )
                await backpressure_manager.record_arrival()

            return await call_next(request)
        except HTTPException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
        except (TypeError, ValueError) as exc:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": str(exc)},
            )
