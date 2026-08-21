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

## Stage-2b wave 2 — three batches closed after the plan (commit `9cb94047`)

Persisted **intake-1238..1250**, all dive-verified against primary source: Yang et al. SC24 power
telemetry, GrepSeek, GPU Forecasters, TritonRL, GPA (CGO'21), the PyTorch KernelAgent/KernelFalcon
blog pair, CodegenBench, FlashInfer-Bench, AutoKernel, ParEval-Repo, daVinci-kernel, KLineage,
Kernel-Smith. Index at **1,246 entries**, validator green; `index_state --check` 0 problems.

**Five things that corrected something we already believed.** (1) **L1+L2 is not a sufficient C6
gate** — omission of a required operator component passes both, so the third tier must be a semantic
judge (train-free), and the planned NVIDIA-only L3 is dropped rather than deferred. Precision
downgrade is defended by nothing we hold, and `intake-1227`'s dtype-keyed tolerance actively rewards
it. (2) **"illusion of solvedness" was mis-attributed** — neither PyTorch post contains the phrase;
it is KernelGenBench's own gloss, so we may not count a third independent voice on KernelBench
weakness. (3) **The memory-family evidence moved against building** — nine systems, one significance
test in the whole literature, non-significant; the best-constructed ablation returns a *negative* at
the loose threshold with a sign that flips between model sizes on n=1 cells. Our §19.3 receipt rule
is *ahead* of this literature: not one of the nine has a re-verification contract. (4) **The
`intake-1222` energy claim is overturned by direct measurement here** — ROCm 6.2 does expose a
monotonic microjoule accumulator (15.30 uJ/tick across 23 deltas, cross-checked against
`--showpower`); scoped honestly as evidence about the instrument, not about any run. (5) **The
"AutoKernel G15 without a source" premise is struck** — it is a homonym of our own program.

Filed **RVP-C6-19..25, RVP-C4-10..14, RVP-PWR-1..4, C5-14..17, AK-PM-9..17, KB-GS-1..4, SC47**, plus
three index corrections (intake-1227 attribution, the survey's FlashInfer figure, intake-1087
promoted to dive-verified with its cross-run-memory negative). **C5 slots unchanged.**

**Shared clone, no lane — stated per the working-tree rule.** Ten peer files were staged in the
shared index, so the commit was built through a private `GIT_INDEX_FILE`.
`vidya-belief-substrate-program.md` and `scripts/vidya/adapters/README.md` carry *uncommitted peer
hunks* (SC44/SC46, the DFlash2 and CT-1 adapter rows), so both were committed as
**HEAD + my-lines-only blobs**, asserted exact. **OPEN HAZARD for the peer session:** those two files
plus `master-handoff-index.md` still hold the peer's pre-existing *staged* blobs in the shared index,
which predate `9cb94047`. I deliberately did **not** reset them — that is their staging to own — but a
plain `git commit` from that stale index would drop my SC47 and the FlashInfer adapter row from the
tip. Both survive in `9cb94047`; re-add from the working tree before committing.

### `arXiv:2604.06056` ingested — `RVP-PWR-3` closed, and our own power instrument now has a datasheet

**`intake-1251`** (McDaniel et al., ORNL/HPE/AMD, v2 2026-04-09, CC BY 4.0). Index at **1,247**. The one
source in this whole wave that lands on our *exact* architecture: MI250X is gfx90a/CDNA2.

**All four figures `intake-1238` carried at medium confidence are CONFIRMED verbatim**, none overturned —
the averaging window is undocumented (II-B), MI250X average power takes *"a few seconds to fully capture the
transition from idle to TDP"* (V-A2), *"aliasing begins below roughly 4 ms on MI250X"* (V-A3), and the
cumulative energy counter refreshes *"at 1 ms granularity"* in microjoules (II-B). Read via two targeted
passes over the paper's own LaTeXML rendering — the route `intake-1238` could not take, since the PDF
exceeds the fetch limit. This closes the loop on the `intake-1222` energy overturn: we verified the
accumulator exists and accumulates on this host; this paper establishes *why* it is the field to use and
quantifies what the alternative field gets wrong on the same silicon. Our measured **15.30 µJ/tick** LSB is
something the paper does **not** state — we hold a number it lacks.

**Three caveats that must travel with any citation, and one is a real credibility cap.** (1) These authors
used **no external physical meter** — Cray PM is their highest reference and its accuracy is *vendor-asserted
from product-development testing*. That is the specific gap between this and `intake-1238`, which had a
physical meter and scores 6/6 to this one's 4/6; the relative lag/aliasing findings rest on the square-wave
probe and are unaffected, but this may never be cited as external validation of an **absolute** watt figure.
(2) **MI250X is dual-die OAM; our MI210 is single-die** — timing characteristics are expected-to-hold and
worth confirming, absolute joules are not ours. (3) Dense HPC linear algebra, **zero ML/inference content**,
no statement on single-GPU applicability — so the token-cadence **phase-lock hazard remains unmeasured by
either paper.** That gap is ours (`RVP-PWR-2`), and this paper hands us the instrument to close it.

Also found: **its own central equation cannot be applied as published** — `W_conf` is defined in terms of
t_d/t_r/t_f and no numeric values for them appear anywhere, only Figure 5. Filed as **`RVP-PWR-5`** (measure
them ourselves; the square-wave sweep produces them as a by-product) and **`RVP-PWR-6`** (adopt the
runtime-vs-power decomposition — a joules-per-token win that is entirely a tokens-per-second win is a
different engineering fact from one that lowers draw, and we currently do not separate them at all).

### AK-PM-4 SkillBank check RUN (read-only) — the A/B is data-ready and traffic-blocked

Both decision packages operator-ratified as option (a) and bound into their rows (`9de434d7`); the
skipped-gate rule is now in the skill + memory (`6faa32bc`). First ratified execution step, AK-PM-4:
**(1)** trajectory prerequisite over-satisfied — 19,146 memories in the 25-day window (need ≥500), 64,019
total; **(2)** runbook §18 paths are STALE — `/mnt/raid0/llm/tmp/episodic.db` is a 0-byte decoy, live store
is `orchestration/repl_memory/sessions/`; **(3)** the initial distillation NEVER ran — `skills.db` is
schema-only, 0 rows, since 2026-07-27; **(4) NEW UPSTREAM BLOCKER: the episodic store went quiet
2026-08-11T01:31** (v9 freeze day) — zero writes in 10 days, so the A/B treatment arm has no live traffic
until writes resume. Cause not diagnosable from this container; needs the stack-owning session to confirm
`ORCHESTRATOR_MEMRL` at its next reload boundary. Bus routing attempted; this session is non-roster, so the
finding rides in the AK-PM-4 checkpoint for a roster session to carry. AK-PM-11 (kernel-side ablation) is
NOT blocked by this.

## Session close-out (operator /wrap-up)

**After the retroactive gate**: both decision packages operator-ratified as option (a) and bound into
their rows (`9de434d7`) — C6 goes L1+L2+semantic-judge with L3 DROPPED and C6-20 as the judge's hard
prerequisite; the cross-run memory is NOT built until AK-PM-11's n≥5 paired ablation returns, write-side
receipts land now. **Process ratification** ("research-intakes should follow the prescribed flow")
persisted into the skill (`6faa32bc`) and memory (`feedback_research_intake_gate_never_lapses`): a
post-Stage-4 dive wave re-enters the machine at Stage 1/2; ingest approval ≠ filing approval.

**RVP-C6-20 executed to its GPU boundary** (research `ef7fec18`, root `3e09377c`): three genuine Triton
omission mutants + honest controls + references + standard/adversarial input arms; the L1 scanner
mutation-tested non-vacuously (8 planted-dirty samples, scope negative-control, empty-scope refusal,
6/6); **L1 arm: all six candidates PASS with zero findings** — the static half of the falsification
holds. GPU arms (L2 ghost replay, value oracle with NaN/Inf rejection + max-observed-error) written and
refusing to run without `--i-have-a-window`. **Window negotiation in flight**: MI210 held by a
`ct5c_runner.py`-parented llama-server with NO region claim on the bus (reportable condition, surfaced
to operator); `workspace-c0` confirmed not-owner; request routed to `qwen-chat-template-intake`;
operator directed HOLD for the owner's answer.

**AK-PM-4 SkillBank check** (`99ab4f13`): A/B data-ready (19,146 trajectories / 25 days vs ≥500 needed),
runbook §18 paths stale (0-byte decoy at the tmp path), distillation never ran (skills.db schema-only),
and the episodic store QUIET since 2026-08-11T01:31 — treatment arm blocked until the stack owner
confirms `ORCHESTRATOR_MEMRL` at a reload boundary.

**Deferred with named blockers**: C6-20 GPU arms (blocker: owner's window answer — operator-directed
hold); SkillBank A/B (blocker: episodic writes resumed by the stack-owning session); C6-19 judge build
(blocker: C6-20 mutants must first be runnable as its validation set).

### RVP-C6-20 GPU arm COMPLETE — falsified, mid-wrap-up, inside an owner-granted window

The `ct5c` owner (`qwen-chat-template-intake` session) answered during wrap-up: co-resident burst
approved, their metrics latency-independent. Ran 16:03:13–16:03:30Z (~14 s GPU, gfx90a confirmed by the
driver's own guard); owner notified of the exact interval for latency-row annotation. **FALSIFIED:
L1 + L2 + a sound value oracle at standard inputs accepted 2 of 3 omission mutants** — LayerNorm-no-affine
with max error **bit-identical to the honest kernel** (4.768e-07; exact identity under default init),
softmax-no-maxsub at 5.6e-09; matmul-no-transpose caught (94.6) exactly as pre-registered, and passes on
symmetric inputs. All honest controls pass all tiers; all mutants pass ghost replay. `RVP-C6-20` flipped
✅; the judge arm belongs to C6-19's ratified prerequisite clause. Results:
`scripts/kernel_rnd/c6_mutants/results_20260821.jsonl` (research repo).

---

## Sixth pass — CT-5(c) verdict, its same-day correction, and Q38-T4 root cause

**CT-5(c) completed** (60 paired gpqa_diamond_cot, Qwen3.8-27B MI210, v9 HIP residency proven by
three instruments, 0 errors; artifacts `artifacts/chat-templates/ct5c-gpu-20260821/`): headline
T0 70.0% vs T1 63.3%, flips 7:3 against thinking, +23% tokens/solved, non-termination 19 vs 21/60
(the R2d think-loop tail did NOT reproduce — truncation is mode-independent).

**Operator challenged the headline ("why do we keep finding reasoning makes quality worse?") and
the challenge was right.** Truncation decomposition: completed-subset accuracy **95.1% vs 94.9%**,
both-completed paired n=35 → 34 vs 33 (flips 1:0), truncated rows ≈ automatic zeros (0/21
T1-truncated emitted an answer line; truncated-T1 median think 11,078 chars vs 3,187 completed).
The 6.7pp deficit is ENTIRELY a 4,096-cap budget artifact; public thinking benchmarks run ~32K
budgets. Prior anti-reasoning findings here were broken-serving artifacts on other models —
reasoning had never been measured with working serving AND adequate budget. A 16K symmetric-cap
rerun on the same 60 pairs launched 16:2xZ (`/workspace/tmp/ct5c-16k/`). Posture (a) stands
meanwhile; CT-5 carries the correction inline.

**Q38-T4 closed with a root cause that invalidated both proposed fixes**: the 13 "quarter-port"
guard errors were a check-time fleet-mode artifact (launch view defaults to `full` in a clean
shell, filtering the half instances every data file correctly declares). Under
`ORCHESTRATOR_STACK_NUMA_MODE=both`: 13→0 with zero data edits; after a mode-correct regen the
stack-change check is **fully green** for the first time (orchestrator `0d145f4f`). The earlier
half-instance retirement over-read was reverted verbatim before any recompile — production
artifacts never saw it (operator caught it; memory updated with the near-miss).

**Peer co-residency**: granted research-intake-filing-plan a ~14s Triton correctness burst on the
GPU mid-run (doctrine: co-residency is scheduling data); exactly 1 latency row overlapped and is
tagged in `coresidency_annotations.json`. Their RVP-C6-20 falsification succeeded on the granted
window.

### Post-wrap-up interval (operator /wrap-up, second invocation)

No new task rows; the interval's deliverable was the **codex dispatch draft** relayed via the
operator: routes RVP-C6-22/23/24 + AK-PM-12 (evaluator hardening, build now), the three ratified
design constraints (C6 tier stack with L3 dropped; refuse-unknown-part; memory build gated on
AK-PM-11), five cheap probes (AK-PM-13/16/17, RVP-C4-10/11, C5-14/16), and the episodic-store-quiet
action — whole-scope transfer on relay. Two shared-tree repairs this interval, both benign artifacts
of the private-index commit pattern or its twin: (1) the research repo's stale shared index showed my
six c6_mutants files as staged DELETIONS against the new HEAD — scoped `git reset` fixed it; recorded
here because the next committer would have swept a 727-line deletion of a pushed harness; (2) a second
patch-identical twin-commit divergence (ccee7873 local / b3291d43 origin, same parent) reconciled with
a superset-safe `-s ours` merge, same as the first. Peer's live Stage-2b work (+4,102 uncommitted
index lines, CT-5c progress edits) left strictly untouched. GPU-arm follow-ons remain with the codex
agent per the dispatch; this session is quiescent pending compute or new operator input.

### GPU compute pass (operator-directed): RVP-C4-10, PWR-2, PWR-5 all closed with hardware evidence

GPU verified idle first (zero KFD clients via sysfs + host-wide fd scan; 59 W energy-derived draw; the
100% busy field exposed as a latched telemetry artifact — itself corroborating intake-1251). Then, in
~3 minutes of total GPU across five bounded runs: **RVP-C4-10** — PC sampling on ROCm 6.2 is a STUB
(API exported, returns status 16 "defined but not implemented" against the live gfx90a agent; CLI flag
absent) — the GPA/C4-template question closes NEGATIVE by measurement. **RVP-PWR-5** — the confidence-
window parameters the paper never published, measured with two-run persistence: averaged field
t_d ~190 ms, t_r ~4.2 s, t_f ~3.5 s → a phase needs ~8 s before any attributable interior exists.
**RVP-PWR-2** — sampler at 107 µs/sample confirms the 1 ms counter cadence on-die; 250 Hz (the paper's
aliased case) resolves CLEAN at 32 dB, so the 4 ms knee was their instrumentation cost, not the
sensor's; the FFT detection signature validated by forcing aliasing past an analysis Nyquist. **API
trap found the hard way**: `rsmi_dev_energy_count_get` returns the RAW counter (×15.3 to µJ) — a naive
dE/dt under-reads 15.3× and looks plausible; and an async load backlog exactly halved a commanded wave
frequency until sync-per-op. Suite + results: research `scripts/benchmark/power_sensor_probe/` @
`df40658a`. SC48 belief-kernel wiring filed at first measurement. Remaining, deliberately unclaimed:
the token-cadence phase-lock measurement needs a REAL decode workload at the next serving boundary.
