# Deep Dive: Privacy Parser — Hybrid Wrapper over OpenAI Privacy Filter

**Date**: 2026-04-24
**Intake**: intake-452 (github.com/chiefautism/privacy-parser)
**Related**: intake-449 (OpenAI Privacy Filter, upstream model) + existing deep-dive at `research/deep-dives/openai-privacy-filter-pii-preprocessor.md`
**Question**: Does the HybridPIIParser offer enough engineering value over the raw opf 1.5B model to be worth adopting as a component (not just a pattern) for any EPYC use case — and where exactly would it slot in?

## Executive Summary

Privacy-parser is a thin, Apache-2.0 Python wrapper (~400 LOC across `hybrid.py`, `detectors.py`, `model_parser.py`, `postprocess.py`) that turns `openai/privacy-filter` from a redactor into a span extractor and then stacks two engineering layers on top: a label-aware span-merger and a narrowly-scoped regex backstop covering the exact failure modes the raw model has (URL, secret, account_number). The self-reported F1 jumps from **0.733 (raw model) to 0.929 (hybrid)** on the upstream sample eval at +~100 ms CPU latency — a very cheap win if those numbers hold.

The intake-449 deep-dive concluded the raw model was *"a design reference, not a deployment candidate"* because we have no user-facing PII workload. That conclusion still holds for the **orchestrator hot path**. But the hybrid's engineering — especially the conservative regex backstop restricted to three high-precision categories (`private_url`, `secret`, `account_number`) — makes it attractive for a **different, lower-stakes slot we already have**: pre-commit KB-hygiene scanning and any offline/batch ingestion pass where 600 ms/document is a rounding error. The verdict gets a narrow upgrade below.

## Technique Analysis

### Three backends compared

| Backend | Weights | Latency (CPU) | Fixture F1 | Failure mode |
|---|---|---|---|---|
| `PIIParser` (regex-only, `detectors.py`) | 0 | µs | 1.000 on fixture | Fixture is regex-biased; generalizes poorly to novel names/addresses |
| `ModelPIIParser` (`model_parser.py`) | opf 1.5B (~3 GB) | ~500 ms | 0.733 | Span fragmentation, phone/account confusion, occasional URL/secret miss |
| `HybridPIIParser` (`hybrid.py`) | opf 1.5B + regex | ~600 ms | 0.929 | Dominated by residual model errors on names/addresses |

The 1.000 regex F1 is not a real win — it's measured against a fixture (`privacy-filter/examples/data/sample_eval_five_examples.jsonl`) whose patterns are the same ones the regex was written against. The model-only 0.733 is the more honest baseline for what the opf weights alone give you on short messy text, and the hybrid's 0.929 is what you actually get when the regex backstop catches the three failure categories the model documents about itself.

### Why the hybrid backend wins: anatomy of the regex backstop

The code in `hybrid.py::_apply_regex_backstop` is a surgical, asymmetric merge — not a naive union. Four rules matter:

1. **Backstop is restricted to three labels**: `private_url`, `secret`, `account_number`. The tuple is literally `_REGEX_BACKSTOP_LABELS = ("private_url", "secret", "account_number")`. Regex is **not** allowed to add `private_person`, `private_phone`, `private_email`, or `private_date` — the author's judgement is that regex noise would dominate signal there, and the opf model is already strong on those.
2. **Model wins ties**: if a regex candidate overlaps a model span with the same label, the model span is kept. Regex only fires into gaps.
3. **Strong-prefix overrides**: regex wins over the model only with *evidence*, not authority. URLs must start with `http://` or `https://`; secrets must carry a known prefix (`sk-`, `pk-`, `ghp_`, `gho_`, `xoxb-`, `xoxp-`, `AKIA`, `Bearer `). This is the "account-number-as-phone" fix from the commit history made general.
4. **Containment-required account swap**: for `account_number`, the regex span only replaces a model span if it (a) fully contains the model span and (b) the model labeled it `private_phone`. This is the single documented failure mode (long digit runs being tagged as phones), encoded directly into the override logic.

The secret regex taxonomy is worth quoting because it shows the design intent (`detectors.py`):

- Known-issuer prefixes: `sk-…`, `pk-…`, `AKIA[0-9A-Z]{16}`, `ghp_`, `gho_`, `xox[baprs]-`, `Bearer …`
- High-entropy passphrases: `\b(?=[A-Za-z0-9\-]*\d)(?=[A-Za-z0-9\-]*[A-Za-z])[A-Za-z0-9]+(?:-[A-Za-z0-9]+){2,}\b` — i.e. at least three hyphen-separated tokens with at least one digit somewhere. This catches `Priv4cy-Filt3r-2026`-style passwords that a token classifier won't recognize without training data.

