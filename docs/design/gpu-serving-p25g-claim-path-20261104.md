# P2-5g: current GPU host claim path

The current production `architect_critic` on :8083 pins its host threads to
`184-191` without taking an all-q3 CPU-region lock. The historical premise that
starting this production lane necessarily displaces a q3 CPU tenant does not
describe the current launch and dispatch path. No new SMT-only region is needed
for this path. This answers P2-5g's current-serving claim question.

Source review on 2026-11-04 used the actual orchestrator main checkout at
`326f502759986c9846027f8187972969139c0089`; the inspected topology and lock files
were clean. The conclusion follows from the claim implementation, rather than
from an idle snapshot:

| Source | Evidence |
|---|---|
| `scripts/server/stack_numa.py:166,545-567`; `orchestration/stack_topology.yaml:275-289` | `GPU_HOST_LANE` is `184-191`; `architect_critic` uses that lane and launches with `taskset -c 184-191`. |
| `src/runtime/instance_topology.py`, `build_instance_regions` | The production topology uses `smt_siblings="drop"`; its documented GPU lane has empty CPU regions. |
| `src/runtime/direct_region_claim.py` | An empty region list produces no CPU claim in the direct-call dispatch path. |
| `scripts/server/gpu_shadow_lane_lease.py:152-154,329-341` | The separate shadow lease folds the same SMT CPUs to physical q3 and acquires that region. |
| `scripts/server/gpu_shadow_lane.py:8-17` | This shadow scaffold is default-off and disconnected from the production launch path. |

The CPU roles configured to include physical cores `88-95` or their SMT siblings
remain relevant to physical contention: `architect_general` uses `NUMA_FULL`
(`0-95`), and frontdoor half B uses `NUMA_HALF_B` (`48-95,144-191`). Empty GPU CPU
claims do not demonstrate an absence of SMT contention. Enabling the historical
shadow lease or a CLI claim that folds the SMT lane would reintroduce q3 lock
displacement and would require a separately reviewed claim design first.

No serving process, lock policy or launch configuration was changed. A single
q3-free snapshot was not used to infer that configured CPU roles are absent.
