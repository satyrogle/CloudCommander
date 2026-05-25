"use client";

import { Activity, Gauge } from "lucide-react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { BackpressureTelemetry } from "../lib/types";

type Props = {
  backpressure: BackpressureTelemetry | null;
  history: Array<{
    index: number;
    raw: number;
    ema: number;
  }>;
};

export function BackpressurePanel({ backpressure, history }: Props) {
  const raw = backpressure?.raw_utilization_rho ?? 0;
  const ema = backpressure?.ema_utilization_rho ?? 0;
  const overloaded = backpressure?.status === "overloaded" || raw >= (backpressure?.limit_rho ?? 0.95);

  return (
    <aside className="telemetry-panel">
      <div className="panel-title">
        <Gauge size={18} />
        <span>Backpressure</span>
      </div>

      <div className={`status-strip ${overloaded ? "danger" : ema >= 0.7 ? "warn" : "ok"}`}>
        <span>{overloaded ? "Saturated" : ema >= 0.7 ? "Recovering" : "Healthy"}</span>
        <strong>{raw.toFixed(2)}</strong>
      </div>

      <div className="metrics-grid">
        <div>
          <span>Raw rho</span>
          <strong>{raw.toFixed(3)}</strong>
        </div>
        <div>
          <span>EMA rho</span>
          <strong>{ema.toFixed(3)}</strong>
        </div>
        <div>
          <span>Arrivals</span>
          <strong>{(backpressure?.raw_arrival_rate_hz ?? 0).toFixed(2)}/s</strong>
        </div>
        <div>
          <span>Service</span>
          <strong>{(backpressure?.raw_service_rate_hz ?? 0).toFixed(2)}/s</strong>
        </div>
      </div>

      <div className="chart-shell">
        <div className="chart-heading">
          <Activity size={16} />
          <span>M/M/1 Saturation</span>
        </div>
        <ResponsiveContainer width="100%" height={170}>
          <AreaChart data={history}>
            <XAxis dataKey="index" hide />
            <YAxis domain={[0, 1.2]} width={32} tick={{ fill: "#8a98a8", fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: "#111820",
                border: "1px solid #2d3a46",
                borderRadius: 4,
                color: "#e8eef5"
              }}
            />
            <Area type="monotone" dataKey="raw" stroke="#ff6b7a" fill="#ff6b7a" fillOpacity={0.16} dot={false} />
            <Area type="monotone" dataKey="ema" stroke="#6ee7b7" fill="#6ee7b7" fillOpacity={0.14} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </aside>
  );
}
