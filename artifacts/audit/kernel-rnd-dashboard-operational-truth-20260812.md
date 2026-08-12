# Kernel-R&D dashboard — operational-truth audit

**Date**: 2026-08-12 · **Auditor**: `mainC` · **Lane**: `none` (read-only; no server started, no
inference, no compute) · **Assigned**: coordinator-agent `msg-20260811T234536Z-113`, relayed from
`inference` as an operator request.

**Method**: every finding below is derived by calling the hub's own contract functions directly with
substituted paths — not by reading the code and reasoning about it, and not by starting a server. The
live surface was left untouched.

---

## Verdict

**Three of the four plane-rule requirements PASS. One passes with a caveat. One NEW defect found, and
it is the same scar as incident 8 sitting one panel over — unfixed.**

| Plane-rule requirement | Verdict |
|---|---|
| Registry entry | **PASS** |
| Health probe | **PASS, with a caveat** |
| Freshness envelope | **PASS** — and it is the strongest one on the hub |
| No unregistered pages | **PASS** |
| *(operator ask)* Current production-kernel identity, wrong **loudly** on drift | **PARTIAL — see D-1** |

---

## The failure mode the brief asked me to hunt

> *"What does this page show when its producer is dead, and is that distinguishable from healthy?"*
> (incident 8: the loop died at trial 1302 and stayed dead ~23 h with every dashboard reporting
> active, because `/kernel` is absence-tolerant over a missing directory.)

**REPAIRED, and verified empirically.** Pointing `KERNEL_DASHBOARD_JSON` at a non-existent path:

```
artifact_present : False
runs             : None          <-- null, NOT []
pareto           : None
totals           : None
generated_at     : None
error            : "kernel dashboard contract not exported — the AutoKernel loop
                    (epyc-inference-research) has written nothing to <path>."
```

The distinction that matters is on the wire and is load-bearing: `[]` says *the producer reported and
there is nothing*; `null` says *no producer reported*. The old shell said `[]` for both, which is
exactly how a dead loop rendered as a clean, empty, trusted page. `static/kernel.html` then renders a
reporting banner carrying four independent facts a badge cannot (`reporting`, `content`,
`artifact_present`, `watchdog`), plus age, unreported sections, and the registry's declared
`absence_means` sentence — so a blank card cannot appear without a sentence saying what blank means.

**This is a genuinely good repair and I could not break it.**

---

## D-1 — NEW DEFECT: the production-kernel panel is absence-tolerant, quietly

**Severity: HIGH.** This is the one fact the operator specifically required to "be wrong loudly
rather than quietly if that drifts".

**Drift itself IS loud.** `_production_kernel_summary` shells `git symbolic-ref` + `rev-parse`
against the canonical checkout and compares to the attestation's `production_branch` /
`production_head`, live — not against a hardcoded string. A mismatch renders
`does not match attestation` in CSS class `fail`. Correct.

**But a MISSING attestation is silent.** Verified by calling the function with a non-existent
attestation path:

```
_production_kernel_summary(<missing>) -> {'available': False,
                                          'artifact_present': False,
                                          'evidence': '/nonexistent/ratify_v9.json',
                                          'error': None}      <-- no reason string
autokernel_current_state(...).production_kernel.available -> False, error -> None
```

and `static/kernel.html` renders that branch as:

```js
} else h+='<div class="muted">freeze attestation unavailable: '+esc(prod.error||"not found")+'</div>';
```

So when the attestation goes missing the page drops the entire production-kernel identity to **one
`muted` line reading "freeze attestation unavailable: not found"** — the same visual weight as an
informational aside, with no reason, no `alarm`/`absent` class, and no `absence_means` sentence.

**The asymmetry is the finding.** `_read_kernel_contract` handles precisely this case by
*synthesising* an explicit sentence when `err is None` (file simply absent rather than unparseable):

```python
if err is None:
    shell["error"] = ("kernel dashboard contract not exported — ... has written nothing to <path>.")
```

`_production_kernel_summary` passes `err` straight through, so `error` is `None` and even the muted
line can only say "not found". **The incident-8 scar fix was applied to the runs contract and not to
the attestation panel one function away.**

**Why this is not theoretical.** The kernel contract's own history is the precedent, documented in
`server.py`: its previous default path sat under `/mnt/raid0/llm/tmp`, the first entry of the
producer's `EPHEMERAL_ROOTS` — "one sweep from gone, leaving no event behind". An attestation file
that is moved, swept, or renamed produces exactly this state, and the page would stop asserting
production identity **without ever saying so loudly**. We froze v9 today; a surface that can quietly
stop asserting which kernel is production is the stale-pin class the auditor has been finding all
evening, one level up.

**Fix shape** (not applied — see below): mirror the synthesised-reason pattern into
`_production_kernel_summary`, and render the unavailable branch with the `absent`/`alarm` class plus
an `absence_means` sentence rather than `muted`.

---

## D-2 — health probe cannot distinguish "hub alive" from "kernel producer dead"

**Severity: LOW — recorded, not urgent.** The registry entry declares `"health_path": "/health"`, and
`/health` is documented in `server.py` as the **transport** probe: it answers only *this process is
serving* and returns `{"status": "ok"}`. A dead AutoKernel producer leaves `/health` green.

The hub does carry the right instrument — `/api/health`, the three-valued fold over
`dashboard/panels.py` (`ok` / `absent` / …) — but the registry points every consumer at the transport
probe. Anything reading the registry to decide "is Kernel-R&D healthy" gets the wrong answer by
construction.

Low severity because the `/kernel` page itself is honest (see above), so a human looking at the page
is not deceived; only an automated consumer of `registry.json` would be.

---

## What passes, with evidence

- **Registry entry** — present and complete:
  `{"id": "kernel", "title": "Kernel-R&D", "port": 8100, "path": "/kernel", "owner_repo":
  "epyc-root", "health_path": "/health", …}`.
- **Freshness envelope** — present and the richest on the hub: `reporting`, `content`,
  `artifact_present`, `watchdog{state,reason}`, `age_s`, `unreported[]`, `absence_means`, `producer`,
  `producer_repo`, `evidence`. Three section statuses, not two — `not_reported` is *a value rather
  than an omission*, which is the correct modelling of a dead owner.
- **No unregistered pages** — routes served (`/`, `/machine`, `/autopilot`, `/kernel`, `/bus`,
  `/benchmarks`) reconcile 1:1 against `registry.json`.
- **Contract-version handling** — an unlabelled document reads as v1 (legacy exports carry no
  `schema` key, and demanding the label would push a reader toward "render empty"); an *unknown*
  label is never coerced to v1. Both directions are the anti-absence-tolerance choice.

---

## Why no fixes were applied in this pass

The brief says report first unless trivial. D-1's server-side half **is** trivial (~4 lines mirroring
an existing pattern), and I still did not apply it: `dashboard/server.py` is one of the two paths
**on auditor hold** in `merge/origin-reconcile-20260811`, pending a ruling on which side is
authoritative. Editing it on `main` now would deepen the exact conflict being adjudicated, and a
four-line improvement is not worth complicating a merge that is otherwise down to two files.

**Both defects should be applied after that merge lands**, together, since they touch the same panel.
