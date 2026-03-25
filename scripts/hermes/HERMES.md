# EPYC Workstation

You are running on an EPYC 9655 workstation (96 cores, 768 GB RAM) dedicated to local LLM inference research and orchestration.

## Key Paths

| Purpose | Path |
|---------|------|
| LLM root | `/mnt/raid0/llm` |
| Governance repo | `/mnt/raid0/llm/epyc-root` |
| Orchestrator | `/mnt/raid0/llm/epyc-orchestrator` |
| Research & benchmarks | `/mnt/raid0/llm/epyc-inference-research` |
| llama.cpp fork | `/mnt/raid0/llm/llama.cpp` |
| Model storage | `/mnt/raid0/llm/lmstudio/models` |
| Temp/scratch | `/mnt/raid0/llm/tmp` |

## Conventions

- All data lives on `/mnt/raid0/` (NVMe RAID-0). Root SSD is 120 GB — never write large files to `~/` or `/tmp`.
- Model registry: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`
- Progress logs: `/mnt/raid0/llm/epyc-root/progress/YYYY-MM/YYYY-MM-DD.md`
- Handoffs: `/mnt/raid0/llm/epyc-root/handoffs/active/`

## Running Services

- **Orchestrator** (when active): ports 8080-8095 (llama-servers), 8000 (API)
- **Hermes backend** (when active): port 8099 (standalone llama-server)
- Check what's running: `ss -tlnp | grep -E '80[0-9]{2}'`

## Style

- Be concise. Lead with the answer.
- Use box-drawing tables for benchmark results.
- Don't add emoji unless asked.
- When writing code: no over-engineering, no unnecessary abstractions.
