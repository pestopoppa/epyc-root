# Inference serving launch support — 2026-11-06

- Owner: operator-support session (`inference-serving-20261106`).
- Task: provide manual GPU/CPU launch commands for C6 champion-candidate models
  outside the frozen production stack; check the operator-launched Q38FN CPU server.
- Champion: C6 `65da39eb1`; CPU store `cpu-20261105-65da39eb1-c6fold2`, GPU store
  `gpu-20261106-65da39eb1-c6fold2`; `llama-server` 10512.
- Outcome: success for command provision and live check; one launch defect found.
- Live check: `:8074` PID 1344098 healthy; Q38FN UD-IQ4_XS, `n_ctx=8192`, one slot;
  MTP active (`draft_n=11`, `draft_n_accepted=9`). Process was affinity-bound to CPU 0
  only (`Cpus_allowed_list: 0`) instead of `0-95`; no kill/restart performed.
- Context finding: canonical Q38FN benchmark recipe `-c 8192` is too small for
  OpenCode; 16,450-token request triggered compaction. Serving variants use
  `-np 4 -c 262144` (Q38FN/27B) or `-np 4 -c 786432` (35B long-context GPU).
- Recipes: `epyc-inference-research/artifacts/serving-recipes/` and
  `scripts/benchmark/m12_launch_argv.py`; Q38FN CPU recipe under
  `autokernel/campaigns/ak-q38fn-cpu-decode-20261003/inputs/`.
- No kernel build, no model change, no measurement claim, no production cutover, no
  commit. Progress entry: `progress/2026-11/2026-11-06-inference-serving-launch.md`.
- **Correction (2026-11-06 review, live PID 1394163):** the `Cpus_allowed_list: 0`
  reading is the main thread only. The C6 process has 47 compute threads masked
  `2..94` at ~4720% CPU; `taskset -c 0-95` is working. Do not treat this as a launch
  defect. Full review: `progress/2026-11/2026-11-06-inference-serving-launch.md`.
- **Final matrix (2026-11-06, exploratory):** CPU Q38FN 8k 46.98; 28k prose 16.07
  (MTP acceptance 0.37-0.48); 54k **t96+MTP 16.05** vs t48 14.29; t96/no-MTP
  12.86; t48/no-MTP 15.07. Matched code prompt 8k **29.35/30.26**, 16k
  **29.37/29.86** (acceptance 0.860/0.947); 28k code arms invalid (EOS first
  token). GPU 27B DFlash2 at 54k: f16/n8 np1/np2/np4 42.8-43.8; q8/n7 40-42;
  16k reference 71.06. Artifact
  `artifacts/compute/local-launch-optimization-20261106/`. Launcher
  `scripts/session/launch_local_inference.sh` defaults CPU t96+MTP/np4/262k/f16,
  GPU np4/262k/f16/n8/cache. Host left free; no llama-server; all locks released.
