# HG-9 Step 1 immutable source and draft readset

This readset binds the source audit and PROPOSED artifact. Git source references are content-pinned; listed SHA-256 values hash each file's bytes as emitted by `git show <commit>:<path>`. No source file was edited by this audit.

ROOT pin: `4c0c653baf1654c8c25c66433cf39c8faefd8e52`

APP pin: `62db79be0bf9a4cdc8341ec48d8d240a14458288` (`https://github.com/pestopoppa/epyc-orchestrator`)

| Repository | Path at pin | SHA-256 |
|---|---|---|
| ROOT | `handoffs/active/reviewer-escalation-and-human-gate-policy.md` | `8e13498b14fa49b2fcb9464aeb1dd5d47f34af14e79f30f7dd7a22ea4971eae2` |
| ROOT | `handoffs/active/tri-role-coordinator-architecture.md` | `81dbb06b6243093d5bb36f7d98ccbc10b68d72695a716b5ccef8700c5eb95c42` |
| APP | `src/roles.py` | `408f10be964705638562ec9a6d0e1cd56b26ac849fdb964e8bac0c9a7fe4be61` |
| APP | `src/orchestration/escalation.py` | `5817e45c487edbb51c761fde632bb3a96a708f81ea9ef343354c8758aec9992f` |
| APP | `orchestration/model_registry.yaml` | `dd81678d5bd7d097b4168f41a97e97f1d85a292dd560a029ba3b908b9598eba5` |
| APP | `orchestration/review_decision.schema.json` | `313d9e4a97bd30807a9870085f12bc5c059797e51dbb8bcb4276a1e901cd2783` |
| APP | `src/proactive_delegation/review_service.py` | `eb0f7392a2d531a8f18bef924cb461d39a6afa4e6a41cc0df6de7fbd6a36c231` |
| APP | `src/proactive_delegation/policy_reducer.py` | `aa7736d750ec98dc13dddd36aadf93899ad7ba67241f332df4382e5ced63ce6b` |
| APP | `orchestration/machine_review_envelope.schema.json` | `d70b5ffd88a64d8090f82a6032db8ea1bbf18510d9b774564ac4b009a2405c0b` |
| APP | `src/proactive_delegation/review_envelope.py` | `ffd81d390f069a83bfcda62f31d1f917be04dd21aab8da161583ebcf04dfa0cb` |
| APP | `src/typed_decisions/types.py` | `8b5e2ec7f76a95ad0ff93e3af0f19153410fa68e61b2bae7f06eaa94a4e31bd1` |
| APP | `src/typed_decisions/runner.py` | `29cf2de3cddd46ad0f918c730388257f4c5ebbb024c7c77e40a7446f2512c51d` |
| APP | `src/typed_decisions/prepared_action.py` | `b2921dc9006a2f2ad9fe82299f4b774e1d65b5ef02467001a2f2272471a04a90` |
| APP | `src/typed_decisions/call_recorder.py` | `5349ebc4b00b667a975d486d9cb1912315e0873d31fe53fec71390defa350a46` |
| SCRATCH | `docs/design/hg9-detect-repair-topology.md` | `20bb1ccb215bbc0681cc0bf07cffdf054d3971c770aa4847cbc56037d12c80a5` |
| SCRATCH | `hg9-handoff-index-drafts.md` | `fbd96f77109460d1a50745ac5efc1f694511ec87a9bb33bf6013a86227c0786c` |

The APP worktree is currently at `300cf5817edccc4f82089f0faa477828496068b6`; a read-only diff found `src/backends/serving_calls.py` and `src/typed_decisions/coherence_judge.py` unchanged from the APP pin above. The HG design relies on the immutable 62db pin links embedded in the draft, not the mutable checkout state.
