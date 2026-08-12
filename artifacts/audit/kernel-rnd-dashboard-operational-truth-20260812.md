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

---

# Addendum — AutoKernel state reconciliation (second pass, 2026-08-12 00:40Z)

Requested by `inference` (`msg-20260812T002331Z` / `-002354Z`): reconcile the Kernel-R&D surface
against the latest durable receipts and frozen-v9 identity. **Read-only throughout** —
`dashboard/server.py` is on auditor hold, no server started, no inference, lane `none`.

## PASS — production-kernel identity is correct and attested

Read live from `autokernel_current_state()`:

```
branch  production-consolidated-v9
head    0db32c06e3e550065b78311a6031ef3dd2c4f27c
version 10125 (0db32c06e)
status  production_promoted_frozen · frozen: True · ratified 2026-08-11T01:16:00Z
checkout.branch/head identical → MATCHES ATTESTATION: True
```

## PASS — the three auto-selected receipts are present and correctly authority-labelled

| receipt | state | authority |
|---|---|---|
| `inf03-mi210-controller-ab-v1` | **refused**, 6/8 ready, missing `evoengineer` + `argus` | `diagnostic_only` |
| `…-available-source-six-arm-v1` | **ready**, 6/6 | `availability_conditioned_diagnostic_only` |
| `inf03-actor-critic-real-smoke-v6` | **complete**, `rankable: false`, `matched_campaign_implied: false` | `diagnostic_only` |

`promotion_claim: false`. All three match what `inference` reported at 23:52Z.

## The five requested fields are ABSENT, not stale — and the cause is not what it looks like

Probed the entire `current_state` document (2,496 chars) for each:

| requested | present anywhere |
|---|---|
| hardened instrument `a4cb04ca…` | **no** |
| GPU replay 20/20 positive / `NOT_REPRODUCED` / 2% floor / median `1.2442%` | **no** |
| fresh-v9 controls · CPU IQK · matched archive (pending markers) | **no** |
| AutoKernel-relevant ROCm dependencies | **no** |

**These are not stale values needing correction. They are fields that do not exist** — so the repair
is additive, not a value fix. Two independent causes, and the second is the actionable one:

**(a) The exported contract does not exist at all.** `KERNEL_DASHBOARD_JSON` points at
`/mnt/raid0/llm/autokernel/surface/kernel_dashboard.json` — **that file, and the `surface/` directory
itself, are absent from disk**; a filesystem-wide search finds no `kernel_dashboard.json` anywhere.
So every `runs` / `pareto` / `totals` figure on `/kernel` is currently the ABSENT shell. The scar fix
is doing its job (nulls + explicit sentence, not a clean empty page), but **the page today has two
producers and only one of them is alive.**

**(b) The receipts ARE on disk; the selector cannot see them.** `autokernel_current_state()` resolves
exactly **three hard-coded receipt filenames** (`full-eight-arm-refusal.json`,
`available-source-six-arm.json`, and the smoke receipt). There are **129 probe directories**, and the
three newest — dated today — are precisely the ones `inference` asked for:

```
ak-v9-final-preflight-20260812-r1
ak-instrument-smoke-a4cb04ca-20260812     <-- the hardened instrument a4cb04ca
ak-gpu-prefetch-v9-20260812-r1            <-- the GPU replay
```

The evidence is durable and already written. The dashboard is blind to it because its selector is a
fixed allowlist rather than a schema match.

## Smallest post-hold repair

1. **Extend the selector, do not add a panel.** Add the new receipt filenames/schemas to
   `autokernel_current_state()` alongside the existing three. That surfaces the instrument, the GPU
   replay and the v9 preflight from receipts that already exist — no producer change needed.
2. **Render the replay honestly**: 20/20 positive *and* `NOT_REPRODUCED` at the 2% floor (median
   1.2442%) must appear together. A 20/20 shown without the floor verdict reads as a pass.
3. **Land D-1 in the same change** — the missing-attestation branch must become a loud `alarm`, not a
   `muted` line — since both touch the same panel.
