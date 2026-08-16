# Inference progress — 2026-08-16

## AutoKernel planner-conditioning v3

- Promoted the complete AutoKernel research line to `epyc-inference-research` `main` through merge
  `0d701b9ae6717821f4728a62897b73773f63c874`. The final reviewed product tip is
  `6807a0b1034de7aab751f65e40084463dc0d9015`.
- Sealed and validated the fresh bundle
  `/mnt/raid0/llm/autokernel/deployments/gpu-discovery-quant-ladder-occupancy-v3`, graph SHA-256
  `31af931de1da453cf7c28c450de301b7db89c13cd58a1064d512390a514bd4a2`.
  Validate-only reported `inference_executed=false`.
- The merged-tree hardware-free gate passed **303/303**, with three expected failures documenting the
  intentionally future AK-ADM-1 machine-policy work. Portfolio validation passed with 21 hypotheses,
  22 DNR records, 29 immutable evidence carriers, and the same exact four eligible hypotheses.
- The planner is `gpt-5.6-sol/high`; the independent critic is `claude-fable-5/high`. Both receive the
  complete sealed planner context. The dashboard now exposes bounded AutoKernel and planner activity
  through `/api/kernel/live`; it correctly reports inactive while no campaign owns the controller lock.

## Planner memory and governance

- Preserved the non-governed Goedel-8B quant-ladder measurements from root commit
  `9e21451c5680d10eae7b577979a9e78b39d27eed` as `non_governed_design_prior`, not promotion evidence.
  The IQ2 production lever now has the threshold target that determines value: at most 64 true and
  allocated VGPR, eight waves/SIMD, zero scratch and zero spill. Landing at 65–70 VGPR is not a win.
- Recorded IQ1_S as an inactive, zero-spend counterfactual. The operator explicitly does not need an
  IQ1 run; no model was built or retained and no GPU work was scheduled from this evidence.
- Added exact Q4_K MMQ baseline-correctness memory: stock 18/43 versus the 43/43 control, two 25-failure
  negatives, and a 172/172 diagnostic repair that cannot unlock authoring until it has a committed
  clean source identity. Added the exact Q8 integer-native DP4A DNR, the latent IQ-residency tripwire,
  and exact-instantiation/phase/tool-execution evidence traps.
- Kept the current spend set unchanged: Q5 type-specific dequant, a genuinely new Q8 quantizer
  mechanism, production-shape FA/GQA7, and RMS direct load/reduction.

## Runtime and next actions

- No model inference, kernel build, profiler run, or GPU campaign ran during this wrap-up.
- The next live launch is deliberately a fresh v3 state root. Its concrete external prerequisite is a
  working Docker socket in this devcontainer followed by exact inspection of the pinned planner image;
  production/instrument identities and GPU availability must then revalidate.
- Before a long campaign, AK-RSM-1 owns durable per-stage receipts plus graceful stop/resume. AK-ADM-1
  owns typed pre-model enforcement of the six currently prompt-bound limitations. RVP-C2-6d owns the
  clean Q4_K qsum source identity and unchanged 172/172 rerun. C5-3 still requires a live 193-workload
  correctness-only run; C5-5 still requires the joined `sol_execbench_problem_id` corpus field.
