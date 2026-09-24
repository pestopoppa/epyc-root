# 2026-09-24 — Qwen-Image-2.1 production cutover and session wrap-up

- Removed the PhotoMaker V2 model stack and its test image as requested, reclaiming approximately 27 GB. Preserved ERNIE-Image-Turbo model files and its prior launcher for rollback.
- Switched orchestrator image generation to Qwen-Image-2.1, retaining the existing `image_generate` surface and sdapi-compatible service role on port 8190. Added an isolated CPU-only Diffusers environment/service and optional local reference-image conditioning. The launcher masks GPU visibility; no GPU was used.
- Reloaded the `sd_server` service and verified Qwen health/readiness on port 8190. No image-generation request was sent; generation remains under explicit operator control. The Qwen-vs-ERNIE matched-prompt comparison remains unrun.
- Verification: focused orchestrator tests passed (82); CPU environment dependency check, Python compilation, shell syntax, manifest load, and `git diff --check` passed. A broader runtime-facts test set had one unrelated stale topology failure: `test_runtime_facts_resolve_worker_logical_alias_to_physical_topology` expects removed `numa_instance` data for port 8072.
- Updated the orchestrator pipeline chapter and ERNIE evaluation handoff to record Qwen as production and ERNIE as rollback-only. README freshness check emitted no warnings.
- Disk availability rose from about 473 GB to about 498–500 GB after PhotoMaker removal and Qwen CPU environment setup. Exact free space varies with concurrent host activity.
