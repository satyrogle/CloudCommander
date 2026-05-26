from __future__ import annotations


class SystemUtilizationFilter:
    """Single-variable Kalman filter for utilization telemetry smoothing."""

    def __init__(self, process_noise: float = 0.005, measurement_noise: float = 0.05):
        if process_noise < 0:
            raise ValueError("process_noise must be >= 0")
        if measurement_noise <= 0:
            raise ValueError("measurement_noise must be > 0")

        self.q = process_noise
        self.r = measurement_noise
        self.estimated_utilization = 0.0
        self.error_covariance = 1.0
        self.initialized = False

    def feed_measurement(self, raw_measurement: float) -> float:
        if not self.initialized:
            self.estimated_utilization = raw_measurement
            self.error_covariance = 1.0
            self.initialized = True
            return self.estimated_utilization

        predicted_covariance = self.error_covariance + self.q
        kalman_gain = predicted_covariance / (predicted_covariance + self.r)

        self.estimated_utilization = self.estimated_utilization + kalman_gain * (
            raw_measurement - self.estimated_utilization
        )
        self.error_covariance = (1.0 - kalman_gain) * predicted_covariance
        return self.estimated_utilization
