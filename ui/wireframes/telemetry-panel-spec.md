# Telemetry & Guardrail UI Spec

## 1. Global Health Bar (Header Level)
- **Data Source:** `GET /api/v1/telemetry/system/backpressure`
- **Visuals:**
  - Green: `rho < 0.7`
  - Amber: `0.7 <= rho < 0.95`
  - Red/Pulsing: `rho >= 0.95` or `status=overloaded`
- **Metric Text:** `Control Plane Load: <rho> (λ: <arrival_rate_hz>/s | μ: <service_rate_hz>/s)`

## 2. Node Guardrail Badges (Cloud Map Overlay)
- **Data Source:** `GET /api/v1/telemetry/nodes/{node_id}/guardrail-state`
- **Behavior:**
  - Normal: no badge
  - Warning: amber badge
  - Approval_required: orange lock
  - Frozen: red lock (mutation controls disabled; API returns `423`)

## 3. Controller Event Log (Bottom Drawer)
- **Data Source:** `GET /api/v1/telemetry/events/recent`
- **Row Format:** `[Timestamp] | [Event Type] | [Aggregate ID] | [Summary]`
- Example:
  - `14:02:11 | CompensationStrategySelected | Node-X | selected full_revert (score 0.75)`
  - `14:05:00 | GuardrailThresholdBreached | Node-Y | severity warning (PID trajectory steep)`
