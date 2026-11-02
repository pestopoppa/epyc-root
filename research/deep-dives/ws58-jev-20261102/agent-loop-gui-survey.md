# Loop-flow GUI survey (ws58-jev, 2026-11-02)
Clones: /mnt/raid0/llm/tmp/dive-ws58-jev-20261102/gui/src/<name> (depth 1). SHAs are HEAD at clone time.

## 1. Candidates
| Source | URL | License | HEAD sha | Gives | Fit for static hub page |
|---|---|---|---|---|---|
| LangGraph (OSS lib) | github.com/langchain-ai/langgraph | MIT | e5c961d7 | Python graph runtime; checkpoints, `get_state_history` (pregel/main.py:1510) and `update_state` (:2613) = time-travel/fork. Mermaid export. NO editor. Studio is "LangSmith Studio" (README:57), a hosted LangSmith product, not in this repo | Library only; steal the checkpoint/fork semantics, not the UI. Studio = not OSS, reject |
| XState | github.com/statelyai/xstate | MIT | 060cd633 | Statechart runtime + JSON machine config; typed spec; events/transitions/guards | Spec format candidate; JS only; Python side would need own interpreter |
| @statelyai/inspect | github.com/statelyai/inspect | MIT | 8624f3bf | Live inspector, state + sequence diagrams of events | Default inspector UI URL is https://stately.ai/inspect (README:98): hosted, so not local-only unless self-host option is verified. Package MIT, UI dependency external. Viewer only, no replay of saved journals |
| xyflow / React Flow | github.com/xyflow/xyflow | MIT | d4bc936e | Node/edge canvas editor, drag, custom nodes, controlled state (round-trip is your code) | Best editor substrate; needs React + bundle (vendor a built bundle, no CDN) |
| Rete.js | github.com/retejs/rete | MIT | 2aae1995 | Node-editor + dataflow/control-flow engine, plugin-based | Heavier, dataflow-oriented; no advantage over xyflow here |
| Node-RED | github.com/node-red/node-red | Apache-2.0 | 22d019c4 | Full flow editor + runtime, flows are JSON | Own server/runtime (Node); wrong plane (not stdlib hub); loop semantics (stop reasons) not native |
| Langflow | github.com/langflow-ai/langflow | MIT | b5c54a64 | LLM flow builder, JSON flows | Own app stack; flows are LLM-pipeline DAGs, not loops with stop reasons. Reject for embedding |
| Flowise | github.com/FlowiseAI/Flowise | Apache-2.0 with carve-out (enterprise dirs under packages/server/src/enterprise are commercial; LICENSE.md) | 9291856d | Chatflow builder | Same as Langflow; license carve-out; reject |
| Burr (Apache) | github.com/apache/burr | Apache-2.0 | 0512d8a0 | Python state machine (actions/transitions/conditions), `visualize` to graphviz (core/application.py:2021), tracking server+React UI (telemetry/ui/src), fork_parent_pointer = replay/fork from a saved state (application.py:857,2082) | Closest conceptual match (closest to "states, transitions, saved state replay"). UI is a full app (own server); not embeddable, but its data model (per-step state snapshots, parent pointer) is the template to copy |
| Mermaid stateDiagram | github.com/mermaid-js/mermaid | MIT | 370c4af5 | Text to SVG state diagram; generated view | Single vendored JS file, trivial for static page; view-only, no click-to-edit round trip |

Not cloned (named, unverified): d2/ELK/dagre layout libs (layout only); Temporal/Restate UIs (workflow replay, server-heavy).
Note: Studio verdict is from README text only; I did not enumerate LangSmith licensing further.

## 2. Hub findings (worktree /mnt/raid0/llm/worktrees/intake-ws58-jev-20261102)
- Plane rule: data with the producing subsystem, pages/nav/registry on the :8100 stdlib hub; "Adding a dashboard = three things" (registry entry, health probe, freshness envelope); no unregistered pages: dashboard/README.md:30-80.
- Hub is stdlib-only, static HTML re-read per request, route table maps path to file: dashboard/server.py:11-29, 142-160, 2002-2004 (`/cockpit`, `/loop`).
- Static pages present: autopilot, benchmarks, bus, cockpit, gpu-window, handoffs, loop, machine, nav.js (dashboard/static/). Registry: dashboard/registry.json (entries machine, autopilot, cockpit, gpu-window, handoffs, autokernel-loop, bus ...).
- Existing graph rendering: hand-rolled inline SVG provenance graph in dashboard/static/cockpit.html:61-62, 112-119, 352-404 (filters by status, legend, node detail). No library, no CDN: precedent for dependency-free rendering.
- Existing canvas feature: yes. /workspace/repos/epyc-orchestrator/src/canvas_export.py (689 lines; JSON Canvas export of HypothesisGraph/FailureGraph, header lines 1-3, canvas dir under log_dir/canvases :30-41) and src/canvas_import.py (503 lines; `parse_canvas` :116, `compute_canvas_diff` :145, `extract_constraints` :260, `apply_constraints_to_plan` :394, `validate_canvas_schema` :438). MCP tools export_reasoning_canvas / import_canvas_edits: src/mcp_server.py:232-268; tests tests/test_canvas_export.py, test_canvas_import.py; doc docs/chapters/08-graph-reasoning.md. This is already an export -> human edit (Obsidian-style JSON Canvas) -> diff -> constraints round trip. Reuse its diff/validate pattern for loop spec edits.

## 3. Recommended minimal build path
1. Typed loop spec: JSON (schema-validated, e.g. JSON Schema + pydantic on the Python side) with `states[]`, `transitions[{from,to,guard,threshold_ref}]`, `stop_reasons[]`, `thresholds{name:{value,unit,direction}}`. Keep XState-like shape (states/on/guard) for familiarity, but own the schema; do not adopt a runtime.
2. Generated view (viewer-only, phase A): Python emits Mermaid `stateDiagram-v2` from spec; new hub page vendors one mermaid.min.js (pinned, no CDN) or, to match cockpit.html precedent, a small inline-SVG renderer. Needs registry entry + probe + static-snapshot freshness envelope per README.
3. Replay stepper (phase B, still read-only): copy Burr's model, per-step state snapshots with parent pointer. Replayer is a pure function (spec, saved journal input, step n) -> (state, fired transition, stop reason); page scrubs steps and highlights the edge. Journals read from producer's data plane (orchestrator API), not the hub.
4. Round-trip edits (phase C): start with threshold/field edits only (form -> JSON patch -> validate -> write spec via the owning session), mirroring canvas_import's diff + validate_canvas_schema. Graph-structure editing (add/remove states/edges) via xyflow only after A/B proven; export back through the same schema validator. Alternatively reuse JSON Canvas as the edit surface (already supported by the orchestrator, editable in Obsidian) with a spec<->canvas adapter, zero new UI.
Decision gates: hub stays stdlib (vendor built JS, no node server); edits never write directly from the page, only propose a patch.
