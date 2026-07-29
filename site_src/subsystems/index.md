# Subsystems

Pedagogical walkthroughs of the production stack. These are the **how it's built** chapters, complementing the **what we learned** topic articles.

Two repos, two chapter sets.

## Orchestrator

Production multi-tier inference platform — routing, escalation, REPL environment, MemRL, calibration, SkillBank, tool registries. The runtime substrate that turns 9 llama-server instances + 2 auxiliary services into a single coherent system.

**Read these for**: how a request actually flows; how escalation decisions are made; how the autopilot continuously optimizes; how the REPL environment integrates tools and structured outputs; how memory and calibration work.

Source: [pestopoppa/epyc-orchestrator](https://github.com/pestopoppa/epyc-orchestrator)

## Research

Benchmark infrastructure, model evaluation, and inference-optimization research. The substrate that produces every measurement and every model swap.

**Read these for**: how the 30+ eval suites are constructed; how speculative decoding, MoE optimization, prompt lookup, and RadixAttention are evaluated; what we deprecated and why; how the canonical benchmark protocol works; how to size a model for the hardware.

Source: [pestopoppa/epyc-inference-research](https://github.com/pestopoppa/epyc-inference-research)

---

Pick a subsystem from the left nav. For research deep-dives on specific papers and techniques, see [Deep-Dives](../deep-dives/index.md). For domain syntheses, see [Topics](../topics/index.md).
