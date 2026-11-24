# intake-2864 — Sybil inference-optimisation skill vs the AutoKernel loop

Source @ `fda968e` (MIT), read in full. AK loop compared at epyc-inference-research `3ab8362e5` (`scripts/kernel_rnd/autokernel/loop/`), handoffs on origin/main.

| # | Learning | AK status | Evidence |
|---|---|---|---|
| 1 | Accept only if the candidate beats both neighbouring controls, ≤3% regression elsewhere | PRESENT (stronger) | alternating pairs, measured A/A floor, `MIN_PAIRS=5`, warmup pair (`bench.py:113-117`); non-regression refusal (`keep_screen.py:24-29`); MAD outlier guard (`serving.py:2543`) |
| 2 | 3-in-noise plateau with a STATUS block (best vs baseline vs ceiling, ranked remaining levers) | PARTIAL | per-family escape live (`actors.py:3305-3330`), same-state stop live (`same_state_stop.py`); campaign `PLATEAU_STOP` is specified (`autokernel-loop.md:2107`) but only a test references it; replay-only plateau stop (`exploration_policy_replay.py:163`) |
| 3 | No rerun of a rejected experiment without a new reason | PRESENT | `do_not_repeat` structural gate (`dispatch_guard.py:207-260`); `refused_at_formation` counts toward exhaustion (`actors.py:3268-3285`) |
| 4 | Progressive-disclosure references (context diet) | PRESENT | `actor_context.py:9-60` sections to files with TOC, short inline set |
| 5 | "Suspiciously fast = broken" output sanity | PARTIAL | numerics and graph-KLD gates exist; asserted roofline caps refused for lessons (`autokernel-loop.md:4094`); no pre-keep tripwire on a speedup above the op's roofline headroom |

Notes: the looping-output n-gram flag (`bench.py:100`) is serving-level; AK kernel keeps are judged by numerics, so it does not transfer directly. A PACEvolve plateau pack was declined 2026-11-03 (`autokernel-loop.md:4184`); the proposed plateau box only implements the already-specified stop.

Artifact audit: clean (`/mnt/raid0/llm/tmp/dive-sybil/`).
