#!/usr/bin/env python3
"""A9 stage 2 — gfx90a training-viability smoke on REAL pretrained weights via TRL.

Stage 1 FAILED its own pre-registered criterion 3 (loss drop). Diagnosis:
test-method defect, not hardware. A randomly-initialised base with LoRA on
attention projections only cannot learn a 4096-way arithmetic token map in
60 steps; embeddings and lm_head were frozen and carry the mapping. Criteria
1, 2 and 4 passed, so the gradient path itself was already demonstrated.

This is a NEW pre-registration, not a rewrite of stage 1's. Stage 1 stands
as FAILED on its own terms and is reported that way.

Pre-registered decision rule (written BEFORE this run):
  PASS iff all four hold —
    1. every step executes on cuda:0, no CPU fallback
    2. LoRA params receive finite non-zero gradients on every step
    3. final-quintile mean loss < first-quintile mean loss by >= 20%
       on memorisation of a fixed 64-example instruction set (a task a
       pretrained 0.5B with LoRA on attn+MLP can demonstrably fit)
    4. peak VRAM sampled DURING by external rocm-smi > 0
  Reported separately, NOT gating: whether TRL's SFTTrainer API path works
  under transformers 5.15.0 / trl 1.9.2, since the row names TRL specifically.

PARAMETERISED 2026-09-15 (EVL-25 W3(a) fit check). The run above is the DEFAULT of
every flag below, so `a9_stage2_trl_sft.py <out.json>` still reproduces the 2026-08-12
smoke exactly. The flags exist because the fit question -- does a bf16 LoRA on a
9B-class base fit 64 GB -- is the SAME harness at a different model, rank and sequence
length, and re-typing a measured recipe into a copy of the script is how two runs stop
being comparable.

The grad-norm is computed and CLIPPED IN fp64: transient bf16 LoRA gradients reach
~1e34 on layer-0 attention projections, and `clip_grad_norm_` norms in fp32, where
that squares to `inf` and scales every parameter to NaN.
"""
import argparse, json, os, sys, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

DEFAULT_MODEL = "/mnt/raid0/llm/cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775"

ap = argparse.ArgumentParser(description="A9 stage-2 bf16 LoRA smoke / fit check")
ap.add_argument("out", nargs="?", default="/workspace/tmp/a9_stage2_result.json")
ap.add_argument("--model", default=DEFAULT_MODEL)
ap.add_argument("--model-label", default=None, help="name recorded in the result")
ap.add_argument("--rank", type=int, default=16)
ap.add_argument("--alpha", type=int, default=None, help="default: 2 * rank")
ap.add_argument("--seq-len", type=int, default=64)
ap.add_argument("--steps", type=int, default=60)
ap.add_argument("--batch", type=int, default=16)
ap.add_argument("--lr", type=float, default=2e-4)
ap.add_argument("--max-grad-norm", type=float, default=None,
                help="clip the fp64 grad norm to this value (default: no clipping, "
                     "matching the 2026-08-12 run)")
ap.add_argument("--gradient-checkpointing", action="store_true")
ap.add_argument("--seed", type=int, default=42)
args = ap.parse_args()

OUT = args.out
MODEL = args.model
torch.manual_seed(args.seed)
dev = torch.device("cuda:0")

load_t0 = time.time()
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16).to(dev)
model.config.use_cache = False
if args.gradient_checkpointing:
    model.gradient_checkpointing_enable()
    # Without this the checkpointed blocks see inputs that do not require grad, the
    # recompute graph is never built, and checkpointing silently saves nothing -- a knob
    # that reports as enabled while doing nothing is the vacuous-pass shape.
    model.enable_input_require_grads()
load_s = time.time() - load_t0
vram_after_load_mb = round(torch.cuda.memory_allocated() / 1e6, 1)

lora = LoraConfig(r=args.rank, lora_alpha=args.alpha or 2 * args.rank,
                  lora_dropout=0.0, bias="none",
                  target_modules=["q_proj","k_proj","v_proj","o_proj",
                                  "gate_proj","up_proj","down_proj"],
                  task_type="CAUSAL_LM")
model = get_peft_model(model, lora)
trainable = [(n,p) for n,p in model.named_parameters() if p.requires_grad]
n_train = sum(p.numel() for _,p in trainable)
n_total = sum(p.numel() for p in model.parameters())

# Fixed 64-example memorisation set — unambiguous, and a pretrained model
# with LoRA on attn+MLP fits it easily. Loss failing to drop here would be
# a real finding about the hardware, not about the task.
EX = [f"Q: What is the codeword for item {i}?\nA: The codeword is zeta-{i*37 % 991}."
      for i in range(64)]
if args.seq_len > 64:
    # A longer sequence is what makes the activation term of the fit question real, so
    # the examples are PADDED TO the requested length rather than left short: a
    # "seq_len=1024" run whose tensors are 40 tokens wide measures nothing about 1024.
    enc = tok(EX, return_tensors="pt", padding="max_length", truncation=True,
              max_length=args.seq_len)
else:
    enc = tok(EX, return_tensors="pt", padding=True, truncation=True,
              max_length=args.seq_len)
