# RTG-58 / KPF-64 — measurement-sufficiency case study (2026-11-02)

Sources (origin/main after the pin `3ac825873dfb`): commits `a9f44ef56` "Record partial FB and bounded F72 comparison", `0e20b47a3` "Guide efficient measurement stopping and audit backlog", `87082830c` "Add decision-focused reporting principle", `fd06fb064` "Wrap up RTG-58 cache reuse comparison"; `handoffs/active/kv-prefix-fork-and-paged-attention.md` (+18 lines since the pin: KPF-64-F-SUCCESSOR-OBS, KPF-64-FB72-PARTIAL-OBS, F72 prospective repeat, F72 monitor revision, KPF-64-F72-STOP-OBS); `progress/2026-11/2026-11-02-rtg58-readiness.md` (17:15Z, 17:17Z, final entries); `wiki/kv-cache.md` § "KPF-64 cache reuse: 2026-11-02 operational comparison"; evidence packets `artifacts/compute/rtg58-kpf64-f-20261102/`, `artifacts/compute/rtg58-kpf64-fb72-partial-20261102/PARTIAL_AGGREGATE.json`, `artifacts/engineering/rtg58-kpf64-f72-early-stop-20261102/{EARLY_STOP.md,EARLY_STOP_V2.md,EARLY_STOP_DECISION.json}`; raw run dirs `/mnt/raid0/llm/tmp/kv-prefix-fork/kpf64-fb72-20261102/` and the F72 dir (KEEP-marked).

## 1. The question

Practical: **does cache-enabled KV prefix reuse still hold when the server runs on 72 threads (q0–q2), and does it beat the FB configuration (cache RAM 0, which also disables idle-slot caching)?** Decision it drives: whether the RAM-cache arm stays the default for the 72-core serving shape. The formal KPF-64 F–FB gate (full-cohort paired comparison with a timing claim) is a different, stricter question.

## 2. Original plan versus what ran

| | planned | ran |
|---|---|---|
| F24 (24 threads, cache on) | full 230-request repaired cohort | **completed 230/230** (coverage audit: no failed/missing/duplicate; 90.99 % cached prompt tokens vs 91.73 % ideal) |
| FB72 (72 threads, cache RAM 0) | full 230-request cohort, ≈ 4–5 h | **stopped by the operator at 49/230** (rc 143, 17:15Z) — on the 49 identities paired to F24: 0 % cached vs 71.47 %, 17,312 vs 4,945 uncached tokens/request, mean service 326.9 s vs 180.7 s |
| F72 (72 threads, cache on) | not in the original plan; a second ≈ 4–5 h run would have been the "complete" design | **launched after FB72 was stopped, with a predeclared exploratory stop rule, stopped at 20 matched requests**: cached share 34.55 % (F24) vs 34.51 % (F72) vs 0 % (FB72) on the same requests |

Two 4–5 h measurements became one complete run plus two short ones (49 and 20 requests).

## 3. The preliminary readout and the error estimate used

- Readout: paired cached-token share per request, paired by session/turn identity to the already-complete F24 run (deterministic pairing in monitor v2), starting from the 49 FB72-exposed identities.
- Error estimate: a **pragmatic ± 5 percentage-point band from four-family resampling** over the matched pairs, requiring ≥ 20 pairs covering all four families and prompt drift ≤ 2 %; the monitor reports unmet conditions and saves the exact complete-line snapshot before signalling the driver (`EARLY_STOP_V2.md`).
- Observed effect vs band: the F24–F72 difference was 0.04 pp (inside the band by two orders of magnitude); the F–FB difference was 34–71 pp (outside it by an order of magnitude). The sample-size-induced error was irrelevant to the sign of either answer.

## 4. The stop decision

Operator-directed (17:17Z): "stop as soon as the requested information is clear". The monitor fired at the predeclared boundary (20 matched pairs, all families, drift within bound); F72's driver was signalled after the snapshot was saved; the decision was recorded as `KPF-64-F72-STOP-OBS` with `[belief: cc]`, the wiki section was added, and OPERATING_CONSTRAINTS gained the decision-focused reporting principle (`87082830c`).

## 5. Why it was valid

1. **The effect dwarfed the noise.** With a ± 5 pp band and a 34–71 pp effect, no additional request could reverse the ordering; with a 0.04 pp F24–F72 gap, no additional request could make 72 cores look different from 24 at the practical level.
2. **Pairing removed the dominant variance.** Comparing the same session/turn identities across arms turns a between-request spread into a within-pair delta; the completed F24 run supplied the pairs.
3. **Predeclared, deterministic, snapshot-recorded.** The band, the minimum pairs, the family coverage and the drift bound were written before the look; v2 removed the only ambiguity (pair ordering).
4. **Labelled correctly.** The record calls it an *operational decision on partial evidence* and *not a gate verdict*, exactly the distinction the sufficiency guide draws.
5. **Limitations stated, not hidden:** nonrandom early subset (completion order), co-tenancy with GPU P1 work, different CPU layouts, and FB disabling both RAM and idle-slot caching — so no timing claim and no attribution of the F–FB gap to RAM alone.

## 6. Formal-gate requirements it still had to respect (and did)

- The full-cohort F–FB **gate stays open**: KPF-64's parent remains unticked; the handoff text says "not a completed F–FB verdict".
- **No timing claim** — co-tenancy and layout differences forbid it (MEASUREMENT_POLICY: contention model and host state are part of a floor's identity).
- The ± 5 pp resampled band is "an exploratory heuristic, not a formal confidence interval or gate": repeated looks on ordinary intervals are not error-controlled, and the constitution has not adopted a sequential method (OP-ABSEQ recommends no amendment; OP-PQP, OP-ALPHAWIN open). So the stop could only ever produce an operational decision or a futility stop, never "gate satisfied".
- Evidence durability: partial aggregates, source hashes and the decision snapshot were committed; raw private data stayed KEEP-marked; the belief ledger received `cc` observations, not invented measurement warrant.

## 7. Takeaway for the plan

The pattern is: complete one arm, pair the rest against it, predeclare a band and a minimum coverage, look at planned points, stop when the effect is clearly inside or outside the band, label the result as operational, keep the formal gate open. It saved roughly two long runs here because the effect was large relative to the band. Where the expected effect is comparable to the band (e.g. the ≥ 95 % tg128 ratio in EXP-01, the 1.10× PF1 threshold), the same procedure yields *futility or continue*, not an answer — which is still a saving, because futility is reached early.
