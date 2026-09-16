# Security-Review Skill (two-pass STRIDE + OWASP)

**Status**: v1 skill scaffold landed 2026-06-13; slash-command integration landed 2026-06-18; CI gate deferred
**Created**: 2026-06-03 (via research intake → factory.ai deep-dive)
**Categories**: agent_architecture, benchmark_methodology, tool_implementation

## Objective

Add a dedicated **security-review** skill (we have a general code-review skill but no security reviewer) that performs a two-pass, framework-driven security analysis of a diff or codebase, with exploit-path-gated severity to suppress false positives. The OWASP-LLM:2025 checklist is directly load-bearing for our own agent/orchestrator/autopilot stack.

## Implementation Status

**Landed 2026-06-13**:

- `.claude/skills/security-review/SKILL.md`
- `.claude/skills/security-review/agents/openai.yaml`

The v1 skill covers the Factory-derived mechanism:

- STRIDE + OWASP Web/API Top 10 + OWASP LLM Top 10 2025 + supply-chain checks.
- Two-pass candidate discovery and exploit validation.
- P0/P1/P2/P3 severity mapped to concrete exploit-path gates.
- Structured finding schema: title, location, problem, exploit path, suggested fix, residual risk, checks run.
- Explicit false-positive guard: do not emit a finding unless attacker capability, reachability, trust-boundary crossing, vulnerable sink, unblocked mitigation analysis, concrete impact, minimal fix, and file/line evidence all pass.

Decision: the skill now has a dedicated slash command wrapper. CI and PR-summary integration stay deferred until a concrete enforcement workflow exists.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-658 | Factory.ai code-review benchmark + security-review feature | high | adopt_patterns |

Full mining → [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md) (Part 3E).

## Mechanism to reproduce (from Factory's `security-reviewer`)

- **Frameworks (checklists)**: STRIDE (Spoofing/Tampering/Repudiation/Info-Disclosure/DoS/EoP) + OWASP Top10:2021 + **OWASP Top10-LLM:2025** (prompt injection, excessive agency, insecure output handling, embedding weaknesses) + supply-chain (lockfiles, typosquatting, install scripts, broad version ranges, brand-new deps).
- **Two-pass**: pass 1 = trace changed data flows across the 7 trust boundaries (auth, authz, validation, database, network, filesystem, **LLM**) → candidate findings; pass 2 = **validate each candidate for reachability/exploitability** before emitting (anti-FP, same verifier discipline as eval-tower).
- **Severity = Critical/High/Medium/Low ↔ P0–P3, each requiring a concrete exploit path** (built-in FP suppression).
- **Structured finding schema** (shared with the code-review 8-gate upgrade): title ≤80 imperative / problem / file+line / severity / suggested fix / 1–3 sentence overall assessment → eval-gradeable.
- Optional per-repo `threat-model.md` injected as focusing context.

## Open Questions

- Which local model(s) drive it? OWASP-LLM analysis of our own stack ideally uses a cross-family reviewer (avoid self-blindness) — tie to eval-tower EV-6.
- Scope presets (base-branch compare / uncommitted / specific commit / custom) — the slash command now accepts an optional scope argument and defaults to the current diff; richer CI/PR presets remain future work.
- Existing code-review skill upgrade — no local `.claude/skills/code-review` exists in this repo. The reusable 8-gate filter and finding schema live in `security-review/SKILL.md`; fold them into a future code-review skill if/when one is added.
- CI integration: PR-summary + min-severity threshold gate — wire later.

## Notes

- Pairs with the **code-review 8-gate bug filter + P0–P3 + finding schema** upgrade to our existing code-review skill (harvest Part 3E) — adopt both together so they share the finding schema.
- Cross-refs: `eval-tower-verification.md` (two-pass = verifier), code-review skill, [`privacy-hygiene-precommit-hooks.md`](../completed/privacy-hygiene-precommit-hooks.md) (secret scanning overlap), `feedback_observe_before_diagnosing`.

## 2026-08-03 — intake Stage-2: CodeCrucible + benchmrk (intake-943, intake-948)

_Via `/research-intake`. intake-943 lands at **`adopt_component`**: CodeCrucible runs on local GGUF
unpatched, and its per-phase provider split **is** the cost-aware-routing ablation we had scoped as
future work — already built, by someone else, on the same shape._

Three mechanisms to lift, in dependency order. The **ordering is the finding** in two of the three:

