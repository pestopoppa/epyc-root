# Preparation and KPF offline audit — 2026-10-31

### 2026-10-31 LEX2 held-out and CS-26.F1 preparation

LEX2 held-out capsule v5 is engineering preparation, not READY: no actual dev selection, held-out inference, score or release decision exists. A same-launcher public JFK control exercised positive-trie Nemo and frozen Whisper fixed/auto-language paths, followed by a STOP partial/drain control. The held-out instance still depends on the actual dev selection and the frozen plan; the original scientific task remains open. [Qualification and bounded capsule](../../artifacts/compute/codex3-prep-and-kpf-audit-20261031-0443/). [belief: cc]

CS-26.F1 independent first-window raw capture is READY (publication manifest SHA-256 `a68a475c397c3fe281b7f9b661a5049aafd5b99e7bffad7aebc93f7d4163ca8f`). Its plan contains eight arms × 22 clips × three repetitions; public tiny-model normal and STOP controls qualify the launcher, not full-target timing or quality. Selected STT2 runner arms, the second window and STT5 WER remain outstanding; no F1 verdict is claimed. [Plan and controls](../../artifacts/compute/codex3-prep-and-kpf-audit-20261031-0443/). [belief: cc]

### 2026-10-31 #25592 replay preparation

Private multi-turn replay is READY (publication manifest SHA-256 `40370fc8a7f084795cf9f8efa4fb5a5bac2214a5f02f08875b1d4e630c4c790e`). Five actual three-turn sequences are selected and seven predeclared per-store slots remain UNKNOWN. The real launcher public 0.6B control does not exercise the full model, MTP or long contexts; no full-run, rate or gate conclusion follows. The capsule retains only hashes and count metadata for private sessions. [Plan and controls](../../artifacts/compute/codex3-prep-and-kpf-audit-20261031-0443/). [belief: cc]

### 2026-10-31 KPF collector and retirement audit

An offline audit of 40 original full records found 60 positive response-timing versus zero post-completion-slot observations across 37 records; all 37 also passed both aggregate fork-count and token-sum checks. Captured source SHA-256 `6676a39bb424712619132b63a05e1b7c7a91f0a2d1b8888c08a7e6fc36942e20` matches the original source manifest: final response timings are captured before release resets fork counters, while the collector requests `/slots` after completion. This phase mismatch explains why the two observations cannot be equated; it does not establish a native fork failure or change original run checks. Future diagnostics need an in-request sample or retained task-identified field; do not redraw original cases. [Offline audit and captured excerpts](../../artifacts/compute/codex3-prep-and-kpf-audit-20261031-0443/). [belief: cc]

The retired Qwen3.6-35B UD-IQ3_XXS candidate is not referenced by any active READY or armed packet in the audit; the withdrawn historical packet remains retained. The active KPF packet was already prospectively pinned to Q8 before its full run. The Q8 full digest in the declaration was not recomputed by this audit. The owner stopped both captured GPU qualifier watcher processes and verified them dead before any native GPU control or READY; no pending watcher is claimed live. Original KPF scientific gates remain open. [Retirement and watcher-stop receipts](../../artifacts/compute/codex3-prep-and-kpf-audit-20261031-0443/). [belief: cc]

No scientific checkbox changed.
