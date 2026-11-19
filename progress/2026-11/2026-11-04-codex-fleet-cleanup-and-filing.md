# 2026-11-04 — Codex fleet cleanup after dispatcher stop + filing backlog drain (operator session)

Shared-clone session (no lane); this new file is the only commit content.

## Fleet state
- Dispatcher had been stopped by the operator. All 11 registry-"live" Codex handoff sessions had exited cleanly
  (each printed `WRAPPED <sha>`); registry reconciled live -> suspended. 17 leftover `pane-status` tmux windows closed.
- 12 idle filler wrappers (10-28..11-01, only polling `sleep`) reaped. The 7 ARMED-UNBOOKED rows among them
  (fa4-c5 r8/r12, codex-m4-c3-original, hil15b x3, cs8-stt5 baseline r2) demoted to BACKLOG in FILLERS.md
  (backup `FILLERS.md.bak-20261104-reap-demote`). Correction: their class `block-correctness` is a scheduling
  category (booked-block only), not a fault; they were never granted because no block was booked.
- Compute idle cause: keeper healthy, cands=0 — 0 runnable rows (282 BACKLOG mostly harness-fix, 72 STALE-ARMED).
  Refill requires the handoff-session dispatcher (operator to restart; proposed max_live=4).

## Operator approvals applied
- EXP01-EXT approved; row brf-exp01-trellis-ext-20261104-r4 ran: IQ4_KT/Q4_K_M tg128 0.953 [0.937, 0.969] — inconclusive, no speed case.
- kvu upstream issue posted: https://github.com/ggml-org/llama.cpp/issues/31654 (handoff note `fe9a23d86`, lane/h-kvu, unpushed).
- D9-acked: `b700b641a` (file_result bare handoff names), `84c3d7c86` (publish_row completed-smoke result binding;
  behaviour change: missing-result smoke rows now leave READY). Installed live in compute-flags/bin.

## Filing drain (84 unfiled run-ends -> 4 subagents)
All filed via `churn/file_result.py --verdict-json` except 4 refused (no manifest: kvfork174d custody/pinned,
akxall8-v5-rootcg, brf-exp01-pilot — all smoke-only / superseded). No checkboxes ticked; owners tick.
Verdicts: scratchpad `verdicts/`; receipts in `compute-flags/filing-done/`.

Key results:
- LSA: GitNexus ops.cpp parser stall fixed (80 s timeout -> 3.4 s); LSA graph candidate passes all CPU builds/cases;
  MI210 synthetic found tol-0 BF16 key-projection mismatch, fixed by HIP repair (35B geometry untested).
  Window control sink4+last4608 lost retrieval on 1 item (no population claim). Blocked vdpbf16ps matches frozen; unblocked off by 1 ulp.
  HIP std::sort does not compile for gfx90a.
- C6 q4 MMVQ fixes pass on their single exact cases; 25 q4_K MUL_MAT fails remain on MMQ route -> run the mmqfix candidate.
- AKX-ALL-10.1 route-2 sinks CPU correctness PASS; LB3.2 CV4 pair PAIR_INVALID (MG G-arm ~5x slow).
- PF1-EXPAND: MI210 overtakes CPU on Q38FN prefill from L=512 (A2 1.12x) / 1024 (A1 1.44x); 2048 1.94-2.12x; L=512 control guard missed -> 384/768 refinement.
- KVU-16h: L3 decode loss 58-61% -> P5 and split-per-slot triggers MET. KVU-16g: no first-prompt TTFT tax. KVU-16a: 35 GiB non-KV VRAM (27B Q8).
- P12: two half servers at np16 = 0.69x one full server. M4 GPU A/A noise SD ~3%; r8 0.9597 within noise.
- YARN E1-MEM chain r2: 128k->500k single-server chain COMPLETE, peak 47.6 GiB (<55).
- CAFE-4 lifecycle build PASS; rollback build fails `-lcommon` link. G3 MI210 cells timing UNKNOWN (no correlation ids).
- BRF EXP09 mechanism did not fire (REVISE). UFH-12 cosine distributions captured. UFH-14 pilot no actual open.
- Infra failures needing owner fixes: GDN HIP repair (grant has SMT siblings, needs exactly 4 CPUs); ch31 fixture
  (`all` target, mtmd.h missing); akxall8 v7 (duplicate R15 ancestor in inherited_cpu_claim.py); sr8 spec-stats
  extraction; tu-dtap-2 CRM pair rc=75; inf22-m4 r4 rc=1; cs8-stt4 crisp HIP rc=64; yarn r1/r2 share one RESULT path.
- Tool gap: file_result.py rejects verdict "invalid"; no-result runs filed as `fail` with "INVALID RUN" rationale.

[no-belief: session-cleanup progress note; the filed verdicts are carried by filing-done receipts]

## Later the same day
- Verdict recording: 5 boxes newly ticked (LSA-SCREEN-1-CPU-WINDOW, EXP01-EXT, PF1-EXPAND-LOADTHREADS,
  KPF-32.IMPACT, REPL-EMB-2.11-QUERY); ~32 boxes got dated partial/fail checkpoints with next steps
  (main `080d14f02`, `8433e2e38`, `981ef5ba9`). No tick on umbrella or failed boxes (no closure inflation).
- Follow-up rows published READY (smoke PASS):
  - `pf1-expand-r2-20261104` — PF1-EXPAND-2 crossover at L=384/448/512/768, 5 reps (box `ca5246d1a`, `9b3053853`).
  - `handoff-kvu19-p5-champion-a1-20261104` — KVU-19-P5A1: does the champion masked-block skip remove the
    58-61% L3 decode tax (box `0b45d7d0a`). Split-per-slot NOT re-opened: operator decided "keep shared 393k"
    on 2026-10-03 on the same trigger; re-ask only if this row returns NO-RECOVERY.
  - `cafe4-v10-mtp-rollback-build-v3-20261104` — rollback examples/CMakeLists linked nonexistent target
    `common` (-> bare -lcommon); fixed to `llama-common`. Link only verified when the full row runs.
- Dispatcher restarted by operator with max_live=4 (hs-dispatcher window); first pass resumed 5 sessions on
  pending run-end events (kvu, akagg, fable5-window2, agentic-serving-harness-fixes, df2).
- Dispatcher window behaviour: windows close on DONE/pause only; "continue" sessions keep a pane-status window
  until resumed (handoff_sessions.py ~1340-1356). Not changed.
- Shared clone /workspace holds an unpushed local duplicate of the morning progress commit (`d29de8d4b`,
  same content as main `3ccf46e8c`); drop it at next clone sync, do not push it.
