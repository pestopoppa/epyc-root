# intake-2640 — From Alignment to Access Control (arXiv 2609.26682v1)

**Dive date**: 2026-11-06 · **Read depth**: FULL · **Revision**: v1 (2026-09-22)

## What it is

A **position and analytical-framework paper with zero first-party measurements**. It proposes a three-axis
dissection of enforcement approaches (policy definition, mechanism enforceability, stack position), names the
"Pretty Please region" where prompt-borne policies sit, and argues enforcement must be access control with the
policy definition separated from the mechanism (PEP/PDP/PIP, hook-based deterministic interception, tool-call
boundary as the surface). Every number it cites is from cited work; there is no prototype, case study or ablation.

It can justify moving a rule from prose to enforcement. It cannot support any claim that a specific enforcement
works, and it offers nothing usable on cross-policy conflict resolution (it names that as an open problem).

## Local mapping (from the lane)

- Destructive action authorization: deterministic and strongest (PreToolUse hook with no override, trash-first
  `rm`, inode identity checks).
- Filesystem containment: deterministic but partial (37 generated deny globs; the generator admits `sudo -n mount`
  slips past).
- Trust-boundary edits: partial — hard on Write/Edit, soft through bash.
- Process-kill containment: partial deterministic hook plus prose.
- Tool-use authorization and content/behavioural policy: prose only.
- Single control plane: absent; rules are triplicated across CLAUDE.md, OPERATING_CONSTRAINTS, hooks and
  opencode.json — though the permission generator is a working PIP→PEP precedent.

## Actionables

| Action | Owner | Disposition |
|---|---|---|
| Add a machine-readable rule registry with `enforcement_class: hard\|soft\|prose` and its PEP, generated into surfaces | coordination-and-churn-pipeline.md | adopt (design principle) |
| Promote tool-use authorization from prose to a hook at the tool boundary | engineering-hygiene-backlog.md | adopt |
| Declare cross-policy precedence for hard rules in one place | coordination-and-churn-pipeline.md | watch |

## Surfaced

MCP Context Forge (concrete hook-based tool-call gateway); IH-Benchmark; SOPBench.
