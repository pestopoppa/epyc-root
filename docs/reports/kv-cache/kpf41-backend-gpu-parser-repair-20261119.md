# KPF-41 backend GPU parser repair

Offline regression verdict: **PASS**, six tests, including full retained-r2 replay and refusal controls. The parser reconciles 5,207 selected cases: 2,978 supported OK, 2,229 unsupported, and 25 required shared-trunk cases OK. It accepts exactly 212 graph warmup complete/reset diagnostics. Original qualification r2 remains **INCONCLUSIVE** because post-run custody was not captured then; a check now cannot supply that missing historical warrant.

The corrected row is `kpf41-backend-gpu-qualification-r3-20261119`; it retains the same pinned kernel and five build artifact digests, adds strict interleaved parsing, and checks custody even when parsing fails. Publisher smoke is requested; its outcome is recorded below. Full GPU qualification requires the new granted run and a filed verdict.

Evidence in place:

- Original log: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r2-20261119/out/corpus.log`, SHA-256 `00f32fda75481a50e864a3bb5abb1597378768a3143d5b97bfd46b440cc48537`.
- Prior executed wrapper: same r2 directory, `job.py`, SHA-256 `1f93091859e5a1b7a5d89bce19b9e1d51a76956f2253622619ae409085785479`.
- New source: detached git worktree at `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r3-20261119/source`, commit `15caecbbf4cb27452dbd87fa1a68a0e75098388e`.
- New prepublication custody check returned rc0 (source clean/detached, five receipt hashes, own loader paths); this is input validation only.

Corrected packet files (repo-relative directory `docs/reports/kv-cache/kpf41-backend-gpu-qualification-draft-20261105`):

- `job.py`: SHA-256 `c5b689b5b16f09809c73bd06086f0dcbbf1f4e720536569c8999e4c60718b980`.
- `corpus_parser.py`: SHA-256 `3bf112be8214b2e2be9a91af79153d3b4f990e1febef9ac801286f4019afc185`.
- `test_corpus_parser.py`: SHA-256 `2340fec1d72841b224e8039ce675ff0b10f86e9a5e215d3cace40379db63acf5`.
- `runtime.sha256`: SHA-256 `7bdd80eba5fd7f54d65f6e94405c57e8c5111df51dd14e462866764be3f12f45`.
- `launch.sh`: SHA-256 `2fb9dbefd0e855d981c82120125ad6c8a6a9fbaa49a14bc8bdf0e4c45c8ee7bf`.
- `spec.json`: SHA-256 `3a817b6665cb71b47c6897876d06543bdab05fdb38bc1e2b4ea6aa3d79c9732b`.

Publisher outcome: first request was refused because the repair box is a non-inference deliverable. The measured successor now owns a separate explicit inference box, `KPF-41.BACKEND-GPU-R3-QUALIFICATION`, with the same kernel identity and stop contract. Publication with `ROWFLOW_REPO` set to the owning lane returned rc0: **GPU busy; smoke queued**. No smoke PASS, readiness or fresh GPU verdict is claimed. The publisher warned about the prose prerequisite; the explicit owner-applied decision rule remains unchanged.