The account regex is the simplest and strongest: `(?<![\d\-])\d{10,24}(?![\d\-])` — a bare 10-24 digit run with no adjacent digits or hyphens. Wide net by design; the containment rule keeps it from stealing phone numbers.

### Viterbi + BIOES + span-merge pipeline — the engineering contribution

The pipeline has three stages below the model (in `hybrid.py::parse`):

1. **Viterbi tuning via calibration file**. `ModelPIIParser._write_calibration` writes a small JSON with six transition biases; the default hybrid config sets `transition_bias_end_to_start = -0.5` (discourage ending-then-immediately-starting another span) and `transition_bias_inside_to_continue = +0.2` (gently prefer continuing an in-progress span). This is a calibration layer — same weights, different decoder — and it attacks the documented opf failure of span fragmentation.
2. **Span-merge** (`postprocess.py::merge_adjacent_spans`). Same-label spans separated only by whitespace / `.-,/` within a label-specific gap cap (`private_person=3`, `account_number=1`, `private_email=0`, etc.) get glued. This is the "`Quindle` + `Testwick` → `Quindle Testwick`" fix and the "`404` + `Nowhere Lane` → single address" fix in one pass.
3. **Regex backstop** (described above).

The three stages are independently toggleable via constructor flags (`enable_viterbi_tuning`, `enable_merge`, `enable_regex_backstop`) — meaning the ablation story is built into the API surface, which is unusually clean for a one-author repo.

### Latency vs accuracy trade

600 ms per call on CPU is the hybrid cost. For context: our 30B-A3B worker decodes at ~49 t/s single-NUMA-node (per `project_96t_single_node_operating_point`), so 600 ms is ~30 decode tokens of wall time. That's too expensive for a per-request filter on a hot path, but utterly trivial for:

- Pre-commit hooks (hundreds of ms of hook budget is standard)
- Offline KB ingestion passes (we already eat multi-second OCR/chunking latency per document)
- Nightshift batch jobs

Regex-only is µs and would be fine on the hot path — but it's the fixture-biased 1.000 number, not a robust-signal 0.929, so the honest hot-path deployment would be regex-only for speed + eventual consistency reconciliation via hybrid in batch.

## Cross-EPYC Applicability

### opendataloader-pipeline-integration.md — gap #5 status

Gap #5 is **"No prompt injection filtering"**. Privacy-parser does not close gap #5. It is a PII *span extractor*, not a prompt-injection detector — prompt injection is adversarial-instruction detection, a categorically different problem. The intake-449 deep-dive already made this point; intake-452 inherits the same limitation. **Gap #5 stays open.**

What *does* change: intake-452's hybrid is a ready-made drop-in for the "if a PII step is ever added to the pipeline" conditional in the intake-449 note. Instead of re-wrapping opf ourselves (writing our own BIOES → span → merge → backstop stack), we'd import `pii_parser.hybrid.HybridPIIParser` and be done. That's a concrete reduction in future engineering effort, not a reason to add a step now.

### KB-hygiene use case (pre-commit hook for accidental secrets/emails)

This is the slot where privacy-parser earns its keep. Concretely:

- **Hook location**: `/workspace/.git/hooks/pre-commit` (and in sibling repos `/mnt/raid0/llm/epyc-orchestrator`, `/mnt/raid0/llm/epyc-inference-research`, `/mnt/raid0/llm/epyc-root`). Or, better, managed via `pre-commit` framework with a repo-local hook.
- **Scan targets**: staged text files — markdown, Python, YAML, JSON, shell. Skip binaries and known-heavy paths (`*.gguf`, `.gitnexus/`, `logs/`, `progress/` archives where historical references are fine).
- **Command shape**:
  ```bash
  git diff --cached --name-only --diff-filter=ACM | \
    xargs -r python -m pii_parser.cli_model --fail-on secret,account_number,private_email
  ```
  (the upstream CLI is `pii_parser.cli_model`; a small wrapper would need to exit nonzero when spans with the gating labels appear)
- **Gate labels**: `secret` and `account_number` are hard-fail. `private_email` is soft-warn (the repo contains team emails legitimately — `daniele.pinna@gmail.com` is in the user memory). `private_url` is noise here (we reference URLs constantly). `private_person`, `private_phone`, `private_address`, `private_date` are not relevant for a code/docs repo hygiene hook.

