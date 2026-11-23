# Dive — verge — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://neurips.cc/virtual/2026/178991", retrieved: "2026-11-23", sha256: "0116f18e3fdc"}

Expanded from intake-2830 (vegafafnir), section 7. Source location. Web search found no arXiv id for this title, and author-name searches found none either. The NeurIPS listing (effective URL `https://neurips.cc/virtual/2026/loc/sydney/178991`) gives the title, the authors, the venue (Poster in Workshop: ML for Systems) and the full abstract. Its "Project Page" link points to OpenReview, `https://openreview.net/forum?id=VlaOSoLEV1`. OpenReview's forum, PDF and API endpoints all returned a browser challenge (HTTP 403 `ChallengeRequiredError`), so the body of the paper was not reachable. The only primary text read is the authors' abstract on the NeurIPS page. It is enough to mint an entry because every claim below is anchored in that abstract, but the read depth is abstract-only.

## 1. Stage-1 fields

- **Title**: VERGE: Verifier Execution Regimes Break Greedy Equivalence in Speculative LLM Serving (confirmed on the NeurIPS page)
- **Authors**: Kailash Talreja, Satyam Kumar, Saurabh Jha
- **Version/venue**: NeurIPS 2026 workshop poster (ML for Systems), listing 178991; OpenReview forum VlaOSoLEV1. No arXiv preprint was found.
- **Categories**: speculative_decoding, benchmark_methodology, inference_serving
- **Novelty**: low to medium. The phenomenon (packed verification is not row-exact against AR decoding) is already established in house (INF-70 E2a; `docs/design/spec-decode-run-nondeterminism-20261122.md` §2) and in intake-2830. The abstract adds three things: a chain from local verifier flips to drafter decision errors (strict false accepts) to user-visible divergence; a backend-pinning null result; and a second, independent prompt-level divergence rate.
- **Relevance**: medium. Production is always speculative, and our identity gates compare arms that change verify width. VERGE adds no mechanism we lack. Its value is an HTML-anchorable, independent rate for the claim class "most greedy speculative outputs diverge from AR within 128 tokens". intake-2830 (PDF-only, stage1-unverified) cannot supply that anchor.
- **credibility_score**: 2. Workshop peer review is light and the reviews are not visible, so I count 0. Listed for NeurIPS 2026, within 12 months: +1. No major-lab byline visible: 0. No commercial bias: 0. Independent corroboration of the mechanism by in-house INF-70 E2a measurements (verified rows fail identity under drop and redecode; cpu-decode-roofline-program.md, cited via intake-2830's dive): +1. intake-2830 itself is stage1-unverified, so I do not count it.
- **Verdict**: worth_investigating. The abstract corroborates, with its own numbers, the A/B-identity conclusion our design doc already encodes. The body (setup, model, hardware, the definition of "strict reachable") could not be read. Nothing here is a component.

## 2. Key claims

0. **Packed verification must reproduce AR decisions for greedy speculation to be lossless; violations reach user-visible output: CONFIRMED (abstract framing).**
   - page, Abstract: "Greedy speculative decoding is lossless only if packed target verification reproduces ordinary autoregressive (AR) target decisions on the same prefix"
1. **53.55% of 592 prompts diverge from AR by token 128: CONFIRMED.** This was the steering snippet, now verified verbatim. The abstract does not give the model, hardware, engine or drafter.
   - page, Abstract: "Free-running speculative output differs from AR on 53.55% of 592 prompts by token 128"
2. **About 0.34% strict reachable AR-packed disagreement, reproduced by controlled and real-drafter experiments, with strict false accepts on the neural drafter: CONFIRMED (abstract). The definition is NOT-FOUND-IN-SOURCE.** The abstract does not say whether 0.34% is per position, per verify row or per round.
   - page, Abstract: "Controlled and real-drafter experiments independently reproduce about 0.34% strict reachable AR-packed disagreement"
   - page, Abstract: "the neural drafter encounters strict false accepts rather than merely an upper-bound risk"
3. **29.90% first diverge at positive AR margin, and every first divergence maps to a measured verifier event: CONFIRMED (abstract). The denominator is ambiguous**: 29.90% of all 592 prompts, or of the diverging ones. If it is of all prompts, then roughly 24 points of the 53.55% are zero-margin (exact-tie) divergences. That would echo intake-2830's 39.2% exact bf16 ties, but the abstract does not say which reading is right.
   - page, Abstract: "29.90% first diverge at positive AR margin, and every first divergence maps to a measured verifier event while prefixes are still identical"
4. **Pinning both paths to the PyTorch MATH backend gives no detectable reduction (MATH-AUTO = +0.012 pp, 95% CI [-0.077, +0.106] pp): CONFIRMED.**
   - page, Abstract: "Forcing both paths to PyTorch MATH produces no detectable reduction in strict disagreement (MATH-AUTO = +0.012 percentage points, 95% CI [-0.077, +0.106] pp)"
   - page, Abstract: "pinning a backend flag is insufficient to guarantee greedy equivalence"
5. **Setup (model, precision, hardware, engine, drafter, prompt sets): NOT-FOUND-IN-SOURCE.** This claim is not carried into the draft's key_claims, which hold claims 0-4. The abstract is silent, and the body is behind the OpenReview challenge. The phrase "PyTorch MATH" implies a PyTorch SDPA stack (inference from the backend name, uncited).

## 3. Reported results (as the abstract states them; setup not stated)

- About 0.34% strict reachable AR-packed disagreement, reproduced independently in controlled and real-drafter experiments.
- Strict false accepts observed with the neural drafter.
- Free-running speculative output differs from AR on 53.55% of 592 prompts by token 128. 29.90% first diverge at positive AR margin. Every first divergence maps to a measured verifier event while the prefixes are still identical.
- MATH-AUTO = +0.012 pp, 95% CI [-0.077, +0.106] pp, so pinning the backend does not detectably reduce strict disagreement.
- Hardware, model and engine: not in the abstract.

## 4. Performance-principles table (mechanism and cost model)

| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| P1. A packed (multi-row) verify forward is not AR-row-exact, so it can accept a draft token that AR would not emit (a "false accept") | YES. C19 dispatches different kernels for n=1 and for verify widths (MMVF cap 8, FA VEC vs GQA_VERIFY, GDN rows vs fused; see intake-2830 dive P1). Not measured as a false-accept rate on GPU. | YES, measured in house. INF-70 E2a: drop and redecode fail at verified rows, and only serial is exact (cpu-decode-roofline-program.md, via intake-2830 dive P2). `GGML_ROWEXACT_N` is the in-house cure on CPU (`ggml/src/ggml-cpu/ggml-cpu.c:1708-1727 @ a6a32c1`; default 0, MTP n-max 4 costs 22.93 → 21.56 t/s). |
| P2. Pinning a kernel *family* or backend flag does not restore equivalence; only width-1-equal arithmetic or serial verification does | YES as a design rule. An "FA-VEC for verify rows" style pin would still run a multi-row reduction order unless each row used the n=1 kernel. Port cost of real row-exactness on HIP: a row-at-a-time path per op (MMVQ/MMVF n=1 kernels looped per verify row, FA VEC per row), which is roughly k+1 n=1 passes per verify. That is a test oracle, not serving (uncited estimate). | YES. ROWEXACT is per-row kernels, not a flag; `LLAMA_SPEC_EXACT=row` requires it (`tools/server/server-context.cpp:1855 @ a6a32c1`). |
| P3. Divergence attribution: map each first divergence to a verifier event while prefixes are identical | YES, code/analysis only: log the verify-row logits at the first-divergence round. | YES, same. |

## 5. In-house state

- `LLAMA_SPEC_EXACT` has the modes drop, redecode, serial, row and batched-greedy-inexact (`tools/server/server-context.cpp:42-77 @ a6a32c1`). Serial is "Exact by construction; no batching benefit" (L52-53).
- `GGML_ROWEXACT_N` has row-exact CPU kernels, opt-in with compiled default 0 (`ggml/src/ggml-cpu/ggml-cpu.c:1708-1727 @ a6a32c1`).
- `GGML_DETERMINISTIC` is **not present in C19 `a6a32c1`** (`git grep` returns zero hits under ggml/src, src, common and tools/server). It lives only on fork branch `llama.cpp-experimental-determ-20261122` (`bef2e4c7d`).
- The design doc already states VERGE's conclusion in our own terms: "Deterministic mode makes **A/A** exact. It cannot make **A/B** byte-identical" (`docs/design/spec-decode-run-nondeterminism-20261122.md:83 @ d785b6d`). It replaced single-sample identity with a margin-classified statistical gate (§3, L86-102).
- The served path samples at T > 0 for most roles (per intake-2830's dive), so greedy equivalence is a gate instrument, not a serving property.

## 6. Derived-actionables ledger

- **V1 (refines intake-2830 A1; doc-only).** Task: add one sentence to `docs/design/spec-decode-run-nondeterminism-20261122.md` §2 stating that pinning a kernel family or backend flag is not a remedy for A/B divergence, citing `intake-<verge>#04`, and that only row-exact kernels (`GGML_ROWEXACT_N`, CPU) or `LLAMA_SPEC_EXACT=serial` give width-1 equality. Owner: speculative-decoding.md (INF-50 / DF2-12.1 own the identity rule; exists, not frozen). Compute: none. Decision: closes the option of adding a "pin FA/matmul kernel" arm to A1 or A4. Stop: the sentence lands and cite-check exits 0.
- **V2 (refines intake-2830's citation status; doc-only).** Task: where a handoff, wiki page or gate rationale cites a prompt-level greedy-speculative divergence rate to justify a statistical identity gate, cite `intake-<verge>#01` (53.55% of 592 by token 128, anchorable). Keep `intake-2830#record` for the Vega-Fafnir figures, which stay stage1-unverified. Owner: speculative-decoding.md (§3 protocol consumers: DF2-12.1, CAFE-3 P9, RS-REPLAY gates). Compute: none. Decision rule: a gate rationale must pass `scripts/vidya/cli.py cite-check` (exit 0). A rate cited only via intake-2830 is a whole-entry citation of a stage1-unverified record.
- **V3 (refines intake-2830 A1; folded in, no new row).** When A1 measures S, also record the share of first divergences at exactly zero top-2 margin. Our logits are f32, so this share should be near 0. VERGE (29.90% at positive margin) and intake-2830 (39.2% exact bf16 ties) both suggest that bf16-logit stacks put a large share at exact ties. If our zero-margin share is not near 0, logits are being rounded somewhere on our path. That would be a finding in itself, and it would mean τ cannot be transferred from bf16 papers. Owner: speculative-decoding.md (A1's owner). Compute: inside A1's row, no extra.
- **Decline: ingest-on-reachability of the VERGE body as a separate row.** The full text is behind an OpenReview challenge. Its likely content (setup, a definition of "strict reachable") would refine numbers we do not gate on. No ledger row above depends on it.

## 7. Dive-surfaced sources (strict rule: ingest only if it changes a ledger row of this run)

- **OpenReview forum VlaOSoLEV1** (same work, full text): unreachable by automation (challenge). Decline as a separate entry; it is this entry's body.
- **arXiv 2607.17283, "Lossless but Not Free: An Empirical Anatomy of Speculative Decoding on Consumer Hardware"** (not in the index; a search snippet says quantized backends can lack batch invariance). Decline. It would not change V1-V3 or intake-2830's A1-A4, because our own A/A margins (design doc §5a: OFF A/A 7/16 at 0.006-0.19 nat) already measure quantized-backend noise on our stack directly.
- **arXiv 2609.26638** (diffusion-drafted OCR, near-tie argmax flips under bf16, per snippet; not in the index). Decline. It restates the mechanism on another workload with no actionable delta.

## 8. Contradiction / adversarial pass

- **Not a replication of Vega-Fafnir's numbers.** VERGE's 53.55% (592 prompts) and intake-2830's 60% (150 prompts) are different measurements on stacks that are unknown or different. They agree in order of magnitude only. Treat VERGE as an independent observation of the same claim class, not as corroboration of 60%.
- **Stack dependence is real.** arXiv 2510.22876 v4 Table 4 (the bspecforensics entry, this wave) shows vLLM v1 on H100 with batch-invariant kernels off still giving 80/80 exact for speculative BS=1 against non-speculative BS=1 (Qwen3-4B/0.6B, K=3, 80 MT-Bench prompts). On that stack, verify width alone flipped nothing. So "a majority diverge" is not universal, and VERGE's rate must not be imported as a prior for our kernels.
- **Ambiguities in the abstract**: the unit of 0.34%, and the denominator of 29.90%. Workshop venue; reviews not visible.
- No reviewer pushback or failed reproduction was found (reviews were unreachable).

## 9. read_depth

PARTIAL: abstract only. Not read: the OpenReview body (PDF and forum blocked by a challenge), any figures or tables, the setup and the definitions. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## 10. Artifact audit

artifact audit: clean. page.txt (2536 bytes, sha256 0116f18e3fdc…) is the NeurIPS listing, retained by fetch_one.py (artifact=yes). All 9 quotes are verified substrings. The OpenReview fetch attempt failed and left no file.

**Quotability of Vega-Fafnir via VERGE:** VERGE does not anchor any Vega-Fafnir number. It anchors its own analogous rate (53.55% of 592 by token 128), its backend-pinning null and its false-accept finding. A rationale that needs "most greedy speculative outputs diverge from AR by token 128" can cite `intake-<verge>#01`, with the stack caveat above.
