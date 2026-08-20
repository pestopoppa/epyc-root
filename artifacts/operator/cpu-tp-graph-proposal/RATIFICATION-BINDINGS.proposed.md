# CPU-TP Phase 0/1 proposed ratification bindings

This is a proposal, not a ratification receipt. The measurement trust boundary remains
human-amendment-only.

The hardware-free preflight implementation is frozen in `epyc-inference-research` commit
`e6a4e4b7443442d305a0a991b697cbc0013d3b16` on branch
`codex/cpu-tp-phase01-runner-20260820`. It is intentionally incapable of starting a benchmark,
even when presented with a syntactically valid ratification receipt. A later execution-enabled
revision must bind the ratified protocol and these identities before it may acquire a region lock
or collect a sample.

| Authority | SHA-256 |
|---|---|
| `P-BENCH-NUMA-TP-1.draft.md` | `eb88445deba323135af8284d4a9f0c9598c15c9f0d687312a9f626fe0a6b7768` |
| Validate-only runner | `318427c6f1aad2f934a523f66b04b330b99469b094a36c94af876c01ab79f026` |
| Schema manifest | `43cb00274e7afa54b1d6e83cd2a721a837e17db7dcabdb5820bc6b5b4055f502` |
| Stable stopping rule | `6ce033d259bf9eae7b9dcb52a936240020565a4f7450fb5da0ecdf22a97731f2` |

The current-host validate-only receipt is
`8a069e9f1c5bc8b20c6a8e9432cf01ed7794d71c410dba3d4062e705f96e9b33`.
It records expected hard blocks for absent N25 and human-ratification receipts, absent `perf` and
AMD uProf PCM, an unacquired q0–q3 region lock, and uptime beyond one week. It is diagnostic
evidence only and cannot satisfy any gate after the planned reboot.
