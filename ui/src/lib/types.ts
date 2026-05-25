import type { Edge, Node } from "reactflow";

export type CentralityNode = {
  node_id: string;
  centrality_score: number;
  rank: number;
};

export type ServiceGraphProjection = {
  tenant_id: string;
  version: number;
  nodes: Array<{
    node_id: string;
    lifecycle_state: "active" | "orphaned" | "tombstoned" | "frozen";
    cpu_cores: number;
    memory_gb: number;
    last_sequence_id: number;
  }>;
  edges: Array<{
    source_node_id: string;
    target_node_id: string;
    last_sequence_id: number;
  }>;
};

export type BackpressureTelemetry = {
  status: "healthy" | "overloaded";
  utilization_rho: number;
  arrival_rate_hz: number;
  service_rate_hz: number;
  raw_arrival_rate_hz: number;
  raw_service_rate_hz: number;
  raw_utilization_rho: number;
  ema_arrival_rate_hz: number;
  ema_service_rate_hz: number;
  ema_utilization_rho: number;
  limit_rho: number;
};

export type BlastRadiusNodeData = {
  label: string;
  centrality: number;
  rank: number;
  lifecycleState: string;
  cpuCores: number;
  memoryGb: number;
  lastSequenceId: number;
  adapterHealth?: AdapterHealth | null;
};

export type TelemetrySnapshot = {
  nodes: Node<BlastRadiusNodeData>[];
  edges: Edge[];
  backpressure: BackpressureTelemetry | null;
};

export type EventSeverity = "INFO" | "WARNING" | "CRITICAL";
export type EventSource = "PID" | "CIRCUIT_BREAKER" | "TOKEN_BUCKET" | "SYSTEM";
export type AdapterHealth = "UP" | "DEGRADED" | "DOWN";

export type TelemetryEvent = {
  id: string;
  timestamp: string;
  source: EventSource;
  severity: EventSeverity;
  type: string;
  message: string;
  metadata: Record<string, unknown>;
};
