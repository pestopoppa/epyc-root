# KPF-18 group-3: diagnostic native source rebinding

On 2026-11-04, `scripts/coordination/kvfork/kpf18-g3-custody/rebind_manifest.py` accepted all 52 entries of the isolated candidate's retained `NATIVE-SOURCES.sha256` after path rebinding. It checked each selected regular file against the original pinned SHA-256 and rejected symlink traversal. The [diagnostic manifest](NATIVE-SOURCES-diagnostic.sha256) has SHA-256 `a6c67a712fc36568e2f4120c90a623f5817becdbe7f083c38cdd0323f9d9c032`; the [mapping](rebinding.json) has SHA-256 `7bb9dc296dac7d871a3e33a9771cf3e9b080c81c243f456cb5da5a7176b896f3`. Both preserve absolute paths of the checked snapshot; scratch paths can later disappear or change and must be revalidated before use.

Historical bytes were materialized individually with `git show` into `/mnt/raid0/llm/tmp/kvfork/g3-custody/historical/`, without copying a checkout. Their original manifest digests matched:

- `epyc-orchestrator`: `src/runtime/region_lock_cli.py` at `9dbcc8fb17427320a3d0a7815b00e62f29aa0c35`; `cpu_region_lock.py`, `gpu_quiet_lock.py`, and `lock_queue.py` at `11e6d867890952c01bcad367e931f86f5520df02`; `instance_topology.py` at `4ae008a826198808a158b3a2a22e090763f3f107`; and `scripts/region-lock` at `c5dc4ae5e99a30636d6c4307f4f0acf2c2e59fa4`.
- Root `scripts/vidya/adapters/README.md` at `8a640317ed024745f294d11c5c88887270fddd07`.
- `grant_ok.sh` and `grant_ok_launcher.py` from `/mnt/raid0/llm/tmp/codex-ni-20261026-launch-admission-gate/baseline/`; three missing gate files from the isolated candidate, and three Vidya Python files from the retained R16 export, as identified by the mapping.

This establishes only a diagnostic, relocated source-byte inventory. The disabled launcher does not consume this manifest; no integration, current lock semantics, grant, cancellation, output supervision, GPU smoke, inference or correctness verdict follows. In particular, matching old lock bytes does not authorize their substitution into a live launcher. The original manifest and launcher were not modified, and no binaries are copied into this report.
