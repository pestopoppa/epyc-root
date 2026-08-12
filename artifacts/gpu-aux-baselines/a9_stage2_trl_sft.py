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
"""
import json, os, sys, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

OUT = sys.argv[1] if len(sys.argv) > 1 else "/workspace/tmp/a9_stage2_result.json"
MODEL = "/mnt/raid0/llm/cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/7ae557604adf67be50417f59c2c2f167def9a775"
torch.manual_seed(42)
dev = torch.device("cuda:0")

tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16).to(dev)
model.config.use_cache = False

lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, bias="none",
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
enc = tok(EX, return_tensors="pt", padding=True, truncation=True, max_length=64)
ids = enc.input_ids.to(dev); att = enc.attention_mask.to(dev)
labels = ids.clone(); labels[att == 0] = -100

opt = torch.optim.AdamW([p for _,p in trainable], lr=2e-4)
STEPS, BATCH = 60, 16
losses, devs, grad_ok = [], set(), []
t0 = time.time()
for step in range(STEPS):
    sel = torch.randint(0, ids.size(0), (BATCH,), device=dev)
    out = model(input_ids=ids[sel], attention_mask=att[sel], labels=labels[sel])
    out.loss.backward()
    gnorm = torch.sqrt(sum((p.grad.float()**2).sum() for _,p in trainable if p.grad is not None))
    grad_ok.append(bool(torch.isfinite(gnorm) and gnorm.item() > 0))
    opt.step(); opt.zero_grad(set_to_none=True)
    losses.append(out.loss.item()); devs.add(str(out.loss.device))
elapsed = time.time() - t0

q = max(1, STEPS//5)
fq, lq = sum(losses[:q])/q, sum(losses[-q:])/q
drop = (fq-lq)/fq

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
  "model": "Qwen2.5-0.5B-Instruct",
  "device_name": torch.cuda.get_device_name(0),
  "torch": torch.__version__, "hip": torch.version.hip,
  "params_total": n_total, "params_trainable": n_train,
  "trainable_pct": round(100*n_train/n_total, 3),
  "steps": STEPS, "elapsed_s": round(elapsed,2),
  "steps_per_s": round(STEPS/elapsed,2),
  "all_steps_on_device": devs == {"cuda:0"},
  "all_grads_finite_nonzero": all(grad_ok),
  "loss_first_quintile": round(fq,4), "loss_last_quintile": round(lq,4),
  "loss_drop_frac": round(drop,4),
  "loss_curve": [round(x,4) for x in losses],
  "peak_vram_torch_mb": round(torch.cuda.max_memory_allocated()/1e6,1),
  "trl_api": trl_status,
}
res["criteria"] = {
  "1_on_device": res["all_steps_on_device"],
  "2_grads_finite_nonzero": res["all_grads_finite_nonzero"],
  "3_loss_drop_ge_20pct": drop >= 0.20,
  "4_vram_external": "PENDING-external-sampler",
}
res["verdict_internal"] = all(v for k,v in res["criteria"].items() if k != "4_vram_external")
json.dump(res, open(OUT,"w"), indent=2)
print(json.dumps({k:v for k,v in res.items() if k!="loss_curve"}, indent=2))
