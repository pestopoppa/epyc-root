#!/usr/bin/env python3
"""A9 stage 1 — gfx90a training-viability smoke, no-download tier.

Proves the gradient path end-to-end on MI210: autograd + LoRA adapters +
bf16 + AdamW, on a randomly-initialised Qwen2 of realistic shape. This
answers "can this hardware train at all", which is the W3 gate, without
depending on a network fetch.

Pre-registered decision rule (written BEFORE the run):
  PASS iff all four hold —
    1. every step executes on device (cuda:0), no CPU fallback
    2. LoRA params receive finite non-zero gradients on every step
    3. final-quintile mean loss < first-quintile mean loss by >= 20%
       on a synthetic task with a learnable pattern
    4. peak VRAM sampled DURING the run (external rocm-smi) > 0
  Any single failure = FAIL. No post-hoc rule changes.
"""
import json, os, sys, time
import torch
from transformers import Qwen2Config, Qwen2ForCausalLM
from peft import LoraConfig, get_peft_model

OUT = sys.argv[1] if len(sys.argv) > 1 else "/workspace/tmp/a9_stage1_result.json"
torch.manual_seed(42)

dev = torch.device("cuda:0")
assert torch.cuda.is_available(), "no ROCm device"

VOCAB, SEQ, BATCH, STEPS = 4096, 256, 8, 60

cfg = Qwen2Config(
    vocab_size=VOCAB, hidden_size=512, intermediate_size=1376,
    num_hidden_layers=8, num_attention_heads=8, num_key_value_heads=4,
    max_position_embeddings=SEQ, torch_dtype="bfloat16",
)
model = Qwen2ForCausalLM(cfg).to(dev, dtype=torch.bfloat16)

lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, bias="none",
                  target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                  task_type="CAUSAL_LM")
model = get_peft_model(model, lora)
trainable = [(n, p) for n, p in model.named_parameters() if p.requires_grad]
n_train = sum(p.numel() for _, p in trainable)
n_total = sum(p.numel() for p in model.parameters())

# Learnable synthetic task: token t is followed by (t*7+13) mod VOCAB.
# A model that learns anything at all drives loss well below ln(VOCAB)=8.32.
def batch():
    x = torch.randint(0, VOCAB, (BATCH, SEQ), device=dev)
    x[:, 1::2] = (x[:, 0::2] * 7 + 13) % VOCAB
    return x

opt = torch.optim.AdamW([p for _, p in trainable], lr=3e-4)
losses, devices_seen, grad_ok = [], set(), []

t0 = time.time()
for step in range(STEPS):
    ids = batch()
    out = model(input_ids=ids, labels=ids)
    loss = out.loss
    loss.backward()
    gnorm = torch.sqrt(sum((p.grad.float() ** 2).sum()
                           for _, p in trainable if p.grad is not None))
    grad_ok.append(bool(torch.isfinite(gnorm) and gnorm.item() > 0))
    opt.step(); opt.zero_grad(set_to_none=True)
    losses.append(loss.item())
    devices_seen.add(str(loss.device))
elapsed = time.time() - t0

q = max(1, STEPS // 5)
first_q, last_q = sum(losses[:q]) / q, sum(losses[-q:]) / q
drop = (first_q - last_q) / first_q

res = {
    "stage": "A9-stage1-random-init-lora-sft",
    "device_name": torch.cuda.get_device_name(0),
    "torch": torch.__version__, "hip": torch.version.hip,
    "params_total": n_total, "params_trainable": n_train,
    "trainable_pct": round(100 * n_train / n_total, 3),
    "steps": STEPS, "elapsed_s": round(elapsed, 2),
    "steps_per_s": round(STEPS / elapsed, 2),
    "devices_seen": sorted(devices_seen),
    "all_steps_on_device": devices_seen == {"cuda:0"},
    "all_grads_finite_nonzero": all(grad_ok),
    "loss_first_quintile": round(first_q, 4),
    "loss_last_quintile": round(last_q, 4),
    "loss_drop_frac": round(drop, 4),
    "loss_curve": [round(x, 4) for x in losses],
    "peak_vram_torch_mb": round(torch.cuda.max_memory_allocated() / 1e6, 1),
}
res["criteria"] = {
    "1_on_device": res["all_steps_on_device"],
    "2_grads_finite_nonzero": res["all_grads_finite_nonzero"],
    "3_loss_drop_ge_20pct": drop >= 0.20,
    "4_vram_external": "PENDING-external-sampler",
}
res["verdict_internal"] = all(v for k, v in res["criteria"].items() if k != "4_vram_external")

with open(OUT, "w") as f:
    json.dump(res, f, indent=2)
print(json.dumps({k: v for k, v in res.items() if k != "loss_curve"}, indent=2))
