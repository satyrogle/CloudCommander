from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class PIDGuardrailController:
    """Observe-only PID controller for resource trajectory monitoring."""

    def __init__(self, kp: float, ki: float, kd: float, setpoint: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.previous_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()

    def observe_resource_change(self, current_utilization: float, aggregate_id: str) -> float:
        current_time = time.time()
        dt = current_time - self.last_time
        if dt <= 0:
            dt = 1e-4

        error = self.setpoint - current_utilization
        self.integral += error * dt
        derivative = (error - self.previous_error) / dt

        u_t = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)

        self.previous_error = error
        self.last_time = current_time

        logger.info(
            "[PID Observe] Aggregate: %s | u(t): %.4f | Error: %.4f",
            aggregate_id,
            u_t,
            error,
        )
        return u_t
