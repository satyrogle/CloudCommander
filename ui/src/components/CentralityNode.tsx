"use client";

import { Handle, Position, type NodeProps } from "reactflow";
import type { BlastRadiusNodeData } from "../lib/types";

export function CentralityNode({ data, selected }: NodeProps<BlastRadiusNodeData>) {
  const centrality = Math.max(0, Math.min(1, data.centrality));
  const diameter = 68 + centrality * 52;
  const danger = centrality >= 0.8;
  const warning = centrality >= 0.55;
  const status = data.adapterHealth;

  const background = danger
    ? "rgba(177, 38, 55, 0.94)"
    : warning
      ? "rgba(176, 132, 39, 0.94)"
      : "rgba(21, 32, 42, 0.94)";

  return (
    <div
      className={`centrality-node ${selected ? "selected" : ""}`}
      style={{
        width: diameter,
        minHeight: diameter,
        borderColor: danger ? "#ff6b7a" : warning ? "#f2c14e" : "#6ee7b7",
        background
      }}
      title={`Rank ${data.rank}. Centrality ${centrality.toFixed(2)}`}
    >
      {status ? (
        <span
          className={`health-dot ${status.toLowerCase()}`}
          title={`Adapter health: ${status}`}
          aria-label={`Adapter health: ${status}`}
        />
      ) : null}
      <Handle type="target" position={Position.Top} />
      <div className="node-rank">#{data.rank}</div>
      <div className="node-label">{data.label}</div>
      <div className="node-score">{centrality.toFixed(2)}</div>
      <div className="node-state">{data.lifecycleState}</div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
