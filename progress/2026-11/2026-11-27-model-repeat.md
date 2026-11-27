# 2026-11-27 — model repeat

Operator requested the same repaired full-tools experiment with27B GPU andQ38FN CPU concurrently. Created isolated branch from6552e85cb and revalidated model files/templates/C22 build contents. Model-generalization controls:55 tests pass; exact case matrix prepared for28 fresh conditions with existing repaired main-only baselines reused.

Both owned native servers started concurrently under q0–q3 custody:27B GPU4080461, Q38FN CPU4080462. Both health/slot endpoints show four slots131072 each. Native thinking/tool qualification is running; no real-task quality result yet. Protocol `docs/design/27b-q38fn-full-tools-repeat-20261127.md`; scratch custody `ws58-27b-q38fn-repeat-20261127/KEEP.md`. [no-belief: setup/checkpoint, not model-quality evidence]

Next: codex-a3b-pilot completes native controls, dispatches both models, repairs defects and audits guidance/quality/performance.

## Native repair and GPU dispatch

Epoch01 preflight exposed a greedy-only DFlash device selector with stochastic temperature0.6; actual native SIGABRT was configuration failure before task dispatch. Changed DEV_SELECT to0 using pinned C22 stochastic path. CPU OpenMP cores places expanded into SMT and invalidated a leader-only affinity assumption; explicit singleton physical places plus per-thread topology gate repaired it. Exact original sources/configs/failure receipts retained; both original captured native PIDs reaped and dead-verified.

Epoch02 GPU4174105 and CPU4174106 started together under holder4174024/controller4174029. GPU native qualification passed four physical-slot stochastic/cache controls and both full-tool modes including execute syntax recovery, read/write protected references, and same-session reasoning continuation, with real DFlash proposal counters. Four real GPU candidates launched through independently approved 14-condition queue; CPU native controls continue concurrently. Future owner race fixes and selector compatibility refusal controls are prepared separately without mutating active sources. [no-belief: setup and harness conformance; task quality pending]

Next: codex-a3b-pilot launches CPU queue after capability proof and audits exact task candidates, guidance and performance.

## Both real-task queues active

Q38FN native ON/OFF and full-tool controls passed; MTP postcheck reports617 proposals/461 accepted inON and186/134 inOFF. Main derived generic serving metadata from unchanged native PID/argv/library hashes, current four idle slots and split-context startup log; original LIVE/PASS preserved. Zero-model adapter gap and final MM isolated dependency mount fixed before acceptance. Both14-condition queues are now active at4 workers/model. Index-state check exits0 with pre-existing advisories; git diff check clean. Manual impact review confines canonical changes to worker identity/route/capability and shard placement; no production kernels changed. [no-belief: native and harness conformance, model task verdicts pending]

Next: codex-a3b-pilot audits terminal candidates and records deterministic versus paid corrections separately.
