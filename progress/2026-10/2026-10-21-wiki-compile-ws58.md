# 2026-10-21 — wiki compile sweep 5 (workspace-58-wiki, operator-invoked /wrap-up Step 5)

Operator invoked /wrap-up on 2026-10-21. This is the Step 5 wiki compilation sweep, run in a fresh worktree
from origin/main (`/mnt/raid0/llm/worktrees/ws58-wiki-20261021`) under the `wrapup` lease. The first acquire was
refused while `wrapup2-3c4ca599` held the lease. On the retry the lease was acquired, then synced with
`git fetch origin && git merge origin/main` before the scan.

## Delta
- `compile_sources.py` reported **41 new sources**: 21 active handoffs, 17 progress notes and 3 docs (16 added,
  25 changed, 0 removed). The scan after the sync was identical (41).
- The whole delta was compiled, so the watermark was advanced with a bare `--touch`. After the touch:
  `total_new` 0, `--check-manifest` `has_drift: false`, `writer_evidence_policy_ok: true`.

## Pages updated (13; each got a dated "Compiled Update — 2026-10-21 (sweep 5)" section and a refreshed `Last compiled`)
| Page | Main content |
|---|---|
| `wiki/local-inference.md` | DS41-1017 cutover: W5 ppl 2.6675 vs 2.6122 (+2.1%, <1σ), the ABA timing table (served decode +8.1%, llama-bench tg128 −5.1%, pp512 −29.9%, GPU-on +2.2% inside drift = no measurable penalty), W6 drafter, W7 Sept Q4 deletion, W8 oracle, the same-config determinism lesson |
| `wiki/quantization.md` | What serving MXFP4 experts costs: confounded ppl delta, `mxfp4_8x8_q8_0` prefill, ~276 GiB private RAM per server |
| `wiki/inference-serving.md` | INC-20261021-earlyoom-session-kills (two concurrent DS41-1017 servers; earlyoom's ignore regex made sessions the victims; NIB2-97/98; RATIFY-HOST-MEMORY-RULES-20261021 prepared), the compute filler protocol, C2 replaces C, Q38-T10.1 PASS on both phases, frontdoor-to-GPU ruling, corpus flag-off, stale `/workspace` |
| `wiki/hardware-optimization.md` | Nemotron 3.5 Bolt on the MI210 (pp512 899.2 / tg128 53.4 t/s, indicative), NEMO-BOLT-PROF, AKX-ALL-17.x fail-closed op-suite gate, the pipefail `grep -q` lint |
| `wiki/speculative-decoding.md` | NEMO-LILI-1 (LiLiCorr DFlash no net win yet: ~97 ms round vs 19 ms token), DS41-W6/W6.2 drafter alpha, Q38-T10.1 parity verdict |
| `wiki/benchmark-methodology.md` | Net-paired as the shared margin rule, same-config arms, ABA drift reading, EV-19 pool gate, real-token binning, RUS-2 and ECR-EB-1 |
| `wiki/agent-architecture.md` | HIL-13 task-level report, HIL-13a step events, HIL-14 calibration, HIL-15, HIL-12 audit additions, AHE row correction (`intake-1132#record`) |
| `wiki/context-extension.md` | OOL-1 adapter, YARN-AGG-1/JUDGE-1 spec, Oolong real-token counts and constructibility, V11-100 after C2 |
| `wiki/safety.md` | CT-18 IB2 static-attack ASR table and the Skill-Inject partial |
| `wiki/knowledge-management.md` | Both loop belief readers landed; 12 device-scoped claims (VB-LOOP-TEXT); trial clock 2026-11-30; new write-side rows |
| `wiki/multimodal.md` | Speech placement moves to GPU card 2; CS-9 arms; CS-11 declined; OD-A, CS-8.L |
| `wiki/kv-cache.md` | KPF-62.3 to 62.8 slices |
| `wiki/search-retrieval.md` | RTE-CORPUS-1 ratified flag-off |

## Checks
- `lint_wiki.py`: 0 errors, 112 warnings, the same set as before the edits (no new warning).
- `scripts/vidya/cli.py cite-check --as-of 2026-10-21T21:00:00Z`: rc 0. 4,322 citations; the 2 added citations are
  `#record` forms (`intake-1132#record`, `intake-2269#record`), with no refuted, conflicted or dangling ones.

## Notes
- This note is written after the touch, so it appears as one new source in the next sweep's delta.
- `wiki/INDEX.md` is not updated, consistent with sweeps 3 and 4.
- Scratch `/mnt/raid0/llm/tmp/ws58-wiki/` and the token file are removed at the end of the step.
