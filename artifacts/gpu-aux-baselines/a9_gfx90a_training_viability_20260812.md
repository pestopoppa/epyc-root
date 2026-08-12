# A9 — gfx90a training-viability smoke (MI210, 2026-08-12)

**Status: PASS**, with one numerical caveat that is load-bearing for W3(a).
Row: `handoffs/active/frontier-f3-data-flywheel.md:33` (W3 training-viability gate).
Classification: **OBSERVATION** per MEASUREMENT.md — no protocol entry exists for
training-viability, so no cell here is decision-gating.

## Correction of the record

A previous session reported A9 as **hard-blocked, "no PyTorch on the host"**. That was
**wrong**. The absence proof used `find / -maxdepth 6`, which cannot reach a venv
`site-packages` (depth 8+), and probed only two interpreters. The stack was present the
whole time:

- `/mnt/raid0/llm/tools/geak-v1-rocm62-py312` — torch `2.5.1+rocm6.2`, HIP `6.2.41133-dd7f95766`,
  `torch.cuda.is_available()==True`, `gfx90a` in `get_arch_list()`, trl `1.9.2`, peft `0.20.0`,
  transformers `5.15.0`, accelerate `1.14.0`
- second ROCm venv: `/mnt/raid0/llm/tools/apex-rocm62-venv` (same torch build)
- ROCm `6.2.0-66`

Absent: `bitsandbytes` (so 4-bit QLoRA specifically is not yet runnable; LoRA/SFT/GRPO are),
`verl`. UNSEARCHED: `/root` (permission denied) — reported as unknown, not empty.

**The W3 row names only a HW gate (cleared 07-02) and a DATA gate (satisfied). It never named
a software gate.** The blocker was never a missing measurement, and it was never a missing
dependency either — it was a false negative in a search.

## Stage 1 — random-init Qwen2, LoRA on attention. FAILED its pre-registered rule.

Pre-registered before the run: (1) all steps on `cuda:0`; (2) finite non-zero LoRA gradients
every step; (3) final-quintile loss ≥20% below first-quintile; (4) external rocm-smi VRAM > 0.

Result: 1, 2, 4 PASS. **3 FAILS** — loss `8.4203 → 8.4197`, drop 0.01%, against `ln(4096)=8.317`.
27.9M params, 458,752 trainable (1.65%), 60 steps in 5.75 s (10.4 steps/s), 775 MB peak VRAM,
GPU sampled at 99% during.

Diagnosis: **test-method defect, not hardware.** The synthetic task (`t → (t*7+13) mod 4096`)
is a 4096-way arithmetic map that lives in the embedding and `lm_head`, both frozen; LoRA on
attention projections of an untrained base cannot express it in 60 steps. Recorded as FAILED on
its own terms; not retro-scored.

## Stage 2 — real Qwen2.5-0.5B-Instruct, LoRA on attn+MLP. New pre-registration.

502.8M params, 8,798,208 trainable (1.75%), 60 steps in 8.18 s (7.3 steps/s), 2,984 MB peak
torch VRAM, external rocm-smi 100% GPU / 6% VRAM sampled **during** the run.

| Criterion | Result |
|---|---|
| 1 — all steps on `cuda:0` | **PASS** |
| 2 — finite non-zero grads every step | **FAIL as written** (see below) |
| 3 — loss drop ≥ 20% | **PASS** — `0.9174 → 0.4077`, **55.6%** |
| 4 — external VRAM > 0 during run | **PASS** — 5 non-zero samples, peak 100% GPU util |

TRL API reachable under transformers 5.15.0: `SFTTrainer` and `SFTConfig` both import.

### Criterion 2: the instrument was the defect, and the finding underneath it is real

The failure was 2 steps of 60 (21 and 53), where the gradient norm read `inf`. Direct
measurement of the gradients themselves:

```
step 21: all grad elements finite = True
         max |grad| = 1.975692e+34  (layers.0.self_attn.v_proj.lora_B)
         fp64 gnorm = 1.301715e+35  finite = True
step 53: all grad elements finite = True
         max |grad| = 7.696346e+22  (layers.0.self_attn.q_proj.lora_B)
         fp64 gnorm = 4.941604e+23  finite = True
```

`inf` came from **my own metric**: `(p.grad.float()**2).sum()` squares 1.98e34 to 3.9e68,
which overflows fp32 (max 3.4e38). Every gradient element was finite. Re-measured in fp64,
criterion 2 passes at every step.

**Declared explicitly: the instrument was changed after the pre-registered rule failed.**
Stage 2 is reported as FAILED-as-written and PASSING-on-remeasurement, not as a clean pass.

**The underlying spike is a genuine finding and a trap for W3(a).** Transient bf16 LoRA
gradients reach ~1e34 on layer-0 attention projections while loss converges normally —
AdamW is per-parameter scale-invariant, so a huge gradient still yields a bounded step.
But `torch.nn.utils.clip_grad_norm_` computes its norm in fp32 and **would return `inf` here**,
which propagates a NaN/zero scale factor into every parameter. Any QLoRA/SFT run on this stack
that enables gradient clipping naively will silently destroy the update. Recommend fp64 or
per-tensor clipping for W3(a).

## Verdict

**gfx90a is training-viable.** Autograd, LoRA adapters, bf16, AdamW and the TRL API path all
execute on the MI210 with device residency proven by external sampling during the run.
The W3 training-viability gate is met for LoRA/SFT. Not yet demonstrated: GRPO end-to-end,
and 4-bit QLoRA (needs `bitsandbytes`, absent).

Harnesses: `/workspace/tmp/a9_stage1_lora_smoke.py`, `/workspace/tmp/a9_stage2_trl_sft.py`,
runner `/workspace/tmp/a9_run_stage1.sh`. Raw: `a9_stage{1,2}_result.json`,
`a9_stage{1,2}_vram_samples.txt`.
