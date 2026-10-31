#!/usr/bin/env python3
"""Private PAW adapter: local immutable inputs, native compile server.

Draft only; do not schedule until artifact verification and lifecycle tests pass.
"""
import os
import sys
import json
import time
from dataclasses import replace
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["HIP_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "/mnt/raid0/llm/tmp/inf76-paw-runtime-20261029/vendor/server/src")

from paw_server.compile import pipeline, profiles
from transformers import AutoConfig, AutoTokenizer, StoppingCriteria, StoppingCriteriaList
import torch
threads = len(os.sched_getaffinity(0))
if not 0 < threads <= 24:
    raise SystemExit("unexpected CPU affinity")
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

COMPILER = Path("/mnt/raid0/llm/models/PAW-4B-Qwen3-0.6B-ae0f52b9")
STANDARD_PSEUDO = "/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507"
SMOKE_PSEUDO = "/mnt/raid0/llm/models/Qwen3-0.6B-PAW-smoke-c1899de"
PSEUDO = SMOKE_PSEUDO if os.environ.get("PAW_SMOKE_PSEUDO") == "1" else STANDARD_PSEUDO
print("pseudo_generator_scope", "smoke-only-qwen3-0.6b-max64" if PSEUDO == SMOKE_PSEUDO else "scheduled-qwen3-4b-max512", flush=True)
INTERPRETER = "/mnt/raid0/llm/models/Qwen3-0.6B-PAW-smoke-c1899de"

for p in (COMPILER / "meta.json", COMPILER / "lora_mapper.pt", COMPILER / "compiler/model.safetensors", Path(PSEUDO) / "config.json", Path(INTERPRETER) / "config.json"):
    if not p.is_file():
        raise SystemExit(f"missing pinned artifact: {p}")

profile = profiles.PROFILES[profiles.DEFAULT_COMPILER]
profiles.PROFILES[profiles.DEFAULT_COMPILER] = replace(profile, repo=str(COMPILER))
pipeline.PSEUDO_COMPILER_REPO = PSEUDO

def offloaded_model(repo, device, subfolder=None):
    if device != "cpu" or repo not in (PSEUDO, str(COMPILER)):
        raise RuntimeError("unexpected model or device")
    offload = Path(os.environ["PAW_OFFLOAD_DIR"]).resolve()
    if not offload.is_relative_to(Path("/mnt/raid0/llm/models/PAW-programs")):
        raise RuntimeError("offload directory outside canonical model store")
    offload = offload / ("pseudo" if repo == PSEUDO else "trained")
    offload.mkdir(parents=True, exist_ok=True)
    kwargs = {"dtype": torch.bfloat16, "device_map": "auto", "max_memory": {"cpu": "2GiB"}, "offload_folder": str(offload)}
    if subfolder is not None: kwargs["subfolder"] = subfolder
    model = pipeline.AutoModelForCausalLM.from_pretrained(repo, **kwargs)
    mapping = getattr(model, "hf_device_map", None)
    if mapping is None:
        devices = {str(parameter.device) for parameter in model.parameters()}
        if devices != {"cpu"}:
            raise RuntimeError(f"unexpected unmapped model devices: {devices}")
        mapping = {"": "cpu"}
    print("effective_model_device_map", repo, mapping, flush=True)
    if repo == PSEUDO:
        class Progress(StoppingCriteria):
            def __init__(self, prompt_length): self.prompt_length = prompt_length
            def __call__(self, input_ids, scores, **kwargs):
                event = {"monotonic_s":time.monotonic(),"generated_tokens":int(input_ids.shape[-1])-self.prompt_length}
                with open(os.environ["PAW_PROGRESS_LOG"], "a", encoding="utf-8") as out:
                    out.write(json.dumps(event,sort_keys=True)+"\n"); out.flush()
                return False
        original_generate=model.generate
        def observed_generate(*args,**kwargs):
            inputs=kwargs.get("input_ids")
            if inputs is None: raise RuntimeError("pseudo-generator input ids missing")
            criteria=StoppingCriteriaList(list(kwargs.get("stopping_criteria") or []))
            criteria.append(Progress(int(inputs.shape[-1])))
            kwargs["stopping_criteria"]=criteria
            return original_generate(*args,**kwargs)
        model.generate=observed_generate
    return model.eval()

pipeline._load_model = offloaded_model
if PSEUDO == SMOKE_PSEUDO:
    original_compile = pipeline.compile_spec
    def smoke_compile(*args, **kwargs):
        kwargs["max_new_tokens"] = 64
        return original_compile(*args, **kwargs)
    pipeline.compile_spec = smoke_compile

def local_hub(repo, filename, *args, **kwargs):
    if repo != str(COMPILER) or filename not in ("meta.json", "lora_mapper.pt"):
        raise RuntimeError(f"unexpected hub request: {repo!r} {filename!r}")
    return str(COMPILER / filename)

pipeline.hf_hub_download = local_hub
config_load = AutoConfig.from_pretrained
tokenizer_load = AutoTokenizer.from_pretrained

def local_id(name):
    return INTERPRETER if name == "Qwen/Qwen3-0.6B" else name

AutoConfig.from_pretrained = lambda name, *a, **kw: config_load(local_id(name), *a, **kw)
AutoTokenizer.from_pretrained = lambda name, *a, **kw: tokenizer_load(local_id(name), *a, **kw)

from paw_server import store
expected_bundle_files = {"adapter.gguf", "prompt_template.txt", "meta.json", "pseudo_program.txt", "adapter_config.json"}
if set(store.BUNDLE_FILES) != expected_bundle_files:
    raise RuntimeError("upstream bundle file contract changed")
# Preserve adapter_config.json in the native program directory; current SDK
# local import accepts only its explicitly listed inert GGUF bundle members.
store.BUNDLE_FILES = [name for name in store.BUNDLE_FILES if name != "adapter_config.json"]
from paw_server.cli import main
main()
