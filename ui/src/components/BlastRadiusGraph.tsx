"use client";

import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node
} from "reactflow";
import "reactflow/dist/style.css";
import { CentralityNode } from "./CentralityNode";
import type { BlastRadiusNodeData } from "../lib/types";

const nodeTypes = {
  centralityNode: CentralityNode
};

type Props = {
  nodes: Node<BlastRadiusNodeData>[];
  edges: Edge[];
};

export function BlastRadiusGraph({ nodes, edges }: Props) {
  return (
    <div className="graph-surface">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.22 }}
        minZoom={0.2}
        maxZoom={1.8}
      >
        <Background color="#26313b" gap={24} />
        <MiniMap
          pannable
          zoomable
          nodeColor={(node) => {
            const centrality = (node.data as BlastRadiusNodeData).centrality;
            if (centrality >= 0.8) return "#ff6b7a";
            if (centrality >= 0.55) return "#f2c14e";
            return "#6ee7b7";
          }}
        />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
