"use client";

import { useEffect, useMemo, useState } from "react";
import { useMachine } from "@xstate/react";
import { Network, RefreshCw, ShieldAlert } from "lucide-react";
import { BlastRadiusGraph } from "../components/BlastRadiusGraph";
import { BackpressurePanel } from "../components/BackpressurePanel";
import { AlertTimeline } from "../components/AlertTimeline";
import { telemetryMachine } from "../machines/telemetryMachine";

const defaultTenantId = "00000000-0000-0000-0000-000000000000";

export default function DashboardPage() {
  const [tenantInput, setTenantInput] = useState(defaultTenantId);
  const [snapshot, send] = useMachine(telemetryMachine, {
    input: {
      tenantId: defaultTenantId,
      pollInterval: 5000
    }
  });
  const [history, setHistory] = useState<Array<{ index: number; raw: number; ema: number }>>([]);

  useEffect(() => {
    send({ type: "START_POLLING" });
  }, [send]);

  useEffect(() => {
    const backpressure = snapshot.context.backpressure;
    if (!backpressure) return;

    // Keep a compact rolling chart history derived from the polling machine.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHistory((current) => {
      const next = [
        ...current,
        {
          index: current.length,
          raw: Number(backpressure.raw_utilization_rho.toFixed(4)),
          ema: Number(backpressure.ema_utilization_rho.toFixed(4))
        }
      ];
      return next.slice(-40);
    });
  }, [snapshot.context.backpressure]);

  const highBlastRadiusCount = useMemo(
    () => snapshot.context.nodes.filter((node) => node.data.centrality >= 0.8).length,
    [snapshot.context.nodes]
  );

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            <Network size={22} />
          </div>
          <div>
            <h1>CloudCommander</h1>
            <span>Blast-radius telemetry</span>
          </div>
        </div>

        <div className="tenant-control">
          <label htmlFor="tenant">Tenant</label>
          <input
            id="tenant"
            value={tenantInput}
            onChange={(event) => setTenantInput(event.target.value)}
            onBlur={() => send({ type: "SET_TENANT", tenantId: tenantInput })}
          />
          <button
            type="button"
            title="Refresh telemetry"
            onClick={() => send({ type: "SET_TENANT", tenantId: tenantInput })}
          >
            <RefreshCw size={17} />
          </button>
        </div>
      </header>

      <section className="status-band">
        <div>
          <span>Polling state</span>
          <strong>{String(snapshot.value)}</strong>
        </div>
        <div>
          <span>Nodes</span>
          <strong>{snapshot.context.nodes.length}</strong>
        </div>
        <div>
          <span>Edges</span>
          <strong>{snapshot.context.edges.length}</strong>
        </div>
        <div className={highBlastRadiusCount > 0 ? "attention" : ""}>
          <span>High blast radius</span>
          <strong>{highBlastRadiusCount}</strong>
        </div>
      </section>

      <section className="workspace">
        <div className="graph-region">
          <div className="section-heading">
            <ShieldAlert size={18} />
            <span>Dependency Influence Map</span>
          </div>
          <BlastRadiusGraph nodes={snapshot.context.nodes} edges={snapshot.context.edges} />
        </div>
        <div className="telemetry-rail">
          <BackpressurePanel
            backpressure={snapshot.context.backpressure}
            history={history}
          />
          <AlertTimeline tenantId={tenantInput} />
        </div>
      </section>
    </main>
  );
}
