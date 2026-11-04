# CPU-FA-VKQ-3 independent calibration result

The target 2026-11-02 run completed both arms over one independently enrolled 70,814-token prompt. Each arm generated 128 token IDs, accepted 96 of 121 native MTP drafts (79.3388429752%), and returned HTTP 200. Hybrid minus legacy acceptance is 0 percentage points. Generated token IDs are identical; there is no first divergence within these 128 tokens. Both servers have matching captured PID/birth cleanup receipts, drained true, rc0, with verified server-log hashes. These are full target arms, not qualification controls.

The scope is the one enrolled independent-calibration prompt, model/build/settings in the copied native receipts, and one paired run. This satisfies the task's record-the-acceptance-delta alternative, not a performance, quality, general population, acc_peak, or deployment claim. No original exposed prompt was redrawn. Binary knob content proof and the preflight linked-library receipt are preserved; native startup logs identify the CPU backend.

The owning session reviewed and filed `verdict-proposed.json` through `file_result.py`, which ticked CPU-FA-VKQ-3 and acknowledged the row end. `comparison.json` exposes metrics and actual generated token IDs. Original responses and server receipts/logs are retained alongside per-file hashes. Source result: `/mnt/raid0/llm/tmp/kvu/vkq3-row/launcher/run/`.