The fit is good because (a) the hybrid's strongest categories (`secret`, `account_number`, `private_url`) are exactly the commit-leak categories; (b) pre-commit latency budgets easily absorb 600 ms × N-staged-files; (c) false-positives on `secret` get dismissed with a standard `# noqa: pii` convention or the hook's own ignore file; (d) the opf model handles novel secret shapes the regex might miss (the author explicitly calls this out as a reason the hybrid exists rather than the regex alone).

A regex-only variant (`PIIParser`) would be even cheaper for this use case and is probably the right *first* deployment — the hybrid becomes justified only if the regex starts leaking novel secret shapes that the opf model catches.

### Why this is NOT a router/classifier candidate (wrong shape)

The intake-449 deep-dive flagged the opf architecture (small-MoE, 3.3% active, AR→bidirectional, 128-expert top-4) as a *design reference* for future routing classifiers — not as a deployable classifier itself. Privacy-parser does not change that: it wraps the same weights for the same task. It cannot serve as a router (wrong output space — BIOES spans, not a routing distribution), a draft model (wrong decoder — bidirectional encoder, not causal LM), or a difficulty classifier (no difficulty head, no fine-tune path described). The architectural lessons from intake-449 still apply and are not re-derived here.

## Refined Assessment

Original intake verdict: **`adopt_patterns`** (learn from the regex-backstop and span-merge design but don't deploy).

**Refined verdict: `adopt_patterns` for the orchestrator hot path (unchanged), narrow `adopt_component` for the KB-hygiene pre-commit slot.** The hybrid is a genuine drop-in for a use case we already have — accidental-secret scanning on staged files before commit — and the engineering (asymmetric merge rules, label-aware gap caps, Viterbi calibration file) would take us a week to reproduce from scratch. Importing `pii_parser` for that one slot costs us a Python dep plus ~3 GB of weights (cached in `~/.opf/privacy_filter`, one-time) and buys correct handling of novel secret shapes.

Caveats that keep this narrow rather than broad:

1. The 0.929 F1 is self-reported on the upstream's own 5-example fixture. Not independently replicated. Before deploying, run the hybrid on a held-out set from our own repos (synthesize a fixture with 20-50 intentional secrets + negatives) and measure.
2. The regex-only backend is strictly cheaper and probably sufficient for the secret categories we most care about (`sk-`, `ghp_`, `AKIA`, `Bearer`). Start there; upgrade to hybrid only when regex-only misses something.
3. Relevance remains **medium**. Novelty remains **low** (the engineering is careful but not novel — it's a well-executed model+regex fusion pattern). What's upgraded is the *adoption surface*, not the research value.

## Concrete Next Actions

1. **Stand up regex-only pre-commit hook first.** Write `/workspace/scripts/hooks/pii_precommit.sh` that runs `pii_parser.cli` in regex-only mode on staged files, gating on `secret` and `account_number`. Install in the three repos under `/mnt/raid0/llm/`. No model download required for this phase. Budget: half a day.
2. **Build a 30-50 example held-out fixture** of real-shape secrets (rotated tokens, fake account numbers, synthetic emails) matched to our repo text style. Store as `/workspace/research/fixtures/pii_hygiene_eval.jsonl`. Use it to validate both the regex-only and hybrid backends on *our* distribution before upgrading anything.
3. **Re-evaluate hybrid upgrade after 30 days of regex-only operation.** If regex-only has zero misses on the held-out fixture and zero real-world bypasses, stop. If it misses 2+ novel shapes, pull in `pii_parser[hybrid]`, accept the 3 GB opf weight cache, and switch the hook.
4. **Do not add a privacy step to the orchestrator hot path or the opendataloader Phase 1/2 pipeline.** Gap #5 (prompt injection) remains open and privacy-parser does not address it. Revisit only if a third-party-user-data workload materializes.

## Sources

- Primary repo: https://github.com/chiefautism/privacy-parser (Apache-2.0)
- Upstream model: https://huggingface.co/openai/privacy-filter (intake-449)
- Companion deep-dive: `/workspace/research/deep-dives/openai-privacy-filter-pii-preprocessor.md`
- Handoff context: `/workspace/handoffs/active/opendataloader-pipeline-integration.md` (gap #5 "No prompt injection filtering")
- Source files reviewed: `pii_parser/hybrid.py`, `pii_parser/detectors.py`, `pii_parser/model_parser.py`, `pii_parser/postprocess.py`, `tests/test_hybrid.py`
- Related memory: `project_learned_routing_controller` (architectural reference link via intake-449), `feedback_opensource_only`, `feedback_dont_dismiss_creative_uses`
