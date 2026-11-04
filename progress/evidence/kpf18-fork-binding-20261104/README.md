# KPF-18 native fork binding controls

The isolated `fork-binding.patch` refuses four impossible geometries that the predecessor accepted: source equals destination, source outside four slots, zero fork tokens, and a fork consuming the complete prompt. On 2026-11-04, five existing captured-binding controls plus four mutation controls passed using `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest test_fork_binding test_impossible_forks -v` in `/mnt/raid0/llm/tmp/kvu/kpf18-binding-guard-20261104/`. The test harness depends on retained native fixtures and `debug3_data` outside this packet; the patch is not deployed.

The three recovery receipts name exact-byte matches for seven missing and four mismatched historical native inputs, held under `/mnt/raid0/llm/tmp/kvu/kpf18-native-recovery-20261104/`. The original paths were not changed. Exact bytes alone do not prove a sealed, executable successor, native task binding in a live run, GPU admission, or a control verdict.
