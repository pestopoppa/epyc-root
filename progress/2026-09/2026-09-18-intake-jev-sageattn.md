# 2026-09-18 — research-intake session `intake-jev-sageattn` (TD-7 routing replay)

- TD-7 ran in an operator-granted GPU window on the frozen pre-purge snapshot (2026-04-15 backup, sha256 12ca8b0b…);
  live `episodic.db` outcomes refused by design (2026-09-17 leak purge).
- Result (N=200): agreement with incumbent 3.0% (6/200); native arm 0/200 because every routing action label is
  multi-token (`frontdoor`=front+door) -> all rows JSON fallback; strong SELF bias (177/200 at ~0.975); AUROC 0.50
  vs frozen success labels (no discriminative power); ECE 0.10 with the incumbent-vs-chosen label caveat.
- Diagnostic, not a failure: the replay harness works; two prerequisites before enforcement arguments —
  single-token action codes (new TD-9) and incumbent-aware candidate framing.
- Receipts: artifacts/typed_decisions/run_20260918/routing-replay-n{60,200}-20260918.json + residency trace.
- Server torn down after the run; VRAM returned to 0.
