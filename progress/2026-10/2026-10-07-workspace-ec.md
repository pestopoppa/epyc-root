# 2026-10-07 Wrap-up — workspace-ec (research intake: Q38FN on 2x DGX Spark, Stage 4)

## Summary

Stage 4 of the intake of the myllmbox 2x DGX Spark Q38FN recipe, applying the operator-approved Stage-3 rev2 (+5.0% go/no-go; "approved. Proceed to stage 4"). 26 intake entries (intake-1937 to intake-1962) are dive-verified with 268+ claim anchors; four tasks filed, zero checkbox flips, no index rows, no pruning, no wiki sweep.

Verified outcome: two-Spark aggregate bandwidth (546 GB/s peak, not pooled) is within 2% of our 537.6 GB/s; like-for-like (official 10-expert NVFP4, TP2) the independent median is 53.7 tok/s vs our 52.66; the 93/177 tok/s headline is a 5-of-512-expert healed checkpoint with MTP up to K=7 and a best-window peak. The remaining gap is streaming efficiency. The draft-head vocab trim is not a CPU lever (our B10).

## Tasks filed (4 new, 0 flipped)

1. **cpu-decode-roofline-program.md**: Q38P-1 (measure Q38FN MTP step bytes, expert union, tokens/step, streaming GB/s; parts split by timing need), Q38P-2 (after Q38P-1, schedule or decline B10's IQ4_XS head requant probe).
2. **mi210-big-model-and-acceleration-roadmap.md**: Q38P-3 (ROCm 10.1 value assessment, staged, reboot only inside the v11 window, +5.0% go/no-go; host fact: in-kernel amdgpu of kernel 6.14.0-37), Q38P-4 (vLLM-on-MI210 probe with bundled userspace; also the in-kernel-driver compatibility test).
3. **speculative-decoding-mtp-refresh.md**: note amendment under CAFE-3 only (controller priors, expert-union ordering, d sweep, RecoverSSM monitor); gates unchanged.

## Checklist-sync gate

Flips yours: 0 committed, 0 uncommitted (nothing completed in a handoff; the work was intake-index and plan work). New tasks: 4.

## Derived-actionables gate

Newly filed tasks 4; explicit declines 5 (vocab trim, 5-of-10 expert cut for now, draft-vocab coverage/prefix-cache alignment checks, 2-node TP/EP, adopting vLLM/SGLang as MI210 serving stacks pending Q38P-4). Written, not filed, by design: the physics-normalised comparison clause for C1 (knowledge retention, carried to the next wiki compile); a one-line correction to docs/runbooks/rocm-upgrade-checklist.md (TheRock lists gfx90a Linux as Release Ready on the 2026-10-06 page, not "Build Passing only", intake-1962#record); both are for the owning session or the operator-invoked /wrap-up since the approved plan did not authorise edits to the wiki or the runbook.

## Index

`INDEX_EDITS.md` (out of repo, /mnt/raid0/llm/tmp/intake-q38fn-cluster/) holds proposed Next-action cell text for INF-70 and INF-34; not applied. Only the generated index_state block changed (open count +4); `index_state.py --check` exit 0.

## README freshness

`check_readme_freshness.py` printed no warnings.

## Deferred to the operator-invoked /wrap-up

Index pruning (nothing seen that it would handle from this lane) and the wiki compilation sweep (hardware-optimization and inference-serving pages should absorb the Spark physics comparison and the ROCm 10.1 value-assessment facts).

## Evidence

Scratch, reports and dive artifacts: /mnt/raid0/llm/tmp/intake-q38fn-cluster/ (STAGE3_PLAN.md rev2.1, INTAKE_STAGE1.md, INTAKE_STAGE2.md, dive-*/, dive-s3/). Plan digest recorded in `.research-session.json` as stage3_filing.plan_sha256.
