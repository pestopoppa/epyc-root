# 2026-07-05 — Autopilot dashboard topology-panel explainer flicker fix

## Problem
The explainer paragraph in the topology panel of the autopilot dashboard ("Each
role row's ▸ expands to show its live activity. Three signals in priority
order…") flickered in and out on every refresh, causing visible page flicker.

## Root cause
Not a DOM rebuild. The explainer (`#inflight-explainer`) is a static sibling of
`#topology-strip`, so `renderTopologyStrip()` never touches it. Instead its
visibility was toggled every poll cycle inside `updateTasks(snap)`:

```javascript
explainer.style.display = (slotsActive > inflight.length
    || (slotsActive > 0 && inflight.length === 0)) ? 'block' : 'none';
```

`slotsActive` (summed from `snap.activity[*].n_active`) and `inflight.length`
(`snap.in_flight_tasks`) come from different sources that update at different
cadences. The same-instant comparison therefore thrashed true/false across
successive snapshots, blinking the paragraph `block`/`none` each cycle.

## Change
| Repo | File | Change |
|------|------|--------|
| epyc-orchestrator | `src/api/routes/dashboard.html` (~line 1939) | Set `explainer.style.display = 'block'` unconditionally; removed the oscillating count comparison. Added comment documenting why. |

Initial markup keeps `display:none`, so the legend stays hidden until the first
snapshot then shows steadily — no blinking. Client-side template only; no build
step. Effect on next page load (hard-refresh to bypass cache).

## Result
Flicker eliminated. Legend is a 10px dim static element, so always-visible has
near-zero cost and removes the thrash entirely (chosen over a debounce/hysteresis
approach for simplicity/robustness).

## Deferred
None.
