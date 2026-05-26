# Stories

The narrative layer. Each page picks a thread that runs across the codebase — a feature, an investigation, a falsification — and tells it as a story, with concrete numbers and links to the chapters and topic articles for depth.

If [Topics](../topics/index.md) tells you *what we learned* and [Subsystems](../subsystems/index.md) tells you *how it's built*, this section tells you *what happened and why*.

## Features & systems

- [How a request flows through the stack](how-a-request-flows.md) — cross-repo system tour from HTTP handler to model response
- [Why CPU-only inference is viable on EPYC](why-cpu-inference.md) — the bandwidth math, the NUMA story, the runtime stack
- [The autonomous research loop](autonomous-research-loop.md) — intake → deep-dives → wiki → AutoPilot, end to end

## Specific wins

- [Worker_general: 17 → 76 t/s](worker-general-story.md) — what cascaded when we swapped a 7B for a 26B (and gained throughput)

## Investigations

- [The speculative decoding investigation](spec-decoding-investigation.md) — what worked, what didn't, why the GPU literature doesn't transfer

## Live work

- [What we're investigating now](investigating-now.md) — curated snapshot of the active work queue
- [What we tried and ruled out](ruled-out.md) — falsified hypotheses with the measurements that killed them
