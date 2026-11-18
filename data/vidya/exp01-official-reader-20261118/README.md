# EXP01 official reader controls

The official reader's software controls are separate from acceptance of a native
official run. The armed row `vidya-exp01-proxy-official-native-20261118-r2` has no
terminal filing at this checkpoint. Its publisher smoke and recovered input seal
do not supply an official observation or pilot decision.

`scripts/vidya/canary/exp01_context.py --filing <original-filing>` now derives the
expected claim IDs and repetition counts through the strict adapter. It checks
the actual `AgentPlanner.propose` entry, intercepts the backend, checks explicit
proposal reliance receipts, renders read-only campaign history, and excludes GPU
and unrelated CPU targets. Run it against the completed original official filing
after the reader is on origin/main:

```sh
python3 scripts/vidya/canary/exp01_context.py \
  --reader /mnt/raid0/llm/views/epyc-root-main \
  --research /mnt/raid0/llm/epyc-inference-research \
  --campaign-store /mnt/raid0/llm/autokernel/proof-q38fn-r6-20261112 \
  --filing <original-filing> \
  --scratch /mnt/raid0/llm/tmp/vidya-belief-substrate/exp01-official-canary
```

The scratch path must be fresh. The ledger is isolated; the command starts no
inference or AutoPilot process. `control-regression/` contains the actual planner
regression on the already-filed capture control: four observations, twelve frames,
zero refusals and one repetition per arm. This receipt proves control behavior
only. It is not the future official canary.

`scratch-cleanup.json` records removal of superseded scratch. The four recovered
EXP01 model files, shared imatrix, and parity-r2 BF16 file remain because armed
rows bind their exact paths and stat identities.
