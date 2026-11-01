# NG5 review — 2026-11-01

Read-only review; no repo, registry, index, lane or compute changes. Research clone HEAD `99301fa149af86a6f9743d2b0405c9234ba39586`; its `orchestration/model_registry.yaml` is already dirty due to unrelated 8083 batch prose (do not overwrite it).

## Evidence and coverage

- Handoff NG5 (currently line 199) requires corpus + repeated-5-gram fraction on every ngram claim in handoff, registry, and any citing index row; also distinct prompts on live context-reading drafter replications and a non-context control. The retraction at lines 41–66 already states original clean-real-text 6–17% repeated 5-grams, repeated warm prompt, self-copy mechanism, non-context control and separate distinct-prompt rerun. Those percentages apply to that original screening only; do not transfer them to other corpora.
- Registry `speculative_decoding_policy.evidence_for_reversal` identifies the 12 matched long-context coding prompts (15k–28k; extend/port/FIM/prose), same prompts for gemma, ordinary prose/code and distinct-prompt ngramfix, and warm repeated-prompt retraction. It does **not** give repeated-5-gram fractions per corpus or specify the complete future replication/control discipline. The generic original 6–17% cannot be attributed to the coding corpus without raw evidence.
- Handoff includes other ngram numeric observations (NG4, T3, T5, COPYSPEC) without documented per-corpus fractions, so NG5 is not satisfied by a general note alone. Original fraction may be unknown; label unknown rather than compute or infer from different prompts. Individual historical observations may require native prompt manifests and analysis as a separately scheduled row; no compute was run here.
- Current `inference-research-index.md` INF-50 row has no ngram number and therefore needs no numeric annotation. Index is thin-row contract; do not add history or measurements to it.
- `MEASUREMENT.md` and `agents/shared/MEASUREMENT_POLICY.md` require protocol-id, n/reps, date and attestation for decision-gating claims; others are observations. The trust boundary is human-amendment-only. Do not add a protocol or change the constitution. Specific sources are observations unless independently protocol-attested; retaining legacy figures does not create a gate.

## Exact narrow proposed patch (owner applies after review)

Immediately after handoff retraction paragraph ending “contamination came from the **generation**” add:

> **NG5 reporting and replication:** Identify the corpus and its measured repeated-5-gram fraction beside each ngram observation; where unavailable, say **not recorded**, rather than borrowing a fraction from another corpus. The 6–17% above belongs only to the screened prompts in this retracted run. For replications, do not repeat a prompt on a live server with a context-reading drafter; use distinct prompts and a non-context-reading control arm. Screening the input alone cannot detect copied prior generation. Numbers without the measurement constitution’s complete claim tuple remain observations.

In research master `orchestration/model_registry.yaml`, in `evidence_for_reversal.retracted_positive` append to its folded scalar (preserving existing content):

> The original screened corpus was clean real text with 6–17% repeated 5-grams; that fraction does not describe the other corpora above. For each n-gram observation record its corpus and measured repeated-5-gram fraction, or mark it not recorded. Replications of context-reading drafters must use distinct prompts on a live server and include a non-context-reading control; input screening alone cannot detect prior-generation self-copy.

Avoid editing generated lean view by hand; inspect native compiler propagation and validate unchanged operative YAML and consumer expectations before publication. This documentation-only proposal does not itself satisfy NG5, since individual historical observations still need provenance/fractions or explicit unknown annotations and source/lean publication. Avoid broad blanket claim that every ngram observation has 6–17% repeat. The proposed historical-note phrasing does not amend production drafter selection or MEASUREMENT.md.
