# KVU-16h legacy P3 safety guards — 2026-11-01

Two scratch entry points were changed to refuse legacy A1, which mixed request-level no-draft and drafted traffic on a drafted server. Both reject `all`/`a1` at CLI parse before their own output or server launch; the slot child also refuses a direct `phase_a1()` call. Four CLI refusal cases per entry point and a direct-call refusal for the slot child passed; syntax checks passed. No inference ran. These are partial safety guards, not dedicated-server replacements or a performance result.

| Live file | Original SHA-256 | Guarded SHA-256 | Original backup |
|---|---|---|---|
| `/mnt/raid0/llm/tmp/x0-27b-quants/p3_kvu_probe.py` | `be0f5abccf1e4a446606a85da36bf53a4486964d59ab24f2349c11198f9808ac` | `f49cd7f779c9bb509827b791c906621f5caef9ccc802ed851623532818fb2f37` | `/mnt/raid0/llm/tmp/handoff-kvu-legacy-p3-guard-20261101/p3_kvu_probe.py.orig` |
| `/mnt/raid0/llm/tmp/gpu-slot-ak-20261004/p3_kvu_probe_slot.py` | `7f0f4d50333dc58c1e4797709b47d16965e58f74db6db02c29c1a219e050ca6c` | `b1d7bd064f4f1e6e558d3908312ef28ac1088a493e521668180e24d2f668f86d` | `/mnt/raid0/llm/tmp/handoff-kvu-runner-guard-20261101/p3_kvu_probe_slot.original.py` |

The slot wrapper may start its drafted server before invoking the child, and other copies or direct calls to the first script's internals are not protected. The pinned `x0_common.py`, historical results, READY manifests and production kernels were not changed. The patches capture exactly the two edits; verify hashes before applying to any other copy. A separately prepared P3 diagnostic at `/mnt/raid0/llm/tmp/codex-kvu16h-runner-20261028/` has separate server lifecycles, but is not a shared-runner replacement. Q38-T7 and the rest of the inventory remain open.
