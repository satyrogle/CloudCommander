"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, ActivitySquare } from "lucide-react";
import { fetchTelemetryEvents } from "../lib/api";
import type { EventSeverity, EventSource, TelemetryEvent } from "../lib/types";

type SourceFilter = "ALL" | EventSource;
type SeverityFilter = "ALL" | EventSeverity;

type Props = {
  tenantId: string;
};

const severityToClass: Record<EventSeverity, string> = {
  INFO: "info",
  WARNING: "warning",
  CRITICAL: "critical"
};

export function AlertTimeline({ tenantId }: Props) {
  const [events, setEvents] = useState<TelemetryEvent[]>([]);
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("ALL");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("ALL");
  const [isLoading, setIsLoading] = useState(true);
  const hasLoadedRef = useRef(false);

  useEffect(() => {
    let active = true;

    const sync = async () => {
      if (active && !hasLoadedRef.current) setIsLoading(true);
      const next = await fetchTelemetryEvents(tenantId, {
        source: sourceFilter,
        severity: severityFilter,
        limit: 50
      });
      if (active) {
        setEvents(next);
        setIsLoading(false);
        hasLoadedRef.current = true;
      }
    };

    void sync();
    const timerId = window.setInterval(() => {
      void sync();
    }, 5000);

    return () => {
      active = false;
      window.clearInterval(timerId);
    };
  }, [tenantId, sourceFilter, severityFilter]);

  return (
    <section className="timeline-panel">
      <header className="timeline-header">
        <div className="timeline-title">
          <AlertCircle size={16} />
          <span>Guardrail Alert Timeline</span>
        </div>
        <div className="timeline-filters">
          <select
            value={sourceFilter}
            onChange={(event) => setSourceFilter(event.target.value as SourceFilter)}
            aria-label="Filter by event source"
          >
            <option value="ALL">All Sources</option>
            <option value="PID">PID Controller</option>
            <option value="CIRCUIT_BREAKER">Circuit Breaker</option>
            <option value="TOKEN_BUCKET">Token Bucket</option>
            <option value="SYSTEM">System</option>
          </select>

          <select
            value={severityFilter}
            onChange={(event) => setSeverityFilter(event.target.value as SeverityFilter)}
            aria-label="Filter by event severity"
          >
            <option value="ALL">All Severities</option>
            <option value="INFO">Info</option>
            <option value="WARNING">Warning</option>
            <option value="CRITICAL">Critical</option>
          </select>
        </div>
      </header>

      <div className="timeline-body">
        {isLoading ? (
          <div className="timeline-empty">Loading telemetry...</div>
        ) : events.length === 0 ? (
          <div className="timeline-empty">No events found for this filter.</div>
        ) : (
          events.map((event) => (
            <article
              key={event.id}
              className={`timeline-event ${severityToClass[event.severity]}`}
            >
              <div className="timeline-event-head">
                <span className="timeline-event-type">
                  {event.source} :: {event.type}
                </span>
                <span className="timeline-event-time">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <p className="timeline-event-message">{event.message}</p>
            </article>
          ))
        )}
      </div>
      <footer className="timeline-footer">
        <ActivitySquare size={14} />
        <span>Polling every 5 seconds</span>
      </footer>
    </section>
  );
}
