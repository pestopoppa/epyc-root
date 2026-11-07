# 2026-11-07 — autokernel (AutoKernel session wrap-up)

## Surface proofs (gfx90a low-level tier, AK-GFX90A-ASM-SURFACE)

| Row | Outcome |
|---|---|
| `ak-surface-proof-b-20261106` | COMPLETE, SURFACE_E2E_OK, correctness PASS (stock FA hsk128 585/585, cases 6/6, killswitch 6/6). Hand-asm gfx90a FA (asm_artifacts `.co`, source-patch.v2) built, loaded, verified and timed end to end. |
| `ak-surface-proof-a-20261106` | No GPU result. iglp0 built ok (230 s); `iglp_opt(1)` drove clang-18 device compiles of mmq-instance-iq1_s/iq2_s to 37 min, 222 GB and 124 GB RSS; stopped via STOP + SIGKILL of own PIDs. `iglp_opt(1)` in mmq-vec-dot.cuh is compile-pathological on gfx90a. |
| `ak-surface-proof-a2-20261107` | Published: C6 vs iglp0 only, reuses iglp0 build, min window 5400 s; smoke queued. |

Proof B diagnostic medians (us, n=5), C6 vs h5:

| Shape | C6 | h5 | Ratio |
|---|---|---|---|
| heads16 kv512 | 200.8 | 91.3 | 2.20x |
| heads16 kv4096 | 1066 | 475.7 | 2.24x |
| heads16 kv16384 | 4020 | 1788 | 2.25x |
| heads32 kv512 | 298.2 | 115.8 | 2.58x |
| heads32 kv4096 | 2076 | 516.9 | 4.02x |
| heads32 kv16384 | 8059 | 1887 | 4.27x |

h5_off == C6 within 0.1% (killswitch falls back). Caveat: heads32 ~= heads16 time at kv16384, so check before any keep claim (filed AK-H5-VERIFY). Surface proof only, NOT a keep claim. Result: `/mnt/raid0/llm/tmp/ak-surface-proof-b-20261106/out/RESULT.json`. AK-GFX90A-ASM-SURFACE stays open: its done bar needs an actor-generated candidate (a loop run).

## Tooling (research repo, epyc-inference-research main)

| Commit | Change |
|---|---|
| `0dc9f5c14` | build RLIMIT_AS/CPU ceiling in `execution/worktree.run_build` |
| `8101ea8eb` | per-process cap = 256 GiB whole-build budget / jobs, clamp 16-64 GiB (-j8 -> 32 GiB) |
| `b74651c8a` | custody re-pin `actors.py` after review of `dd3ab6326` + `189b1d29b`; stale author-prompt order test fixed |
| `529036ed8` | `test_custody_hold` child bound to its own tree (venv `.pth` put shared clone on sys.path -> canonical_recipe foreign refusal) |

Full loop suite from a lane worktree: 6023 passed, 1 failed (fixed by `529036ed8`). Earlier runs showed 15 test_validation_final_receipt errors and one 40-min stall near test_scratch that did not recur and pass in isolation (flaky under host load ~55).

## Root work today (already pushed)

- AKX-ALL-31.GDN ticked: K=3 across CPU/GPU x f32/BF16, 0/27,262,976 mismatches; reverse-slot and key-row mutants fail; r11 receipt-ack.
- INF-82 owner/route lines on 53 open AKX boxes: ADOPT 42, RE-FILE-C7R 4, ROUTE main-inf22 3 (+LB3 co-route), ROUTE Pipeline Mgmt 3, DECLINE-recommended 1 (P4c). Triage: `/mnt/raid0/llm/tmp/akx-triage-20261107/TRIAGE.md`.
- Runtime: suspended dispatcher sessions autokernel-all-devices-all-dimensions and autokernel-cross-workload-keep-gate repointed to `autokernel-akx-program.md` / INF-82 (backup `handoff-sessions.json.bak-ak-repoint-20261107`).

## Peers

- main-inf22 corrected the H6 citation (research `cddaaf14c`; 1.017x never existed); accepted routed LB3.1/LB4/LB4.9/LB3-kernel as C8 fold candidates; wants row ids when P0d-W3-HALFB-C6 C7r re-file and the LB3 premeasure produce results.
- Pipeline Mgmt landed opencode fix `189b1d29b`; routed to them AKX-ALL-15/15a/15b + `job.py:46` entry guard (reply pending).

## Handoff changes (this wrap-up)

`autokernel-loop.md`: dated result sub-bullets on AK-GFX90A-ASM-SURFACE (rows A, B) and AK-MMQ-H3; ticked AK-BUILD-CAP, AK-CUSTODY-REPIN, AK-TESTENV-FIX (`[no-belief: tooling-repair]`); new boxes AK-BUILD-MEM-1, AK-H5-VERIFY, AK-MMQ-IGLP1-DNR (futility-only gate class).
