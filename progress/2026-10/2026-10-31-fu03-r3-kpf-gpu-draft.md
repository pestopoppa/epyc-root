# FU03 R3 and KPF GPU draft — 2026-10-31

### 2026-10-31 FU-DIVERGE-03 R3 preparation

The earlier R1 admission failure remains filed. R3 is a successor for the original CLI diagnostic: two baseline arms and one candidate arm with the nine-shard DS41 target. Its same-launcher public Gemma 1B control exercised three native arms and the completion checker, with a separate STOP rc75 partial/drain; no full DS41 target or original arm has run in R3. At 05:07 the owner corrected the unarmed READY metadata's scratch root from R2 to R3 and made KEEP and launcher logs explicit; the earlier manifest is preserved withdrawn, and source, launcher and qualified controls were unchanged, so no new smoke is claimed. Corrected READY manifest SHA-256 `56cea4b0628e8242dc39f453fe166b83a2f03f07b8e22bcce1d74e6d4012c763`; source/plan, 739 GiB guard plus margin, original no-redraw policy and original quality task remain unchanged. No baseline-repeat or scientific result follows. [Bounded capsule](../../artifacts/compute/codex3-fu03-r3-kpf-gpu-draft-20261031/). [belief: cc]

### 2026-10-31 KPF-18.1 GPU v2 preparation and qualifier halt

The prospective GPU v2 draft adds per-request raw active `/slots` observations and errors, monotonic windows and matching of native task/slot IDs to response timings; post-completion observations remain separate and missing, late, conflicting or unmatched samples are UNKNOWN. It preserves the original CPU records and checks. Its comparator is prepared to invoke the completed e332 HIP build and a1f0 fork-off on matched target inputs. The recorded 139 offline tests and comparator dry preflight are preparation evidence only, not a GPU residency or KPF gate. [Draft and source pins](../../artifacts/compute/codex3-fu03-r3-kpf-gpu-draft-20261031/). [belief: cc]

The 04:54 watcher receipt is a historical snapshot. At 05:08 the qualifier invocation halted before native GPU control: its log reports `sudo: /usr/bin/chroot: command not found`, and the publisher halted for missing supervisor completion. The two captured v2 watcher PIDs were absent at the 05:09 host check. No GPU READY, normal or STOP qualification, target inference or full KPF grade follows. Owner action: correct and requalify the host entry before any future native control; retain the halt evidence and original observations. [Halt records](../../artifacts/compute/codex3-fu03-r3-kpf-gpu-draft-20261031/). [belief: cc]

No scientific checkbox changed.

### 2026-10-31 CAFE-1 host-qualified successor

The earlier unarmed `codex3-cafe1-pmin-20261031` READY was withdrawn at 05:10: its host region-lock preflight found the orchestrator venv Python absent; the earlier public control did not cover that real host lock branch. Its old model control remains historical. Corrected hostfix READY manifest SHA-256 `7c120e2d1891db71b4f069c92a2a737ac9dd6f30e436610a4b7e377cb90e39b9` includes actual host startup and lock proof plus public Qwen 0.6B normal control (rc0, 31.72 s) and STOP (rc75, drained); `spec-type none` exercises neither MTP nor the 35B full target. The original five-block decision plan, full target feasibility and CAFE scientific gate remain unrun. [Withdrawal and corrected capsule](../../artifacts/compute/codex3-fu03-r3-kpf-gpu-draft-20261031/cafe-hostfix/). [belief: cc]

### 2026-10-31 HOST lock qualification supersession

At 05:17 the owner withdrew the unarmed F1 independent and LEX2 dev-grid READY packets: their actual host chroot entry uses a canonical region-lock whose host venv interpreter is absent. Their prior controls remain historical evidence but do not qualify that host branch; no grant or native target exposure occurred. Corrected successors are in preparation. The LEX2 held-out engineering-only draft remains unexposed and had no READY. [Retraction receipt](../../artifacts/compute/codex3-fu03-r3-kpf-gpu-draft-20261031/host-lock-retractions.json). [belief: cc]

### 2026-10-31 #25592 HOST lock supersession

At 05:17 the owner withdrew the unarmed `codex3-dsc-25592-replay-20261031` READY after host preflight found its canonical region-lock interpreter absent. Earlier public controls remain historical, but did not qualify the real host branch; no grant or target exposure occurred. A corrected successor is in preparation; five selected sequences and seven unknown slots do not constitute a result. [Retraction receipt](../../artifacts/compute/codex3-fu03-r3-kpf-gpu-draft-20261031/host-lock-retractions.json). [belief: cc]

### 2026-10-31 SW-2 HOST lock supersession

At 05:17 the owner withdrew the unarmed `codex3-sw2-v9-clamp-20261031` READY after host preflight found its canonical region-lock interpreter absent. Earlier small-model controls remain historical but do not qualify that host branch; no grant or target exposure occurred. A corrected successor is in preparation; no current-production, v10 or SW-2 conclusion follows. [Retraction receipt](../../artifacts/compute/codex3-fu03-r3-kpf-gpu-draft-20261031/host-lock-retractions.json). [belief: cc]