4. **Producer-side, separately**: either restore the `kernel_dashboard.json` export or make its
   absence a first-class alarm rather than only a banner state. Right now `current_state` can render
   fully healthy while the entire runs/pareto contract is missing, and **that combination is the
   incident-8 shape at the page level rather than the field level.**

---

# Implementation follow-up — post-hold reconciliation (2026-08-12 01:18Z)

The auditor hold is no longer active: the merge worktree has no dashboard conflict, the selected
dashboard commits are on `main`, and the four touched dashboard paths were clean with no live file
claim. The additive repair was implemented on isolated branch
`codex/kernel-rnd-dashboard-audit-20260812`; no inference or kernel-tree write occurred.

## Live-state correction since the addendum

The runtime producer is no longer absent. A terminal campaign export now exists at
`/mnt/raid0/llm/autokernel/surface/kernel_dashboard.json` and live `/api/kernel` reports:

- campaign `ak-iqk-v9-20260811`, state `preflight_refused`;
- the explicit blocker is the ratified one-week uptime ceiling (13.47 days), routed to an operator
  reboot decision rather than hidden as idle;
- freshness `fresh`, with 4/7 v2 sections reported and the three unreported owners named.

This closes the addendum's producer-absence observation. It does **not** turn the terminal refusal
into success or authorize a reboot.

## Implemented

| Finding | Disposition |
|---|---|
| D-1 missing production attestation rendered quietly | **FIXED** — a missing attestation now renders `ATTESTATION UNAVAILABLE` in the failure class and says production identity is unasserted. |
| Hardened v9 instrument and controls absent | **FIXED** — schema-selected preflight plus attested control summary show 8/8 preflight checks, 5/5 controls, `MAY RANK`, instrument `a4cb04ca…`, direct production-v9 anchor match, B_min 10 and 3.5785% noise floor. |
| ROCm replay absent / positivity could be misread | **FIXED** — one card keeps `20/20 positive`, median `+1.2442%`, the `2.00%` floor and `NOT_REPRODUCED` together; it also reports ROCm0 sampling (2,544 samples) and claim release. |
| Activity card trailed isolated-worktree commits | **FIXED** — committed AutoKernel activity is selected across local refs and explicitly labelled as activity, not merge/deploy state. It now sees the `900cb5c6` matched-archive builder and its immediate predecessors. |

The schema-less historical `summary.json` control artifact is not trusted by filename alone: the
reader requires the control/calibration/provenance shape plus a sibling
`epyc.autokernel.control_composition_attestation.v1` with the same campaign id. The GPU replay and
preflight are selected by exact schema.

## Validation

- `python3 -m unittest discover -s tests -p 'test_dashboard*.py'` — **182 passed**.
- `tests/test_dashboard_static_js.py` is included in that run and parses every static dashboard's
  JavaScript.
- A supervised temporary hub on `127.0.0.1:18100` returned the fresh campaign blocker plus the new
  controls/preflight/replay projections; the exact captured PID was terminated and verified gone.

## Remaining gaps (not silently promoted to dashboard facts)

- **D-2 remains LOW**: the registry's `/health` target is transport-only. Pointing it naively at the
  global `/api/health` fold would recurse through the dashboard-directory probe; a panel-specific
  data-health endpoint or a non-recursive registry-probe contract is needed.
- **Production-kernel-set coverage is partial (MEDIUM)**: the card correctly covers AutoKernel's
  current llama.cpp anchor (`production-consolidated-v9`), but does not yet project the independently
  frozen whisper.cpp and qwentts.cpp identities from the speech-kernel ratification. Those backends
  are AK9 work, so absence is recorded rather than implying they are controlled by today's llama
  campaign.
- **ROCm profiling handoffs are plans, not runtime receipts**: `rocm-verify-profile-backend.md`,
  `agentic-rocm-kernel-authoring.md`, and the kernel-specific profiling handoffs remain discoverable
  through the handoff board. The Kernel-R&D page now shows the ROCm evidence it can warrant (device
  sampler, paired replay, claim release); it must not synthesize progress from open prose rows.