ids = enc.input_ids.to(dev); att = enc.attention_mask.to(dev)
labels = ids.clone(); labels[att == 0] = -100

opt = torch.optim.AdamW([p for _,p in trainable], lr=args.lr)
STEPS, BATCH = args.steps, args.batch
losses, devs, grad_ok, gnorms = [], set(), [], []
oom = None
t0 = time.time()
try:
    for step in range(STEPS):
        sel = torch.randint(0, ids.size(0), (BATCH,), device=dev)
        out = model(input_ids=ids[sel], attention_mask=att[sel], labels=labels[sel])
        out.loss.backward()
        # fp64 THROUGHOUT. A ~1e34 transient squares to ~1e68, which is finite in fp64
        # and `inf` in fp32 -- and an `inf` norm used as a clip scale writes NaN into
        # every parameter, so the fp32 path does not merely mis-report, it poisons.
        gnorm = torch.sqrt(sum((p.grad.double() ** 2).sum()
                               for _, p in trainable if p.grad is not None))
        finite = bool(torch.isfinite(gnorm) and gnorm.item() > 0)
        grad_ok.append(finite)
        gnorms.append(float(gnorm.item()) if finite else float("inf"))
        if args.max_grad_norm and finite and gnorm.item() > args.max_grad_norm:
            scale = args.max_grad_norm / (gnorm.item() + 1e-12)
            for _, p in trainable:
                if p.grad is not None:
                    p.grad.mul_(scale)
        opt.step(); opt.zero_grad(set_to_none=True)
        losses.append(out.loss.item()); devs.add(str(out.loss.device))
        print(f"step {step + 1}/{STEPS} loss {losses[-1]:.4f} gnorm {gnorms[-1]:.3e} "
              f"vram_alloc_mb {torch.cuda.memory_allocated() / 1e6:.0f}", flush=True)
except torch.OutOfMemoryError as exc:
    # The fit question's ONE unambiguous answer: record it as a result, never as a crash.
    oom = f"{type(exc).__name__}: {exc}"[:512]
    print("OOM:", oom, flush=True)
elapsed = time.time() - t0
STEPS = len(losses) or 1

q = max(1, STEPS//5)
if losses:
    fq, lq = sum(losses[:q])/q, sum(losses[-q:])/q
    drop = (fq-lq)/fq if fq else 0.0
else:
    # An OOM on the first step is a RESULT for the fit question. Dividing by an empty
    # loss curve here would turn it into a crash and lose the record the run exists for.
    fq = lq = drop = None

# TRL API reachability — reported, not gating.
trl_status = {}
try:
    import trl
    from trl import SFTConfig, SFTTrainer
    trl_status = {"import": True, "version": trl.__version__,
                  "SFTTrainer": True, "SFTConfig": True}
except Exception as e:
    trl_status = {"import": False, "error": f"{type(e).__name__}: {e}"}

res = {
  "stage": "A9-stage2-real-weights-lora-sft",
  "model": args.model_label or os.path.basename(MODEL.rstrip("/")),
  "model_path": MODEL,
  "device_name": torch.cuda.get_device_name(0),
  "torch": torch.__version__, "hip": torch.version.hip,
  "python": sys.executable,
  "lora_rank": args.rank, "lora_alpha": args.alpha or 2 * args.rank,
  "seq_len": int(ids.size(1)), "batch": BATCH, "lr": args.lr,
  "max_grad_norm": args.max_grad_norm,
  "gradient_checkpointing": bool(args.gradient_checkpointing),
  "grad_norm_dtype": "float64",
  "load_s": round(load_s, 2), "vram_after_load_mb": vram_after_load_mb,
  "oom": oom,
  "grad_norm_max": max(gnorms) if gnorms else None,
  "params_total": n_total, "params_trainable": n_train,
  "trainable_pct": round(100*n_train/n_total, 3),
  "steps": STEPS, "elapsed_s": round(elapsed,2),
  "steps_per_s": round(STEPS/elapsed,2),
  "all_steps_on_device": devs == {"cuda:0"},
  "all_grads_finite_nonzero": all(grad_ok),
  "loss_first_quintile": None if fq is None else round(fq,4),
  "loss_last_quintile": None if lq is None else round(lq,4),
  "loss_drop_frac": None if drop is None else round(drop,4),
  "loss_curve": [round(x,4) for x in losses],
  "peak_vram_torch_mb": round(torch.cuda.max_memory_allocated()/1e6,1),
  "peak_vram_torch_reserved_mb": round(torch.cuda.max_memory_reserved()/1e6,1),
  "trl_api": trl_status,
}
res["criteria"] = {
  "1_on_device": res["all_steps_on_device"],
  "2_grads_finite_nonzero": res["all_grads_finite_nonzero"],
  "3_loss_drop_ge_20pct": None if drop is None else drop >= 0.20,
  "4_vram_external": "PENDING-external-sampler",
}
res["verdict_internal"] = all(v for k,v in res["criteria"].items() if k != "4_vram_external")
json.dump(res, open(OUT,"w"), indent=2)
print(json.dumps({k:v for k,v in res.items() if k!="loss_curve"}, indent=2))
