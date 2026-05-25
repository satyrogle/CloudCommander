import { forceCenter, forceLink, forceManyBody, forceSimulation } from "d3-force";
import type { Edge, Node } from "reactflow";
import type { BlastRadiusNodeData } from "./types";

type SimNode = {
  id: string;
  x?: number;
  y?: number;
};

export async function calculatePhysicsLayout(
  rawNodes: Node<BlastRadiusNodeData>[],
  rawEdges: Edge[]
): Promise<Node<BlastRadiusNodeData>[]> {
  const nodes: SimNode[] = rawNodes.map((node) => ({ id: node.id }));
  const links = rawEdges.map((edge) => ({
    source: edge.source,
    target: edge.target
  }));

  const simulation = forceSimulation(nodes)
    .force("link", forceLink<SimNode, { source: string; target: string }>(links).id((node) => node.id).distance(170))
    .force("charge", forceManyBody().strength(-520))
    .force("center", forceCenter(0, 0));

  simulation.tick(300);
  simulation.stop();

  const positionById = new Map(nodes.map((node) => [node.id, node]));

  return rawNodes.map((node) => {
    const position = positionById.get(node.id);
    return {
      ...node,
      position: {
        x: Math.round(position?.x ?? 0),
        y: Math.round(position?.y ?? 0)
      }
    };
  });
}
