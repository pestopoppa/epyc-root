# 2026-11-02 — handoff ernie-image-turbo-evaluation

## 00:13Z — Resolve typography capture status and inspect retained comparison inputs

### ERNIE handoff: inference inventory and next steps

The 20-prompt typography capture `codex3-ernie-typo20-20261031` already completed rc=0 with 40/40 images; its retained outputs and terminal record are at `/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/`. Do not recapture it: separately attributed human typography review is still needed; the run does not validate the official benchmark score. Qwen-Image-2.1 and ERNIE model bundles and retained ERNIE CPU/HIP launchers exist; a matched comparison still needs a prepared launcher, verified runtime identities, pinned prompts/settings and a published row. The content-filter harness uses the configured ImageGenerator backend, now Qwen, so verify or isolate ERNIE backend identity before attributing an audit to ERNIE. The prior 1024² GPU white-output failure remains unresolved; the handoff says its next test is subject to the 2026-09-17 GPU hold. A bounded row-publication review is in progress with its output registered under the handoff session awaiting directory. No inference, benchmark verdict or checkbox completion occurred. [no-belief: inventory and preparation only]
