# Research Intake Plan — You don't need long context (2026-11-06)

**Status**: awaiting operator approval. **Session**: intake-ydnlc-20261106. **Scope**: intake-2628..2640
(13 entries; 10 dived in waves 1-3, 2 existing entries deepened, 3 left `stage1-unverified`).
**No handoff, index row or stub has been written.**

## What the three waves established

1. Frequent compaction preserves benchmark accuracy **only where ground truth lives outside the transcript**
   (repo, tests, re-readable files) and **only for strong models**. The same paper's Appendix D shows local
   open-weight models losing 7-12 points, with one catastrophic collapse (53.0 -> 3.6).
2. The failure that matters for this project is not task accuracy: it is **governance**. Retained rules are
   violated 2.6x more often after compaction; soft organisational policies decay 8.3x more than hard safety
   norms; side constraints drop to 6% retention on open-weight compactors; and a text-presence check is not a
   safety check.
3. Our CLI harness has a **live provenance hole**: OpenCode's compaction serializer interpolates `[User]:` without
   escaping and re-injects the summary as a user-role message (paper-measured 87-100% laundering across five
   harnesses; our build untested). The orchestrator summary path is structurally safer but has no regression test.
4. There is one cheap fix that survives every source: **keep high-stakes rules out of the compactable surface**
   and enforce them deterministically. Everything else is measurement before activation.

## Work packets

| Packet | Action | Owner |
|---|---|---|
| P1 | Prove or disprove compaction laundering in the shipped OpenCode shell, then close the serializer | `handoffs/active/harness-program.md` |
| P2 | Make compaction governance-safe: fix the instrument, declare the artifact contract and arms, pre-register reliability, guard role boundaries | `handoffs/active/context-and-token-economy.md` |
| P3 | Classify governance rules by enforcement strength and add tool-use authorization | `handoffs/active/coordination-and-churn-pipeline.md` |
| M1 | Cite the short-context result once in the YARN go/no-go; create no task | `handoffs/active/long-context-program.md` |

## Proposed tasks (paste-ready; not applied)

| ID | Owner | Task |
|---|---|---|
| UFH-21 | `handoffs/active/harness-program.md` | **UFH-21 — Prove or disprove compaction laundering in the shipped OpenCode... |
| TOC-CMP-1 | `handoffs/active/context-and-token-economy.md` | **TOC-CMP-1 — Fix the inverted reference-miss detector in the orchestrator... |
| TOC-CMP-2 | `handoffs/active/context-and-token-economy.md` | **TOC-CMP-2 — Build the governance retention-and-compliance probe: declare... |
| TOC-CMP-3 | `handoffs/active/context-and-token-economy.md` | **TOC-CMP-3 — Add the compaction artifact contract to the TOC A/B: the six... |
| TOC-CMP-4 | `handoffs/active/context-and-token-economy.md` | **TOC-CMP-4 — Make the compaction A/B reproducible before running it: pre-... |
| TOC-CMP-5 | `handoffs/active/context-and-token-economy.md` | **TOC-CMP-5 — Add a role-boundary regression test to the orchestrator summ... |
| REG-ENF-1 | `handoffs/active/coordination-and-churn-pipeline.md` | **REG-ENF-1 — Publish a machine-readable governance rule registry with one... |
| REG-ENF-2 | `handoffs/active/coordination-and-churn-pipeline.md` | **REG-ENF-2 — Move tool-use authorization from prose to a tool-boundary ho... |

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| RI-1 | intake-2628 App. A (compaction brief recipe) + App. G prompts | Adopt the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers) as the compaction artifact contract | P2 / TOC-CMP-3 |
| RI-2 | intake-2629 §3.2/§4.3 retention instrument + intake-2637 §5.4 failure census | Fix the inverted reference-miss detector so a destroyed identifier can fire before any retention number is trusted | P2 / TOC-CMP-1 |
| RI-3 | intake-2631 §4.2 retained-but-violated + intake-2636 Table 2 + intake-2639 App. D rubric | Measure rule retention AND retained-rule compliance with deterministic predicates over four arms | P2 / TOC-CMP-2 |
| RI-4 | intake-2636 §6 Constraint Pinning (0% across seven models) | Add a pinned-governance buffer arm: exempt high-stakes rules from folding and re-inject them verbatim with an entailment check | P2 / TOC-CMP-3 |
| RI-5 | intake-2632 §3 checkpoint layout (verbatim prose + declared removals) | Add a verbatim_manifest arm that declares what left the view instead of summarising it | P2 / TOC-CMP-3 |
| RI-6 | intake-2527 §3.3 (590 boundaries, +0.108 blocked actions) and its missing power analysis | Pre-register repetitions and a minimum detectable effect for the compaction A/B and report Pass^3 | P2 / TOC-CMP-4 |
| RI-7 | intake-2638 abstract + local OpenCode serializers + disclosure/opencode.md | Prove or disprove compaction laundering in the shipped OpenCode shell and close the serializer if confirmed | P1 / UFH-21 |
| RI-8 | intake-2638 local read of the orchestrator consolidation path | Add a role-boundary regression test to the orchestrator summary path | P2 / TOC-CMP-5 |
| RI-9 | intake-2640 three-axis enforcement dissection + PEP/PDP/PIP separation | Publish a rule registry with an enforcement_class per governance rule and generate the enforcement surfaces from it | P3 / REG-ENF-1 |
| RI-10 | intake-2640 §4 hook-based enforcement at the tool-call boundary | Move tool-use authorization from prose to a tool-boundary hook with a declared fail posture | P3 / REG-ENF-2 |
| RI-11 | intake-2628 §6 scope statement + conclusion | Record the short-context result as one cited consideration in the YARN go/no-go without re-scoping the program | M1 |
| D1 | intake-2628 §5.1 (proposal only; no trained checkpoint) | Decline an SSSM post-training workstream; keep the concept as architecture context | decline: proposal only, no trained checkpoint and no evaluated result |
| D2 | intake-2630 §4 (no strategy beats default; offload lowered 0.38->0.24) | Decline porting the five compaction strategies or retuning thresholds | decline: no listed strategy beats default self-summarisation, and lossless offload lowered the score |
| D3 | intake-2629 §4.3 mechanical reference is the scoring set, not a method | Decline mechanical-extraction-as-summary on the strength of 79.1% | decline: the 79.1% reference is the scoring set, not a deployable method |
| D4 | intake-2397 reuse assessment (no compaction events or constraint labels) | Decline a gated SWE-chat pull until our own probe lands outside the published base rate | decline: the corpus carries no compaction events or constraint labels |
| D5 | intake-2640 framework-only paper (zero measurements) | Decline adopting the access-control framework as a system; adopt only its separation principle in P3 | decline: position paper with zero measurements; only its separation principle is adopted |

