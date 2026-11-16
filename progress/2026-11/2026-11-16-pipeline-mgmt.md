# 2026-11-16 pipeline-mgmt (wrap-up 6)

- **Opencode readonly cleanup verified.** A 75-minute watcher confirmed `/mnt/raid0/llm/opencode/readonly/*.db` did not reappear across an hourly sync run. OP-OPENCODE-RECLAIM is closed (its index row was already removed).
- **E5 Stage-B (INF-45) parked on a host reboot.** Uptime over 7 days fails the P-BENCH host-health gate; the operator chose "Not now". `inf45-e5v2-stageb-r5-20261115` is filed inconclusive. Republish as r6 after the reboot. Open: `cpu_bench` era for binary 10303 is unregistered; qwen38-p1 C1-np1/C1-np16 have no re-run row. Recorded in `handoffs/active/numa-placement-and-contention.md`, no boxes ticked.
- **Filing sweep:** queue_status shows 1 unfiled ended row, `up-farows-bound-gpu-20261115`, owned by autokernel. Not filed by pipeline-mgmt; left to its owner. No pipeline-mgmt rows are unfiled.
