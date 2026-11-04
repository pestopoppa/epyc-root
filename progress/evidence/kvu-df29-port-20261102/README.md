# DF29 free-port successor evidence

This lane preserves the runnable DF2-9 server kit and the source-only port-selector patch. It contains no `artifacts/` directory and no patch hunks targeting `artifacts/`. The historical source remains untouched.

- `source/`: runnable server, shared helpers, client, prompts, bounded port selector and listener-owner verifier.
- `port-selector.patch`: source-only patch for the proposed `scripts/benchmark/df29/` destination; it contains no artifact paths.
- `tests/test_ports.py`: offline socket/ownership tests.
- `source-pins/`: hashes of the historical inputs and proposed successor source.
- `NATIVE-GPU-ROW.md`: proposed six-arm row; native validation remains outstanding.

No GPU server/inference ran for this lane.
