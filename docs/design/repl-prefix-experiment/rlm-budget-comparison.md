# RLM budget comparison

Compared against orchestrator source commit `9e138e3a3e22ecf8c57cd5bf50beed571d107b54` on 2026-11-02. These are source defaults, not proof of a running process's settings. The reference values are the RLM budget constants recorded in the REPL turn-efficiency handoff; no performance or quality conclusion follows from this comparison.

| Dimension | RLM reference | EPYC source at the pinned commit |
|---|---|---|
| Recursion | Exactly 1 | `LLMConfig.max_recursion_depth` defaults to 5; `llm_call` checks the configured limit (`src/config/models.py`, `src/llm_primitives/primitives.py`). |
| REPL output to root | 8,192 characters per turn | `REPLConfig.output_cap` defaults to 8,192 characters. The normal overflow path spills full output to a file and returns a summary; the experimental context arm bypasses that cap (`src/repl_environment/types.py`, `src/repl_environment/environment.py`). The separate LLM sub-call output cap is also 8,192 by default and is a different setting. |
| REPL execution timeout | 120 seconds; 300 and 600 showed no benefit in the reference | `REPLConfig.timeout_seconds` reads the registry's `repl.session`, with a 600-second fallback; the pinned registry sets 600. A separate `REPLConfigData.timeout_seconds` has an environment-configurable default of 30 seconds. These separate configuration surfaces must not be conflated (`src/repl_environment/types.py`, `src/config/__init__.py`, `orchestration/model_registry.yaml`). |
| Tools | Bound to sub-LLMs only, not root | The REPL exposes root-side built-ins such as `run_python_code` and `run_shell`, and exposes `CALL`/`TOOL` when a tool registry is supplied (`src/repl_environment/environment.py`). |
| Termination | `answer['ready']` state variable | `FINAL` and `FINAL_VAR` are REPL completion interfaces; the execution path detects them (`src/repl_environment/environment.py`). |
| Turn output budget | Sweep `ORCHESTRATOR_REPL_TURN_N_TOKENS` over 256–4,096 for our comparison | The EPYC tool-required turn cap defaults to 768, with a floor of 64; difficulty enforcement can instead select 1,500, 3,500 or 7,000 (`src/graph/budgets.py`). The sweep is a proposed experiment, not a result. |

Differences are not recommendations to replace the EPYC settings: the REPL timeout, output spill behavior, tool availability and termination interface form part of its own runtime contract. Compare them experimentally only with pinned settings and matched tasks.