- [x] **GATE-0 production-reachability, ordered BEFORE exploitability.** CodeCrucible short-circuits on whether the code path is reachable in production *before* it reasons about whether the finding is exploitable. That ordering is what keeps the expensive exploitability reasoning off unreachable code, and it is the opposite of our current two-pass order ✅ 2026-09-16
  - Evidence: root `affa8f9d`, branch `sub/tooling-root-20260916`, merged to root main as `719ac638`. In `SKILL.md`, step 4 now opens with GATE-0: trace from a real entrypoint against flag/config defaults, the launch manifest and import wiring.
  - An unreachable candidate stops with evidence, receives no severity and gets no exploit reasoning. The exploit gates 1–8 run only after GATE-0. The finding schema gains a `Reachability (GATE-0)` line.
- [x] **Mandatory pre-CONFIRM refutation.** No finding reaches CONFIRMED without an explicit attempt to refute it. Pairs with the existing two-pass verifier rather than replacing it ✅ 2026-09-16
  - Evidence: `affa8f9d`, `SKILL.md` step 5. A candidate that clears the gates is still PROPOSED. Its strongest counter-argument must be checked against the code with file/line evidence.
  - A refuted candidate goes to residual risk as `refuted: …`. No recorded attempt means no emission. The schema gains a `Refutation attempted` line, and the gates stay in place.
- [x] **A dedup stage ordered before Pass 2 — ordering from CodeCrucible, KEY from benchmrk's matcher.** CodeCrucible's own dedup key is `startLine` equality, which is too weak: two findings on the same line with different classes collapse, and one finding whose line moves under a reformat survives twice. Take its *placement* in the pipeline and benchmrk's *matcher* for the key ✅ 2026-09-16
  - Evidence: `affa8f9d`, `SKILL.md` step 3, which runs before any validation. Pass 1 now records `path`, a line range and `cwes[]`.
  - The dedup key requires all three of:
    - a normalised path (container mounts stripped, and an ambiguous suffix never matches)
    - overlapping line ranges
    - CWE relatedness: identical or parent/child, with the ten MITRE pillars excluded. Without CWEs, the categories must be equal.
  - Merges keep the union of the evidence, follow a stable order and are listed under Checks run. Same line with unrelated classes stays two candidates.
  - This is written as prose for an LLM reviewer. It is not a coded matcher: benchmrk's five-tier scored matcher, with the distance metric beyond parent/child, was not ported. That would be a separate component if the skill ever gets a scripted pipeline.
  - Overlap note: the gold schema and gold-sanity gate are RA-9 in `reviewer-typed-artifacts.md`, already built. The skill points at them and adds no second schema.
- [x] **Adopt benchmrk's annotation envelope as the dual-gold schema.** Its `status:"invalid"` decoys are exactly the false-positive axis intake-845 records us as lacking — we have no negative-control findings anywhere in the corpus today ✅ 2026-09-16
  - Built ONCE, in the reviewer plane: `epyc-orchestrator` `orchestration/gold_annotation.schema.json` + `src/proactive_delegation/gold_annotations.py` (branch `sub/reviewer-artifacts-20260916` @ `e242a156`, merged as orchestrator `bdf76ab3`; see `reviewer-typed-artifacts.md` → RA-9). The security-review skill consumes that schema and must not grow a second one; `finding.cwes[]` and `finding.category` carry the STRIDE/OWASP class.
- [x] **Add a gold-sanity gate for any machine-generated test or annotation** (intake-983): inject into the real project test file, apply the **gold** solution, run the project's **native** runner; if it fails on gold, discard and retry at higher temperature. **Only then** consult the self-consistency judge. Order is load-bearing — the judge reasons about generated test code that may not itself run, and in the source study it endorsed **all six** named invalid cases. Measured per-augmentation defect rate **61.9% (n=105)**; carry that figure, not the 28.5% iterative one ✅ 2026-09-16
  - Same single implementation: `src/proactive_delegation/gold_sanity.py` (`run_gate` / `validate_record`) — see `reviewer-typed-artifacts.md` → RA-9. Wiring it into the skill's pipeline prose is the skill's own concern.

## Progress checklist

- [x] v1 skill scaffold landed 2026-06-13 ✅
- [x] Slash-command integration landed 2026-06-18 ✅
- [ ] CI gate integration (intentionally deferred)
