# 2026-08-21 — Research intake: Qwen chat templates (intake-1212 … intake-1217)

Per-agent shard (`scripts/coordination/WORKTREE_MIGRATION.md`). Operator-submitted single URL,
run through all four intake stages plus a Stage-2b round. **No lane worktree** — operator-spawned
ad-hoc session in the shared clone; staging was hunk-selective and every diff was inspected before
commit, per the SessionStart contract for lane-less sessions.

## Problem

Operator submitted `https://huggingface.co/peculiar-ragdoll/Qwen-Sharp-Chat-Templates` with the
hypothesis that it was *"easy low-hanging fruit to improve all our current and future qwen models"*,
and explicitly invited contradiction.

## What the dives found

Six entries, all dive-verified or dive-overturned. Verification ran against primary source — the
stock `Qwen/Qwen3.8-27B` template, the templates embedded in **our own production GGUFs**, both
community templates, and the frozen `production-consolidated-v9` tree at `0db32c06e`. **No server
was started and no inference was run**; the GGUF templates were extracted by a header read, so the
29 GB model was never loaded.

| Claim | Verdict |
|---|---|
| Sharp = upstream v22.3 + terseness + 3 fast-mode fixes | **CONFIRMED to the byte.** Thinking-ON render minus the terseness block is *exactly equal* to upstream's, at 3 kwarg settings; thinking-OFF differs by exactly the 3 documented changes |
| froggeric: "official template raises on `enable_thinking=false`" | **OVERTURNED.** Neither stock nor our Unsloth variant raises. The real fatal trigger is `reasoning_effort` outside `{xhigh, medium, low}` — including `'none'`, froggeric's own documented off-switch |
| froggeric: "deep Jinja nesting drops llama.cpp speed 80%, cured by AST flattening" | **REFUTED.** Template is compiled **once at model load** (`server-context.cpp:1454`, sole server call site); per-request path renders a pre-compiled program (`server-common.cpp:1092`). Also froggeric's template is 3.0× larger, deeper, 3.3× slower to compile |
| froggeric: chronological retention → prefix cache | **First recorded as overturned; CORRECTED same day** — see below |
| CCoT (intake-1214) | **CONFIRMED**, all four figures. The 27.69% math penalty is GPT-3.5-only; GPT-4 shows no significant decrease |
| TALE (intake-1215) | **CONFIRMED.** 67% token reduction at −2.72%; **+3.11% accuracy on GSM8K at 75.7% fewer tokens** |
| google/minja (intake-1216) | **OVERTURNED as our engine.** Frozen v9 runs a first-party `common/jinja/` engine (ggml-org PR#18462); the only "minja" strings in the tree are a stale comment, a test and a doc |
| Claw-Eval (intake-1217) | **CONFIRMED.** It is an *autonomous-agent trajectory* benchmark — so Sharp's only quantified plate does not measure the knowledge-work/coding claim it is offered for |

## The mistake I made, and what caught it

**I generalised a family conclusion from one model generation.** Testing retention across
stock-3.8, our Unsloth-3.8 variant, froggeric and Sharp, I found all four retained history thoughts
and recorded intake-1213's retention claim as *overturned as a differentiator*.

The operator asked whether any handoff changes targeted **the other Qwen models in the stack**.
They did not — every template task I had written was scoped to Qwen3.8, because that was the only
model I had checked. Sweeping the embedded template of all four production GGUFs produced two
results pointing opposite ways:

| Model / role | Template | `reasoning_effort` outside {xhigh,med,low} | `xhigh` default | Empty-`<think>` dup | Retains history thinking |
|---|---|---|---|---|---|
| Qwen3.8-27B — `architect_general` | 9,993 B `12827f24b742` | **RAISES** on `none`; `high` → `xhigh` | **yes** | **yes** | yes |
| Qwen3.6-27B — `coder_escalation` | 8,057 B `55d4931433fe` | ok | no | no | **no — discards** |
| Qwen3.6-35B-A3B — `frontdoor` | 8,057 B (byte-identical) | ok | no | no | **no — discards** |
| Qwen3.5-122B — `architect_critic` | 7,992 B `8452ca85cb1e` | ok | no | no | **no — discards** |

- **Every defect is Qwen3.8-only** — scoped to the model swapped in 2026-08-20; the incumbents are clean.
- **The retention gap is the incumbents'**, not Qwen3.8's. Three of our four served templates throw
  away past reasoning, which is exactly what the community templates fix. So the claim I had marked
  overturned **holds against three of four production models**.

`intake-1213` `claim_corrections[2]` was corrected from `overturned` to `narrowed`, and its
`dive_corrections` rewritten to carry the reversal so the old conclusion is not re-derivable.
It is currently **inert** for us regardless: we serve `enable_thinking=false` on every one of those
roles, so there is no reasoning in history to retain. That is now `CT-5`, deliberately unbundled
from the A/B.

## Answer to the operator's hypothesis

Installation genuinely *is* out-of-the-box — one `--chat-template-file` flag or one
`gguf-new-metadata` rewrite, no requantization, no registry change, no kernel touch. That half
holds. The correction is which half does anything: under `enable_thinking=false` the **verified**
benefit (retention → prefix cache) is inert, and the **active** ingredient (the terseness prompt) is
the unmeasured one — its only number lives inside a PNG, measured on an agent-trajectory benchmark,
on a reasoning-compression finetune. Our own intake-276 already held that stylistic conciseness is
the weakest form of the intervention; TALE (now filed) is the numeric-budget form and beats it.

## Two defects found in our own tree, incidental to the intake

- **`qwen38-27b-replace-qwen36.md` cites commit `b376dadd`**, which resolves in *none* of epyc-root,
  epyc-orchestrator or epyc-inference-research. The swap that does resolve is `1cff5162` in
  `stack_templates/default.yaml`, and `orchestration/model_registry.yaml` contains **zero**
  occurrences of the fixed string `Qwen3.8` — its `architect_general` / `coder_escalation` still
  name Qwen3.6-27B. Filed as **Q38-T2**.
- **We serve a non-stock (Unsloth) template** on every Qwen role and no registry descriptor says so.
  Filed as **Q38-T3**.

## Changes

| Repo | Path | Change |
|---|---|---|
| epyc-root | `research/intake_index.yaml` | +6 entries (1212–1217) with `claim_corrections`, `claim_anchors`, `depends_on`, `dive_corrections`; intake-194 re-encounter note; intake-1213 retention correction |
| epyc-root | `handoffs/active/qwen-chat-template-evaluation.md` | **new stub** — 5 open + 1 done task, fleet-sweep table |
| epyc-root | `handoffs/active/routing-and-optimization-index.md` | +1 row `RTG-54` |
| epyc-root | `handoffs/active/qwen38-27b-replace-qwen36.md` | +3 tasks (Q38-T1..T3) |
| epyc-root | `handoffs/active/per-request-reasoning-budget.md` | +3 tasks (PRB-T1..T3) |
| epyc-root | `handoffs/active/reasoning-compression.md` | +2 open, +1 done (RC-T1..T3) |
| epyc-root | `handoffs/active/eval-tower-verification.md` | +1 task (ETV-T1) |
| epyc-root | `handoffs/active/prompt-construction-determinism.md` | +1 task (PCD-T1) |
| epyc-root | `handoffs/active/master-handoff-index.md` | regenerated rollup block |
| epyc-root | `.research-session.json` | session state through Stage 4, 6-row steering ledger |

## Results

- `bash scripts/validate/validate_intake.sh` → **exit 0**, 1213 entries
- `python3 scripts/handoffs/index_state.py --check` → **exit 0**, 0 problems
- **16 tasks added, 2 checkbox flips** (RC-T3, CT-6)

## Deferred — with named blockers

- **CT-1 (per-suite A/B)** — blocked on an inference window; nothing is serving today and this
  session ran zero inference by design.
- **PRB-T3 (top-level `reasoning_effort` on our llama-server path)** — blocked on a running server;
  it is a server behaviour, not a template property, and cannot be settled by rendering.

---

## Second pass (same day) — task implementation via 5-agent opus/xhigh fan-out

Operator directed: audit the session's handoff changes, then implement. Audit re-verified all six
task-claims at HEAD; workflow `wf_7114b22d-c95` ran 5 agents (one handoff file each, 562k tokens,
11 min, 0 errors). All agent diffs audited against pre-dispatch snapshots: 12 checkbox flips, 2 new
gated tasks, zero out-of-scope writes.

### Closed (12): Q38-T1/T2/T3 · PRB-T1/T2/T3 · CT-2/CT-3 · ETV-T1 · RC-T1/T2 · PCD-T1

### The two verdict-inverting findings

1. **The Qwen3.8 swap is not live anywhere that matters.** The launcher takes `-m` from
   `orchestration/derived/stack_priors.yaml` (`orchestrator_stack.py:134,:252-262,:1062-1071`) —
   not from `stack_templates/default.yaml`. The derived file (compiled 2026-08-11, nine days before
   the swap) still says Qwen3.6-27B at `draft_max: 4`; the master registry was **never** swapped
   (`git log -S 'Qwen3.8'` → empty; the handoff's ticked "registry swap DONE 2026-08-20" cites a
   commit that resolves nowhere). A stack start today launches Qwen3.6 at draft depth 4. Parity
   validation compares **ports only** (`stack_templates.py:303`), so the divergence passes silently.
2. **CT-3 inverted:** both community templates scan ten `<|think_*|>` pseudo-tokens **out of user
   message content** (frog.jinja:38-66) to overwrite reasoning state — a prompt-injection surface
   input marking structurally cannot mitigate (it constrains tokenization, not template control
   flow). Stock and our GGUF templates are clean of the pattern. Any pilot must strip the two
   marker-scan blocks.

### Other verdicts

- PRB-T1: the `--jinja` removal workaround was **reversed 2026-06-26** (f4a8a3ca; J12 probe 0
  leaks/loops n=15) — the handoff's 2026-04-15 premise was stale. Residual: a live fallback in
  `orchestrator_stack.py:1402` still encodes the reversed policy (fires only on the no-priors path).
- PRB-T3 decisive: `reasoning_effort` has **zero occurrences** in frozen v9 — nothing can read it.
- ETV-T1: scorer contract is trajectory-blind by construction (`debug_scorer.py:86-91` strips
  `<think>` at :107-108, `_score_code_execution` collapses per-test detail to a bool at :448 while
  the research-repo twin already returns the rich dict); two of Claw-Eval's three channels already
  exist on the write side. Verdict: pilot — ETV-T2 filed (report-only divergence counter).
- CT-2: every measured row was captured under the embedded template (`--chat-template-file` has zero
  orchestrator occurrences); E-7's re-calibration trigger lacks the template axis — amendment
  applied to `reasoning-effort-levels.md`.

### Owner-side applies this pass

EVL-33 `Next action` refresh (PRB-T4 queued, 125 chars); E-7 template-axis amendment;
`index_state.py` regen + `--check` → 0 problems.

### Blocked / prepared (operator)

- `orchestrator_stack.py:1397-1402` fallback fix — **classifier-blocked twice** (production
  lifecycle script); exact edit prepared in the PRB handoff. Not worked around.
- Master-registry edits (Qwen3.8 role key + template-provenance block) — registry is frozen;
  exact YAML prepared in the Q38 handoff, ratification bundle presented to operator.
- CT-1 (A/B) and PRB-T4 (TALE-EP run) — inference window; CT-5 — operator decision, package drafted.

---

## Third pass — the operator's script run falsified my own headline finding

The operator ran the v1 ratification script; the pipeline's `lean_registry: stale` error exposed
that `orchestration/model_registry.yaml` in the ORCHESTRATOR repo is **auto-generated** (its own
head banner says so — every audit read the file from the middle). Chasing that: **the true master
(epyc-inference-research) WAS swapped on 2026-08-20 by `b376dadd`** — a local, unpushed commit; the
"resolves in no repo" check had been defeated by that repo's `safe.directory` config. My published
"master registry was never swapped" finding was wrong-level; the operational conclusion stands
(launcher reads derived priors as-is, `orchestrator_stack.py:252-262`; a start still serves
Qwen3.6@4) but the gap is the **compile chain**, not the swap. Corrections written into the Q38
handoff status + a dated correction block; ratify script rewritten as v2 (phase 0 reverts v1's
lean edits with an inverse-edit byte-proof; phase 1 provenance → true master; phase 2 `update
--allow-descriptor-model-removal` with an only-removal assertion + derived verification + check
green; phase 3 unchanged). Second same-day instance of auditing a compiled artifact as its source.

## CT-7 delivered: epyc-qwen3x-v1 built and probe-verified

Operator redirected CT-3 posture: build our own, don't track community. Built
`artifacts/chat-templates/epyc-qwen3x-v1/` from froggeric v22.3 (Apache-2.0): the 46-line inline-tag
scan **deleted** (the injection surface), the tag sanitizer **kept**, terseness excluded (it is an
A/B arm, not a default). Probes: user-content `<|think_off|>` flips froggeric, does NOT flip
epyc-v1; retention holds both shapes; kwargs channel intact; byte-parity with base on tag-free
input. sha256 `faaecb215031…d8c15`. Open: vendored-suite run + `common/jinja` render check.

## Idle-window protocol (operator-directed)

CT-1a filed: CT-1/PRB-T4 run CPU-side during autokernel GPU windows — bus region claim first,
prod sampling temp+seed42, per-question JSONL as drain points, per-suite reporting. Checked now:
no claims held, no inference ports listening — no window to join at this instant.

---

## Fourth pass — ratified AND run (operator: "lets ratify and run")

**Ratification EXECUTED**: orchestrator `7483d7fb` pushed to origin/main. Derived layer verified:
architect_general → Qwen3.8-27B-Q8_0 @ draft_max 8, zero Qwen3.6 references, jinja true; all three
launcher `--jinja` sites now default True. Script survived three reality corrections in the process:
`check`-vs-`update` semantics, the already-transitioned descriptor set (idempotent no-op accepted),
and the pre-existing quarter-port surface drift (Q38-T4 filed; scoped assertions — abort only on OUR
surfaces). The dFlash2 `challenger_under_evaluation` block carried through the recompile intact.

**Validation RUN, all green**:
- Vendored suite vs epyc-qwen3x-v1: v21 9/9; fuzz clean over 2,000 conversations (nine invariants);
  v22 85/100 with all 15 failures being the deliberately-deleted inline-tag feature. Oneline build
  generated (19,421 B), parity holds.
- **Real-engine check on frozen v9 `common/jinja`** (CPU llama-server, test port :8990, model loaded
  3 s from warm cache, killed + verified dead after): all 7 `/apply-template` fixtures rendered
  **byte-identical** to Jinja2 goldens — injection dead, retention alive, on the actual serving path.
- **PRB-T3 live-confirmed**: top-level `reasoning_effort` renders identical to no-kwargs (server
  drops it); `chat_template_kwargs` channel steers. Static + live now agree.

**Non-roster claim disclosure**: the bus claim mechanism is roster-gated; this session has no roster
id and did not borrow one. The run proceeded on operator direction, verified-idle box, non-production
port, with this disclosure in lieu of a claim.

**Answering the operator's draft_max question**: 4 was Qwen3.6-27B's own measured optimum (n4 53.1
t/s, 1.82×, 2026-07-20 sweep); 8 is Qwen3.8's (n8 55.46). Depth is per-model; the pre-ratification
state was a self-consistent old world, not a mistuned one.

---

## Fifth pass — CT-1 A/B launched; wiring obligation discharged

**CT-1 A/B in flight** (operator: "run the CT-1 A/B on CPU now while the box is idle"). Runner at
`artifacts/chat-templates/epyc-qwen3x-v1/ab-cpu-20260821/ct1_ab_runner.py` (live copy in
`/workspace/tmp/ct1-ab/`, gitignored): arm0 embedded vs arm1 epyc-qwen3x-v1, ONLY the template
differs; Qwen3.6-35B-A3B CPU under the full codified canonical recipe (`canonical_recipe.py`:
taskset 0-95 + numactl --interleave=all, OMP spread/cores/active/false, GGML_IQK=1, --no-mmap);
4 suites × 40 pinned seed-42 questions, identical rows both arms; production sampling temp 0.6 /
seed 42, `enable_thinking=false`; scored by orchestrator `debug_scorer` (never hand-rolled);
per-question JSONL = drain points; per-suite + paired-flip reporting. Arm0 healthy at 13:46:53
(5 s load — 33 GB hot in page cache from the fidelity check). Monitor armed on checkpoints,
completions, failures, summary.

**Belief-kernel wiring filed at first-measurement time** per the standing rule: source-table row in
`scripts/vidya/adapters/README.md` (candidate; tuple spec includes template_sha256 — the new axis),
SC46 in `vidya-belief-substrate-program.md`, CT-8 in the CT stub.

**Shared-index race observed live**: three `MM` entries (a peer session staging its wrap-up-doc
update) at commit time — this wrap-up committed through a private index per the newly-documented
pattern.
