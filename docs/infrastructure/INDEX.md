# Infrastructure Documentation

Cross-cutting hardware and storage documentation for the EPYC platform.

## Chapters

| # | Title | Key Topics |
|---|-------|------------|
| [01](01-hardware-system.md) | Hardware System (EPYC 9655) | CPU topology, ~460 GB/s bandwidth, 1.13TB RAM, thermal |
| [02](02-storage-safety.md) | Storage Architecture & Safety | RAID0 layout, filesystem rules, 192-thread memory safety |

## Related references

- **CPU speech vs CPU LLM core contention, and the MI210 constraints for voice work** (STT/TTS placement, `-t 96`
  collapse, partition numbers, :8083 np4/kvu capacity): [`../reference/speech/cpu-speech-contention-20260924.md`](../reference/speech/cpu-speech-contention-20260924.md)

## Cross-Repository Documentation

- **Orchestration architecture** (routing, memory, tools, server stack): epyc-orchestrator `docs/chapters/`
- **Inference optimization** (speculative decoding, MoE, radix attention): epyc-inference-research `docs/chapters/`
- **llama.cpp toolchain** (worktrees, production branch, build flags): epyc-llama `docs/epyc/`
