# November 26 research intake filing

The operator approved the [Stage 3 plan](../../research/deep-dives/intake-nov26-kernels/stage3-plan.md). Stage 4 filed nine non-inference boxes with companion briefs under five existing task owners, and ten monitor notes. Nine active handoff files received changes. No existing checkbox flipped, and no new handoff or hand-authored domain row was needed. The intake covered 15 submitted sources and nine expansions across three sweeps. The approved plan SHA-256 is b413fc944ba3699c3a47d213836f25ed9399e533c292e5248216fe460a9b69be.

| Existing owner | New boxes |
|---|---|
| kv-cache-program | KPF-RESTORE-RECOVERY, KV-NONDET-FIRST-DIFF, KPF-STATE-COPY-CENSUS |
| eval-tower-program | EV-SKILL-NULL-REPLAY |
| autokernel-loop | AK-SHORT-ROW-CENSUS |
| cpu-decode-roofline-program | MOE-STATIC-POOL-REPLAY, CPU-KDA-EXP-CENSUS |
| speculative-decoding | DF2-TARGET-KV-CONTRACT, SPEC-FILTER-TIES |

Four additional handoffs received monitor prose. The November 26 fixed-width atomic-flush diagnosis supplies a baseline for the cross-width comparison. The recurrent-state census distinguishes residual slot transitions from the existing host checkpoint copy.

Validation covers all 24 entry dispositions, owner-bound task lines, fresh briefs, generated-index inputs, and the proposed filing digest. The wiki source scanner recognizes the 24 dives, plan, run summary and [digest](../../research/deep-dives/intake-digests/2026-11-26-ids-2982-3005.md). The README link resolves to the scan-visible run summary. No benchmark was run.

## Wrap-up and dispatch check

The [filing](https://github.com/pestopoppa/epyc-root/commit/4332a76c3) and [hub index regeneration](https://github.com/pestopoppa/epyc-root/commit/573dee585) reached main. At root revision `23e33d5ca`, the dispatcher’s shared eligibility check returned six eligible, three held. All nine boxes remain open and all ten monitor conditions remain prose. This check establishes start eligibility; it assigns no workers or compute.

| Owner | Ready for source work, fixtures or retained-data replay |
|---|---|
| Eval tower | EV-SKILL-NULL-REPLAY — compare skill-gate decisions against shuffled labels and untouched trials |
| Speculative decoding | DF2-TARGET-KV-CONTRACT — map released weights, cache layers and index epochs; SPEC-FILTER-TIES — verify retained support and log-probability semantics |
| AutoKernel | AK-SHORT-ROW-CENSUS — count eligible fused MMVQ calls on 27B and A3B |
| CPU decode roofline | CPU-KDA-EXP-CENSUS — bound the contribution of KDA exponential loops; MOE-STATIC-POOL-REPLAY — price static expert placement from recorded routes |

The `heterogeneous-slot-fabric-residency` hold in [holds.yaml](../../handoffs/active/holds.yaml) covers the KV-cache handoff. It excludes KPF-RESTORE-RECOVERY, KV-NONDET-FIRST-DIFF and KPF-STATE-COPY-CENSUS despite their non-inference class and empty prerequisite gates. The stated release condition is a GPU window. Re-evaluate the box-level dispatcher predicate when the hold changes. The first recovery task should use the current experimental baseline and preserve the neighboring sequence. No task was launched or ticked during wrap-up.

The 3,001-entry index and approved-plan binding passed again. All 72 anchors from this intake were independently reviewed and retained. The canonical belief ledger was current through intake-3005 with zero lag. Reviewed a later AutoKernel handoff change concerning separate bottleneck-classifier work and refreshed the short-row brief’s source fingerprint; its task and acceptance criteria still stand. The handoff index check reported zero problems, and the README freshness check emitted no warnings.

Next: Eval tower can start the skill replay, speculative decoding the DFly2 mapping, and AutoKernel the short-row census in parallel. CPU roofline can independently start its KDA census.
