import type {
  BackpressureTelemetry,
  BlastRadiusNodeData,
  CentralityNode,
  ServiceGraphProjection,
  TelemetrySnapshot
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

const fallbackBackpressure: BackpressureTelemetry = {
  status: "healthy",
  utilization_rho: 0,
  arrival_rate_hz: 0,
  service_rate_hz: 0,
  raw_arrival_rate_hz: 0,
  raw_service_rate_hz: 0,
  raw_utilization_rho: 0,
  ema_arrival_rate_hz: 0,
  ema_service_rate_hz: 0,
  ema_utilization_rho: 0,
  limit_rho: 0.95
};

async function getJson<T>(path: string, tenantId: string): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 1800);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "X-Tenant-Id": tenantId
    },
    cache: "no-store",
    signal: controller.signal
  }).finally(() => window.clearTimeout(timeout));

  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function createFallbackSnapshot(): TelemetrySnapshot {
  const ids = [
    "api-gateway",
    "scheduler",
    "worker",
    "postgres",
    "cloud-adapter",
    "telemetry"
  ];
  const centrality = new Map([
    ["postgres", { score: 1, rank: 1 }],
    ["worker", { score: 0.78, rank: 2 }],
    ["cloud-adapter", { score: 0.64, rank: 3 }],
    ["api-gateway", { score: 0.4, rank: 4 }],
    ["scheduler", { score: 0.28, rank: 5 }],
    ["telemetry", { score: 0.18, rank: 6 }]
  ]);

  const nodes = ids.map((id) => ({
    id,
    type: "centralityNode",
    position: { x: 0, y: 0 },
    data: {
      label: id,
      centrality: centrality.get(id)?.score ?? 0.1,
      rank: centrality.get(id)?.rank ?? ids.length,
      lifecycleState: "active",
      cpuCores: id === "postgres" ? 8 : 2,
      memoryGb: id === "postgres" ? 32 : 8,
      lastSequenceId: 0
    } satisfies BlastRadiusNodeData
  }));

  const edges = [
    ["api-gateway", "postgres"],
    ["scheduler", "worker"],
    ["worker", "postgres"],
    ["worker", "cloud-adapter"],
    ["telemetry", "postgres"]
  ].map(([source, target]) => ({
    id: `${source}-${target}`,
    source,
    target,
    animated: false,
    type: "smoothstep"
  }));

  return { nodes, edges, backpressure: fallbackBackpressure };
}

export async function fetchTelemetrySnapshot(tenantId: string): Promise<TelemetrySnapshot> {
  if (!tenantId.trim()) {
    return createFallbackSnapshot();
  }

  try {
    const [centrality, graph, backpressure] = await Promise.all([
      getJson<CentralityNode[]>("/api/v1/telemetry/graph/centrality", tenantId),
      getJson<ServiceGraphProjection>("/api/v1/projections/service-graph", tenantId),
      getJson<BackpressureTelemetry>("/api/v1/telemetry/system/backpressure", tenantId)
    ]);

    const centralityByNode = new Map(
      centrality.map((node) => [node.node_id, node])
    );
    const projectionByNode = new Map(
      graph.nodes.map((node) => [node.node_id, node])
    );
    const nodeIds = new Set<string>();
    graph.nodes.forEach((node) => nodeIds.add(node.node_id));
    graph.edges.forEach((edge) => {
      nodeIds.add(edge.source_node_id);
      nodeIds.add(edge.target_node_id);
    });
    centrality.forEach((node) => nodeIds.add(node.node_id));

    const nodes = Array.from(nodeIds).map((nodeId) => {
      const projection = projectionByNode.get(nodeId);
      const central = centralityByNode.get(nodeId);
      return {
        id: nodeId,
        type: "centralityNode",
        position: { x: 0, y: 0 },
        data: {
          label: nodeId.slice(0, 8),
          centrality: central?.centrality_score ?? 0.1,
          rank: central?.rank ?? nodeIds.size,
          lifecycleState: projection?.lifecycle_state ?? "edge-only",
          cpuCores: projection?.cpu_cores ?? 0,
          memoryGb: projection?.memory_gb ?? 0,
          lastSequenceId: projection?.last_sequence_id ?? 0
        } satisfies BlastRadiusNodeData
      };
    });

    const edges = graph.edges.map((edge) => ({
      id: `${edge.source_node_id}-${edge.target_node_id}`,
      source: edge.source_node_id,
      target: edge.target_node_id,
      type: "smoothstep",
      animated: false
    }));

    return { nodes, edges, backpressure };
  } catch {
    return createFallbackSnapshot();
  }
}
