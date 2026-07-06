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

## External Client Wiring

`scripts/hermes/reference_openai_client.py` is a safe, non-inference prep helper for plain OpenAI-compatible clients. It prints a copy-pastable cURL + Python `extra_body` example with Hermes `x_*` overrides (`x_orchestrator_role`, `x_max_escalation`, `x_disable_repl`, optional `x_force_model` / `x_show_routing`) and does not send traffic by default. It can also dry-run the quiet-window validation surface: `stream=true`, a demo native OpenAI tool schema, raw `tools` JSON, and `tool_choice`.

```bash
cd /mnt/raid0/llm/epyc-root/scripts/hermes
python3 reference_openai_client.py --print-only
python3 reference_openai_client.py --print-only --x-show-routing --stream --demo-tool

# Send a live request only when explicitly requested:
python3 reference_openai_client.py --send
```

`scripts/hermes/hermes_pin_audit.py` is the dry-run upstream-pin checklist. It reports the current Hermes checkout, remote target tag, dirty state, EPYC config assumptions, and smoke gates without fetching, checking out, installing, or launching services.

```bash
cd /mnt/raid0/llm/epyc-root
python3 scripts/hermes/hermes_pin_audit.py --target-tag v2026.7.1
```

## Style

- Be concise. Lead with the answer.
- Use box-drawing tables for benchmark results.
- Don't add emoji unless asked.
- When writing code: no over-engineering, no unnecessary abstractions.
