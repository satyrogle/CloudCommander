import { assign, fromPromise, setup } from "xstate";
import { fetchTelemetrySnapshot } from "../lib/api";
import { calculatePhysicsLayout } from "../lib/layout";
import type { BackpressureTelemetry, BlastRadiusNodeData } from "../lib/types";
import type { Edge, Node } from "reactflow";

type TelemetryContext = {
  tenantId: string;
  nodes: Node<BlastRadiusNodeData>[];
  edges: Edge[];
  backpressure: BackpressureTelemetry | null;
  pollInterval: number;
  errorMessage: string | null;
};

type TelemetryEvent =
  | { type: "START_POLLING" }
  | { type: "RETRY" }
  | { type: "SET_TENANT"; tenantId: string };

type TelemetryInput = {
  tenantId: string;
  pollInterval?: number;
};

export const telemetryMachine = setup({
  types: {
    context: {} as TelemetryContext,
    events: {} as TelemetryEvent,
    input: {} as TelemetryInput
  },
  actors: {
    fetchCentralityTelemetry: fromPromise(
      async ({ input }: { input: { tenantId: string } }) => {
        return fetchTelemetrySnapshot(input.tenantId);
      }
    ),
    runD3ForceSimulation: fromPromise(
      async ({
        input
      }: {
        input: { nodes: Node<BlastRadiusNodeData>[]; edges: Edge[] };
      }) => {
        return calculatePhysicsLayout(input.nodes, input.edges);
      }
    )
  },
  actions: {
    assignTenant: assign({
      tenantId: ({ event }) =>
        event.type === "SET_TENANT" ? event.tenantId : ""
    }),
    assignTelemetryData: assign({
      nodes: ({ event }) => {
        const output = (event as { output?: Awaited<ReturnType<typeof fetchTelemetrySnapshot>> }).output;
        return output?.nodes ?? [];
      },
      edges: ({ event }) => {
        const output = (event as { output?: Awaited<ReturnType<typeof fetchTelemetrySnapshot>> }).output;
        return output?.edges ?? [];
      },
      backpressure: ({ event }) => {
        const output = (event as { output?: Awaited<ReturnType<typeof fetchTelemetrySnapshot>> }).output;
        return output?.backpressure ?? null;
      },
      errorMessage: () => null
    }),
    assignLayoutCoordinates: assign({
      nodes: ({ event }) => {
        const output = (event as { output?: Node<BlastRadiusNodeData>[] }).output;
        return output ?? [];
      }
    }),
    assignError: assign({
      errorMessage: ({ event }) => {
        const error = (event as { error?: unknown }).error;
        return error ? String(error) : "Telemetry update failed";
      }
    })
  },
  delays: {
    pollDelay: ({ context }) => context.pollInterval
  }
}).createMachine({
  id: "blastRadiusTelemetry",
  initial: "idle",
  context: ({ input }) => ({
    tenantId: input.tenantId,
    nodes: [],
    edges: [],
    backpressure: null,
    pollInterval: input.pollInterval ?? 5000,
    errorMessage: null
  }),
  states: {
    idle: {
      on: {
        START_POLLING: "fetching",
        SET_TENANT: {
          actions: "assignTenant",
          target: "fetching"
        }
      }
    },
    fetching: {
      invoke: {
        id: "fetchCentralityTelemetry",
        src: "fetchCentralityTelemetry",
        input: ({ context }) => ({ tenantId: context.tenantId }),
        onDone: {
          target: "calculatingLayout",
          actions: "assignTelemetryData"
        },
        onError: {
          target: "error",
          actions: "assignError"
        }
      },
      on: {
        SET_TENANT: {
          actions: "assignTenant",
          target: "fetching",
          reenter: true
        }
      }
    },
    calculatingLayout: {
      invoke: {
        id: "runD3ForceSimulation",
        src: "runD3ForceSimulation",
        input: ({ context }) => ({
          nodes: context.nodes,
          edges: context.edges
        }),
        onDone: {
          target: "waiting",
          actions: "assignLayoutCoordinates"
        },
        onError: {
          target: "waiting"
        }
      }
    },
    waiting: {
      after: {
        pollDelay: "fetching"
      },
      on: {
        SET_TENANT: {
          actions: "assignTenant",
          target: "fetching"
        }
      }
    },
    error: {
      on: {
        RETRY: "fetching",
        SET_TENANT: {
          actions: "assignTenant",
          target: "fetching"
        }
      }
    }
  }
});