## Declines and monitor

- **D1 SSSM**: proposal only, zero trained checkpoints; no post-training workstream.
- **D2 strategy port**: no compaction strategy beat default self-summarisation, and lossless offload lowered
  GPT-5.3-Codex 0.38 -> 0.24. Porting is negative expected value.
- **D3 mechanical extraction**: the 79.1% figure is the scoring reference, not a deployable method; it was never
  run through Task Preservation.
- **D4 SWE-chat pull**: no compaction events or constraint labels; the corpus adds only a base rate. Reopen if our
  probe lands outside the published interval.
- **D5 access-control framework**: a position paper with zero measurements; adopt its separation principle (P3),
  not the framework.
- **M1**: the paper itself says its evidence does not rule out beneficial long-context tasks; the YARN gate keeps
  its existing cells.

## Why not a full paper reproduction

The immediate program is design text, local tests and one sandbox probe. The paper's own benchmarks are hosted
frontier models on cloud GPUs; reproducing them would not answer the EPYC question, which is whether *our* local
models lose governance under *our* compaction. The probe in P2 is the smallest experiment that can change that
decision; broader reproduction fires only if the probe shows loss below the pre-registered MDE.

## Stage-3 filing payload

```json
{
  "format_version": 2,
  "entry_updates": [
    {
      "id": "intake-2628",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/context-and-token-economy.md",
        "handoffs/active/long-context-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2629",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/context-and-token-economy.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2630",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/context-and-token-economy.md",
        "handoffs/active/harness-program.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2631",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/context-and-token-economy.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2632",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/context-and-token-economy.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2636",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/context-and-token-economy.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2637",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/context-and-token-economy.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2638",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/harness-program.md",
        "handoffs/active/context-and-token-economy.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2639",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/context-and-token-economy.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2640",
      "integration_disposition": "integrated",
      "handoffs_updated": [
        "handoffs/active/coordination-and-churn-pipeline.md"
      ],
      "handoffs_created": [],
      "disposition_evidence": [
        "Approved plan routes this source's verified findings to the named owner tasks; no deployment is implied."
      ]
    },
    {
      "id": "intake-2633",
      "integration_disposition": "awaiting_dive",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "Not selected for a Stage-2 dive in this run; claims remain provisional and may not be quoted."
      ]
    },
    {
      "id": "intake-2634",
      "integration_disposition": "awaiting_dive",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "Not selected for a Stage-2 dive in this run; claims remain provisional and may not be quoted."
      ]
    },
    {
      "id": "intake-2635",
      "integration_disposition": "awaiting_dive",
      "handoffs_updated": [],
      "handoffs_created": [],
      "disposition_evidence": [
        "Not selected for a Stage-2 dive in this run; claims remain provisional and may not be quoted."
      ]
    }
  ],
  "opportunity_reviews": {
    "P1": {
      "project_objective": "Keep the CLI harness inside the human-only trust boundary while it compacts",
      "implementation_ref": "OpenCode packages/opencode/src/session/compaction.ts serialize() and to-llm-message.ts re-injection; installed v2.2.5",
      "gap": "Role labels are interpolated unescaped and the summary re-enters as a user-role message; untested in our build",
      "operational_change": "Prove or disprove laundering, then escape or re-type the serializer if confirmed",
      "benefit_direction": "A forged user turn can no longer acquire user authority; no change to legitimate compaction content",
      "owner": "handoffs/active/harness-program.md",
      "execution_conditions": "Probe first, patch only on a positive result; no inference required",
      "closure_basis": "Immediate outcome retained by UFH-21; upstream advisory is a follow-on, not a gate"
    },
    "P2": {
      "project_objective": "Decide whether and how compaction may be enabled for governed agent work",
      "implementation_ref": "context-and-token-economy.md CF-AB-1/CF-3c/TOC-MP-2/3 plus the orchestrator summary path",
      "gap": "No rule-retention instrument, an inverted miss detector, and no declared compaction artifact contract",
      "operational_change": "Fix the instrument, declare the artifact contract and arms, pre-register reliability, and add the role-boundary test",
      "benefit_direction": "Retention and compliance become measurable before activation; a null below the MDE is futility, not safety",
      "owner": "handoffs/active/context-and-token-economy.md",
      "execution_conditions": "Design and test work immediate; probe execution gated on TOC-SP-5 binding a window; activation separately gated",
      "closure_basis": "Immediate design/test outcomes retained; measurement and activation remain gated"
    },
    "P3": {
      "project_objective": "Reduce the share of load-bearing governance that exists only as compactable prose",
      "implementation_ref": "CLAUDE.md, agents/shared/OPERATING_CONSTRAINTS.md, scripts/hooks/generate_opencode_permissions.py, opencode.json deny list",
      "gap": "Rules are triplicated across prose, hooks and deny globs; tool-use authorization has no enforcement point",
      "operational_change": "Publish a rule registry with enforcement classes and add a tool-boundary authorization hook",
      "benefit_direction": "A rule's enforcement strength becomes inspectable and survives context loss by construction",
      "owner": "handoffs/active/coordination-and-churn-pipeline.md",
      "execution_conditions": "Registry generation is immediate; the tool-use hook ships behind its own test",
      "closure_basis": "Immediate outcomes retained; conflict-resolution precedence remains an open watch item"
    },
    "M1": {
      "project_objective": "Keep the long-context program decision honest without re-scoping it on one paper",
      "implementation_ref": "handoffs/active/long-context-program.md YARN gate",
      "gap": "No recorded consideration of the short-context counter-evidence in the go/no-go",
      "operational_change": "Cite the result once in the YARN consideration; create no task",
      "benefit_direction": "Decision stays evidence-aware without importing a claim the paper itself bounds",
      "owner": "handoffs/active/long-context-program.md",
      "execution_conditions": "Monitor only; no execution",
      "closure_basis": "No immediate operational step remains; the paper explicitly does not rule out beneficial long-context tasks"
    }
  },
  "actionable_additions": [
    {
      "ledger_id": "RI-1",
      "source": "intake-2628 App. A (compaction brief recipe) + App. G prompts",
      "action": "Adopt the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers) as the compaction artifact contract",
      "terminal_mapping": "P2 / TOC-CMP-3"
    },
    {
      "ledger_id": "RI-2",
      "source": "intake-2629 \u00a73.2/\u00a74.3 retention instrument + intake-2637 \u00a75.4 failure census",
      "action": "Fix the inverted reference-miss detector so a destroyed identifier can fire before any retention number is trusted",
      "terminal_mapping": "P2 / TOC-CMP-1"
    },
    {
      "ledger_id": "RI-3",
      "source": "intake-2631 \u00a74.2 retained-but-violated + intake-2636 Table 2 + intake-2639 App. D rubric",
      "action": "Measure rule retention AND retained-rule compliance with deterministic predicates over four arms",
      "terminal_mapping": "P2 / TOC-CMP-2"
    },
    {
      "ledger_id": "RI-4",
      "source": "intake-2636 \u00a76 Constraint Pinning (0% across seven models)",
      "action": "Add a pinned-governance buffer arm: exempt high-stakes rules from folding and re-inject them verbatim with an entailment check",
      "terminal_mapping": "P2 / TOC-CMP-3"
    },
    {
      "ledger_id": "RI-5",
      "source": "intake-2632 \u00a73 checkpoint layout (verbatim prose + declared removals)",
      "action": "Add a verbatim_manifest arm that declares what left the view instead of summarising it",
      "terminal_mapping": "P2 / TOC-CMP-3"
    },
    {
      "ledger_id": "RI-6",
      "source": "intake-2527 \u00a73.3 (590 boundaries, +0.108 blocked actions) and its missing power analysis",
      "action": "Pre-register repetitions and a minimum detectable effect for the compaction A/B and report Pass^3",
      "terminal_mapping": "P2 / TOC-CMP-4"
    },
    {
      "ledger_id": "RI-7",
      "source": "intake-2638 abstract + local OpenCode serializers + disclosure/opencode.md",
      "action": "Prove or disprove compaction laundering in the shipped OpenCode shell and close the serializer if confirmed",
      "terminal_mapping": "P1 / UFH-21"
    },
    {
      "ledger_id": "RI-8",
      "source": "intake-2638 local read of the orchestrator consolidation path",
      "action": "Add a role-boundary regression test to the orchestrator summary path",
      "terminal_mapping": "P2 / TOC-CMP-5"
    },
    {
      "ledger_id": "RI-9",
      "source": "intake-2640 three-axis enforcement dissection + PEP/PDP/PIP separation",
      "action": "Publish a rule registry with an enforcement_class per governance rule and generate the enforcement surfaces from it",
      "terminal_mapping": "P3 / REG-ENF-1"
    },
    {
      "ledger_id": "RI-10",
      "source": "intake-2640 \u00a74 hook-based enforcement at the tool-call boundary",
      "action": "Move tool-use authorization from prose to a tool-boundary hook with a declared fail posture",
      "terminal_mapping": "P3 / REG-ENF-2"
    },
    {
      "ledger_id": "RI-11",
      "source": "intake-2628 \u00a76 scope statement + conclusion",
      "action": "Record the short-context result as one cited consideration in the YARN go/no-go without re-scoping the program",
      "terminal_mapping": "M1"
    },
    {
      "ledger_id": "D1",
      "source": "intake-2628 \u00a75.1 (proposal only; no trained checkpoint)",
      "action": "Decline an SSSM post-training workstream; keep the concept as architecture context",
      "terminal_mapping": "decline: proposal only, no trained checkpoint and no evaluated result"
    },
    {
      "ledger_id": "D2",
      "source": "intake-2630 \u00a74 (no strategy beats default; offload lowered 0.38->0.24)",
      "action": "Decline porting the five compaction strategies or retuning thresholds",
      "terminal_mapping": "decline: no listed strategy beats default self-summarisation, and lossless offload lowered the score"
    },
    {
      "ledger_id": "D3",
      "source": "intake-2629 \u00a74.3 mechanical reference is the scoring set, not a method",
      "action": "Decline mechanical-extraction-as-summary on the strength of 79.1%",
      "terminal_mapping": "decline: the 79.1% reference is the scoring set, not a deployable method"
    },
    {
      "ledger_id": "D4",
      "source": "intake-2397 reuse assessment (no compaction events or constraint labels)",
      "action": "Decline a gated SWE-chat pull until our own probe lands outside the published base rate",
      "terminal_mapping": "decline: the corpus carries no compaction events or constraint labels"
    },
    {
      "ledger_id": "D5",
      "source": "intake-2640 framework-only paper (zero measurements)",
      "action": "Decline adopting the access-control framework as a system; adopt only its separation principle in P3",
      "terminal_mapping": "decline: position paper with zero measurements; only its separation principle is adopted"
    }
  ],
  "steering_reconciliation": [
    {
      "seq": 1,
      "stage": 1,
      "verbatim": "Run the research-intake skill on this source: https://arxiv.org/html/2611.05306v1. Accept all recommended deep dives for up to three Stage 2 waves.",
      "disposition": "planned",
      "plan_ref": "P2",
      "reason": "Authorizes the Stage-2 dive scope used for all three waves; the Stage-3 filing remains separately reviewed and is mapped here to the compaction-governance packet."
    }
  ],
  "opportunity_scan": [
    {
      "scan_id": "S1",
      "source_ref": "intake-2628 App. A (compaction brief recipe) + App. G prompts",
      "implementation_ref": "handoffs/active/context-and-token-economy.md CF-AB-1 A6",
      "mechanism": "Adopt the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers) as the compaction artifact contract",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Adopt the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers) as the compaction artifact contract",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-1"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S2",
      "source_ref": "intake-2629 \u00a73.2/\u00a74.3 retention instrument + intake-2637 \u00a75.4 failure census",
      "implementation_ref": "handoffs/active/context-and-token-economy.md:119 detector; session_summary.py:276,297",
      "mechanism": "Fix the inverted reference-miss detector so a destroyed identifier can fire before any retention number is trusted",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Fix the inverted reference-miss detector so a destroyed identifier can fire before any retention number is trusted",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-2"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S3",
      "source_ref": "intake-2631 \u00a74.2 retained-but-violated + intake-2636 Table 2 + intake-2639 App. D rubric",
      "implementation_ref": "handoffs/active/context-and-token-economy.md CF-AB-1 co-metric",
      "mechanism": "Measure rule retention AND retained-rule compliance with deterministic predicates over four arms",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Measure rule retention AND retained-rule compliance with deterministic predicates over four arms",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-3"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S4",
      "source_ref": "intake-2636 \u00a76 Constraint Pinning (0% across seven models)",
      "implementation_ref": "handoffs/active/context-and-token-economy.md CF-AB-1",
      "mechanism": "Add a pinned-governance buffer arm: exempt high-stakes rules from folding and re-inject them verbatim with an entailment check",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Add a pinned-governance buffer arm: exempt high-stakes rules from folding and re-inject them verbatim with an entailment check",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-4"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S5",
      "source_ref": "intake-2632 \u00a73 checkpoint layout (verbatim prose + declared removals)",
      "implementation_ref": "handoffs/active/context-and-token-economy.md TOC-MP-2",
      "mechanism": "Add a verbatim_manifest arm that declares what left the view instead of summarising it",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Add a verbatim_manifest arm that declares what left the view instead of summarising it",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-5"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S6",
      "source_ref": "intake-2527 \u00a73.3 (590 boundaries, +0.108 blocked actions) and its missing power analysis",
      "implementation_ref": "handoffs/active/context-and-token-economy.md TOC-MP-3",
      "mechanism": "Pre-register repetitions and a minimum detectable effect for the compaction A/B and report Pass^3",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Pre-register repetitions and a minimum detectable effect for the compaction A/B and report Pass^3",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-6"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S7",
      "source_ref": "intake-2638 abstract + local OpenCode serializers + disclosure/opencode.md",
      "implementation_ref": "harness/opencode-plugin + OpenCode packages/opencode/src/session/compaction.ts",
      "mechanism": "Prove or disprove compaction laundering in the shipped OpenCode shell and close the serializer if confirmed",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Prove or disprove compaction laundering in the shipped OpenCode shell and close the serializer if confirmed",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-7"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S8",
      "source_ref": "intake-2638 local read of the orchestrator consolidation path",
      "implementation_ref": "src/graph/session_log.py:674-683; src/graph/helpers.py:1531-1534",
      "mechanism": "Add a role-boundary regression test to the orchestrator summary path",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Add a role-boundary regression test to the orchestrator summary path",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-8"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S9",
      "source_ref": "intake-2640 three-axis enforcement dissection + PEP/PDP/PIP separation",
      "implementation_ref": "CLAUDE.md + agents/shared/OPERATING_CONSTRAINTS.md + scripts/hooks/generate_opencode_permissions.py",
      "mechanism": "Publish a rule registry with an enforcement_class per governance rule and generate the enforcement surfaces from it",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Publish a rule registry with an enforcement_class per governance rule and generate the enforcement surfaces from it",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-9"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S10",
      "source_ref": "intake-2640 \u00a74 hook-based enforcement at the tool-call boundary",
      "implementation_ref": "handoffs/active/engineering-hygiene-backlog.md + opencode.json deny list",
      "mechanism": "Move tool-use authorization from prose to a tool-boundary hook with a declared fail posture",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Move tool-use authorization from prose to a tool-boundary hook with a declared fail posture",
      "disposition": "actionable",
      "ledger_ids": [
        "RI-10"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S11",
      "source_ref": "intake-2628 \u00a76 scope statement + conclusion",
      "implementation_ref": "handoffs/active/long-context-program.md YARN gate",
      "mechanism": "Record the short-context result as one cited consideration in the YARN go/no-go without re-scoping the program",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Record the short-context result as one cited consideration in the YARN go/no-go without re-scoping the program",
      "disposition": "context-only",
      "ledger_ids": [
        "RI-11"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S12",
      "source_ref": "intake-2628 \u00a75.1 (proposal only; no trained checkpoint)",
      "implementation_ref": "handoffs/active/model-architecture-readiness.md",
      "mechanism": "Decline an SSSM post-training workstream; keep the concept as architecture context",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Decline an SSSM post-training workstream; keep the concept as architecture context",
      "disposition": "declined",
      "ledger_ids": [
        "D1"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S13",
      "source_ref": "intake-2630 \u00a74 (no strategy beats default; offload lowered 0.38->0.24)",
      "implementation_ref": "handoffs/active/context-and-token-economy.md",
      "mechanism": "Decline porting the five compaction strategies or retuning thresholds",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Decline porting the five compaction strategies or retuning thresholds",
      "disposition": "declined",
      "ledger_ids": [
        "D2"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S14",
      "source_ref": "intake-2629 \u00a74.3 mechanical reference is the scoring set, not a method",
      "implementation_ref": "handoffs/active/context-and-token-economy.md",
      "mechanism": "Decline mechanical-extraction-as-summary on the strength of 79.1%",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Decline mechanical-extraction-as-summary on the strength of 79.1%",
      "disposition": "declined",
      "ledger_ids": [
        "D3"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S15",
      "source_ref": "intake-2397 reuse assessment (no compaction events or constraint labels)",
      "implementation_ref": "handoffs/active/harness-program.md",
      "mechanism": "Decline a gated SWE-chat pull until our own probe lands outside the published base rate",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Decline a gated SWE-chat pull until our own probe lands outside the published base rate",
      "disposition": "declined",
      "ledger_ids": [
        "D4"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    },
    {
      "scan_id": "S16",
      "source_ref": "intake-2640 framework-only paper (zero measurements)",
      "implementation_ref": "handoffs/active/coordination-and-churn-pipeline.md",
      "mechanism": "Decline adopting the access-control framework as a system; adopt only its separation principle in P3",
      "consumer": "the EPYC harness and compaction owners named in the mapping",
      "application": "Decline adopting the access-control framework as a system; adopt only its separation principle in P3",
      "disposition": "declined",
      "ledger_ids": [
        "D5"
      ],
      "basis": "Read the verified source passage and the current consumer implementation; the gap and the terminal mapping were reviewed independently."
    }
  ],
  "outcome_reviews": {
    "RI-1": {
      "required_outcome": "Adopt the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers) as the compaction artifact contract",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/context-and-token-economy.md",
          "task_id": "TOC-CMP-3",
          "task_text": "- [ ] **TOC-CMP-3 \u2014 Add the compaction artifact contract to the TOC A/B: the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers), a pinned-governance buffer exempt from folding and re-injected verbatim with a post-fold entailment check, and a verbatim_manifest arm that declares what left the view.**",
          "acceptance": "Each arm is specified as paste-ready design text with its artifact fields and entailment predicate, and the arm set is fixed before any run. Design-only; no behaviour change."
        }
      ]
    },
    "RI-2": {
      "required_outcome": "Fix the inverted reference-miss detector so a destroyed identifier can fire before any retention number is trusted",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/context-and-token-economy.md",
          "task_id": "TOC-CMP-1",
          "task_text": "- [ ] **TOC-CMP-1 \u2014 Fix the inverted reference-miss detector in the orchestrator summary path so a destroyed identifier can fire: read identifiers from `seg.granular_blocks` rather than the compacted text, and add a unit test whose only passing outcome is the destroyed-identifier case firing.**",
          "acceptance": "The detector fires on a fixture where compaction destroyed a known identifier, and stays silent when the identifier survives. Enabling work for TOC-CMP-2; no inference."
        }
      ]
    },
    "RI-3": {
      "required_outcome": "Measure rule retention AND retained-rule compliance with deterministic predicates over four arms",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/context-and-token-economy.md",
          "task_id": "TOC-CMP-2",
          "task_text": "- [ ] **TOC-CMP-2 \u2014 Build the governance retention-and-compliance probe: declare 5-8 EPYC rules with hard/soft/prose enforcement classes and a sibling-target control, then measure four arms (full history, intact rule, degraded residue, rule absent) with deterministic tool-call predicates and the Appendix D v4 rubric, reporting retention as a ceiling and compliance as the result.**",
          "acceptance": "A pre-registered probe reports per-rule retention and post-compaction compliance for each arm on the serving model, with the allowed sibling action as the headroom control. Execution stays gated on TOC-SP-5 binding a window."
        }
      ]
    },
    "RI-4": {
      "required_outcome": "Add a pinned-governance buffer arm: exempt high-stakes rules from folding and re-inject them verbatim with an entailment check",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/context-and-token-economy.md",
          "task_id": "TOC-CMP-3",
          "task_text": "- [ ] **TOC-CMP-3 \u2014 Add the compaction artifact contract to the TOC A/B: the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers), a pinned-governance buffer exempt from folding and re-injected verbatim with a post-fold entailment check, and a verbatim_manifest arm that declares what left the view.**",
          "acceptance": "Each arm is specified as paste-ready design text with its artifact fields and entailment predicate, and the arm set is fixed before any run. Design-only; no behaviour change."
        }
      ]
    },
    "RI-5": {
      "required_outcome": "Add a verbatim_manifest arm that declares what left the view instead of summarising it",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/context-and-token-economy.md",
          "task_id": "TOC-CMP-3",
          "task_text": "- [ ] **TOC-CMP-3 \u2014 Add the compaction artifact contract to the TOC A/B: the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers), a pinned-governance buffer exempt from folding and re-injected verbatim with a post-fold entailment check, and a verbatim_manifest arm that declares what left the view.**",
          "acceptance": "Each arm is specified as paste-ready design text with its artifact fields and entailment predicate, and the arm set is fixed before any run. Design-only; no behaviour change."
        }
      ]
    },
    "RI-6": {
      "required_outcome": "Pre-register repetitions and a minimum detectable effect for the compaction A/B and report Pass^3",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/context-and-token-economy.md",
          "task_id": "TOC-CMP-4",
          "task_text": "- [ ] **TOC-CMP-4 \u2014 Make the compaction A/B reproducible before running it: pre-register a minimum detectable effect of 0.10 blocked actions per step, at least 30 paired compaction points per model with 8-12 repeats each, three arms (raw tail, summary, FIFO), a boundary-stratified bootstrap, and report Pass^3 alongside accuracy.**",
          "acceptance": "The A/B acceptance text carries the repetition count, the MDE and the three arms, and a result below the MDE is written as futility rather than absence. Design-only until the window gates open."
        }
      ]
    },
    "RI-7": {
      "required_outcome": "Prove or disprove compaction laundering in the shipped OpenCode shell and close the serializer if confirmed",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/harness-program.md",
          "task_id": "UFH-21",
          "task_text": "- [ ] **UFH-21 \u2014 Prove or disprove compaction laundering in the shipped OpenCode shell, then close it: place a forged `[User]:` approval in a file the agent reads, run `/compact`, and record whether the summary carries it as a user instruction; if it does, patch the serialize path to escape role labels (or restore a typed message array) in both `packages/opencode` and `packages/core`, add a hostile-tool-output unit test, and file the upstream advisory.**",
          "acceptance": "A recorded sandbox run shows whether the forged approval reaches the summary as user authority; if confirmed, the patch makes the same run inert and a hostile-tool-output test guards it. Scope: local shell only, no inference."
        }
      ]
    },
    "RI-8": {
      "required_outcome": "Add a role-boundary regression test to the orchestrator summary path",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/context-and-token-economy.md",
          "task_id": "TOC-CMP-5",
          "task_text": "- [ ] **TOC-CMP-5 \u2014 Add a role-boundary regression test to the orchestrator summary path: a hostile tool output containing `[User]:` or `<|im_start|>` must not survive `build_consolidation_prompt` as an un-neutralised role boundary, and the summary must stay a prompt block rather than a user-role message.**",
          "acceptance": "A fixture with a forged role label produces a neutralised prompt block and no user-role summary, asserted by test. Local test only."
        }
      ]
    },
    "RI-9": {
      "required_outcome": "Publish a rule registry with an enforcement_class per governance rule and generate the enforcement surfaces from it",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/coordination-and-churn-pipeline.md",
          "task_id": "REG-ENF-1",
          "task_text": "- [ ] **REG-ENF-1 \u2014 Publish a machine-readable governance rule registry with one row per rule carrying `enforcement_class: hard|soft|prose` and its enforcement point, generated into the hook, deny-list and prose surfaces so the rule set has one source of truth.**",
          "acceptance": "The registry enumerates every destructive-op, containment and trust-boundary rule with its class and enforcement point, and the generator reproduces the current deny list byte-for-byte before any new rule is added."
        }
      ]
    },
    "RI-10": {
      "required_outcome": "Move tool-use authorization from prose to a tool-boundary hook with a declared fail posture",
      "review_status": "preserved",
      "review_basis": "Independent review of the selected passage and the current consumer confirms the gap and that the named task's acceptance covers the required operational outcome; activation gates are kept separate from implementation.",
      "task_refs": [
        {
          "owner": "handoffs/active/coordination-and-churn-pipeline.md",
          "task_id": "REG-ENF-2",
          "task_text": "- [ ] **REG-ENF-2 \u2014 Move tool-use authorization from prose to a tool-boundary hook: deny an inference launch that holds no region claim, mirroring the destructive-command PreToolUse hook, and state the fail-open/fail-closed posture in the acceptance.**",
          "acceptance": "A launch without a held claim is refused at the tool boundary and a launch with a claim proceeds, with the fail posture documented and tested."
        }
      ]
    },
    "RI-11": {
      "required_outcome": "The short-context result is cited once in the YARN go/no-go consideration without creating a task or re-scoping the program.",
      "review_status": "closed-with-basis",
      "review_basis": "Monitor-only: the paper explicitly does not rule out tasks where long context is beneficial, so no immediate operational step follows; the YARN gate'\ufffd\ufffd existing cells decide.",
      "task_refs": []
    },
    "D1": {
      "required_outcome": "No work is opened for this recommendation; the decline is recorded with its reason so it is not re-derived.",
      "review_status": "closed-with-basis",
      "review_basis": "Declined on the basis recorded in intake-2628 \u00a75.1 (proposal only; no trained checkpoint); the source itself supports the decline and no immediate operational step remains.",
      "task_refs": []
    },
    "D2": {
      "required_outcome": "No work is opened for this recommendation; the decline is recorded with its reason so it is not re-derived.",
      "review_status": "closed-with-basis",
      "review_basis": "Declined on the basis recorded in intake-2630 \u00a74 (no strategy beats default; offload lowered 0.38->0.24); the source itself supports the decline and no immediate operational step remains.",
      "task_refs": []
    },
    "D3": {
      "required_outcome": "No work is opened for this recommendation; the decline is recorded with its reason so it is not re-derived.",
      "review_status": "closed-with-basis",
      "review_basis": "Declined on the basis recorded in intake-2629 \u00a74.3 mechanical reference is the scoring set, not a method; the source itself supports the decline and no immediate operational step remains.",
      "task_refs": []
    },
    "D4": {
      "required_outcome": "No work is opened for this recommendation; the decline is recorded with its reason so it is not re-derived.",
      "review_status": "closed-with-basis",
      "review_basis": "Declined on the basis recorded in intake-2397 reuse assessment (no compaction events or constraint labels); the source itself supports the decline and no immediate operational step remains.",
      "task_refs": []
    },
    "D5": {
      "required_outcome": "No work is opened for this recommendation; the decline is recorded with its reason so it is not re-derived.",
      "review_status": "closed-with-basis",
      "review_basis": "Declined on the basis recorded in intake-2640 framework-only paper (zero measurements); the source itself supports the decline and no immediate operational step remains.",
      "task_refs": []
    }
  },
  "proposed_tasks": [
    {
      "owner": "handoffs/active/harness-program.md",
      "task_text": "- [ ] **UFH-21 \u2014 Prove or disprove compaction laundering in the shipped OpenCode shell, then close it: place a forged `[User]:` approval in a file the agent reads, run `/compact`, and record whether the summary carries it as a user instruction; if it does, patch the serialize path to escape role labels (or restore a typed message array) in both `packages/opencode` and `packages/core`, add a hostile-tool-output unit test, and file the upstream advisory.**"
    },
    {
      "owner": "handoffs/active/context-and-token-economy.md",
      "task_text": "- [ ] **TOC-CMP-1 \u2014 Fix the inverted reference-miss detector in the orchestrator summary path so a destroyed identifier can fire: read identifiers from `seg.granular_blocks` rather than the compacted text, and add a unit test whose only passing outcome is the destroyed-identifier case firing.**"
    },
    {
      "owner": "handoffs/active/context-and-token-economy.md",
      "task_text": "- [ ] **TOC-CMP-2 \u2014 Build the governance retention-and-compliance probe: declare 5-8 EPYC rules with hard/soft/prose enforcement classes and a sibling-target control, then measure four arms (full history, intact rule, degraded residue, rule absent) with deterministic tool-call predicates and the Appendix D v4 rubric, reporting retention as a ceiling and compliance as the result.**"
    },
    {
      "owner": "handoffs/active/context-and-token-economy.md",
      "task_text": "- [ ] **TOC-CMP-3 \u2014 Add the compaction artifact contract to the TOC A/B: the six-field execution brief (verbatim task, current intent, plan, completion requirements, artifacts, pointers), a pinned-governance buffer exempt from folding and re-injected verbatim with a post-fold entailment check, and a verbatim_manifest arm that declares what left the view.**"
    },
    {
      "owner": "handoffs/active/context-and-token-economy.md",
      "task_text": "- [ ] **TOC-CMP-4 \u2014 Make the compaction A/B reproducible before running it: pre-register a minimum detectable effect of 0.10 blocked actions per step, at least 30 paired compaction points per model with 8-12 repeats each, three arms (raw tail, summary, FIFO), a boundary-stratified bootstrap, and report Pass^3 alongside accuracy.**"
    },
    {
      "owner": "handoffs/active/context-and-token-economy.md",
      "task_text": "- [ ] **TOC-CMP-5 \u2014 Add a role-boundary regression test to the orchestrator summary path: a hostile tool output containing `[User]:` or `<|im_start|>` must not survive `build_consolidation_prompt` as an un-neutralised role boundary, and the summary must stay a prompt block rather than a user-role message.**"
    },
    {
      "owner": "handoffs/active/coordination-and-churn-pipeline.md",
      "task_text": "- [ ] **REG-ENF-1 \u2014 Publish a machine-readable governance rule registry with one row per rule carrying `enforcement_class: hard|soft|prose` and its enforcement point, generated into the hook, deny-list and prose surfaces so the rule set has one source of truth.**"
    },
    {
      "owner": "handoffs/active/coordination-and-churn-pipeline.md",
      "task_text": "- [ ] **REG-ENF-2 \u2014 Move tool-use authorization from prose to a tool-boundary hook: deny an inference launch that holds no region claim, mirroring the destructive-command PreToolUse hook, and state the fail-open/fail-closed posture in the acceptance.**"
    }
  ]
}
```
