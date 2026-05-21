# Cloud Map Layout Spec (React + Cytoscape.js)

## 1. Global Layout

### Header (Top, 48px)
- Tenant selector.
- Global environment status indicator (`Green`, `Yellow`, `Red`) derived from guardrail alert severity.
- Mode toggle: `Read-Only` vs `Command` mode.

### Viewport (Center, ~70% width)
- Primary DAG visualization area.
- Pan/zoom controls with fit-to-graph action.

### Inspector Panel (Right, ~30% width)
- Contextual detail for selected node or edge.
- Includes state detail, command form, and local event stream.

## 2. Viewport (Cytoscape Graph)

### Nodes
- Geometric shape indicates resource type (example: hexagon for ECS task/service).
- Fill color indicates health state.
- Border stroke indicates lifecycle state:
  - `active`: solid border
  - `orphaned`: dotted border
  - `tombstoned`: dashed border

### Edges
- Directed arrows indicate dependency flow.
- Invalid proposed edges should render in warning style prior to submission.

### Interaction
- Clicking a node locks Inspector Panel context to that resource.
- Hover displays lightweight tooltip (name, health, version).
- Multi-select (shift+click) enabled for future batch intent operations.

## 3. Inspector Panel

### State View
- Current allocated CPU, memory, replica count.
- Uptime/health summary.
- Aggregate version ID and latest sequence reference.

### Command Form
- Editable scaling fields.
- Mandatory `Reason Code` dropdown.
- `Submit Intent` action button.
- Inline display of required idempotency key and expected version behavior.

### Local Event Stream
- Mini timeline of the latest 5 events for selected aggregate ID.
- Includes both command-accepted and reconciler-result events.
- Displays status badges: `pending`, `applied`, `failed`.


## 4. Projection Lag and Command UX

- On submit, selected node enters `Syncing` state with spinner and mutation controls disabled for that node.
- Panel shows `Pending Intent` row with idempotency key and expected-version used.
- If command conflicts (`409`), panel prompts rebase using latest version before resubmit.
- If command exceeds lag SLO, show non-blocking warning and refresh option.
- Frozen nodes render with red border and disabled mutation controls; inspector shows drift-resolution actions only.
- No per-slider-step network dispatch; only explicit submit generates a command.
