export const meta = {
  name: 'epyc-refactor-impl',
  description: 'Implement audited work packages in isolated git worktrees, then adversarially review each diff',
  phases: [
    { title: 'Implement', detail: 'one implementer per package stage, in its own worktree' },
    { title: 'Review', detail: 'adversarial reviewer re-checks and fixes the package diff' },
  ],
}

const S = '/tmp/claude-0/-home-user/2773a866-6e4b-53fa-9304-d5960d8e1337/scratchpad'
const OLD = '/tmp/claude-0/-home-user-epyc-root/2773a866-6e4b-53fa-9304-d5960d8e1337/scratchpad'
const BASE_BRANCH = 'claude/vigilant-thompson-shpyh0'

function repoCtx(p) {
  if (p.repo === 'O') {
    return {
      name: 'epyc-orchestrator',
      base: '/workspace/repos/epyc-orchestrator',
      py: '/workspace/repos/epyc-orchestrator/.venv/bin/python',
      test: `cd ${p.wt} && CI=true ORCHESTRATOR_MOCK_MODE=1 /workspace/repos/epyc-orchestrator/.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts="" -n 2 <test paths>`,
      baseline: `${OLD}/orch_baseline_failing_ids.txt (2026-10-07 code; a fresh baseline at the current base head is being written to ${S}/orch_baseline2.txt and may be complete when you look)`,
    }
  }
  return {
    name: 'epyc-inference-research',
    base: '/workspace/repos/epyc-inference-research',
    py: '/workspace/repos/epyc-inference-research/.venv/bin/python',
    test: `cd ${p.wt} && /workspace/repos/epyc-inference-research/.venv/bin/python -m pytest -q -p no:cacheprovider -n 2 <test paths>`,
    baseline: `${OLD}/ak_baseline_failing_ids.txt (2026-10-07 code; about 58% of those failures are host-dependent: root uid, CPU count < 32/64, missing /mnt/raid0)`,
  }
}

function rules(p) {
  const r = repoCtx(p)
  return `
SETTING
- You are implementing part of an audited refactoring program for the EPYC repos, in an ephemeral cloud container (4 CPUs, 15 GiB RAM, running as root; NOT the operator's host — /mnt/raid0 does not exist here).
- Your package: ${p.id}. Repo: ${r.name}. Your git worktree: ${p.wt} (branch wt/${p.id.toLowerCase()}, cut from ${BASE_BRANCH}). Package brief with the full audit evidence: ${S}/pkg/${p.id}.md — read it first.
- Edit and commit ONLY inside ${p.wt}. Never edit ${r.base} (the base checkout, used read-only to check whether a failure pre-exists), other worktrees under /workspace/wt, or /home/user/epyc-root. Never push. epyc-root (governance docs, handoffs, operator artifacts) is readable at /workspace/epyc-root.

RESUMPTION (read first)
- An earlier implementer for this package may have been cut off by a usage limit. Run \`git -C ${p.wt} log --oneline ${BASE_BRANCH}..HEAD\` and \`git -C ${p.wt} status --short\` first. Findings whose id appears in a commit subject are done: re-check them briefly as you go, do not redo them. Uncommitted edits and untracked files are a PARTIAL attempt at the next finding(s): read the diff, run the relevant tests, and either finish and commit it (if sound) or discard it (\`git -C ${p.wt} checkout -- <file>\`, delete untracked files). Delete stray scratch tests (e.g. tests/unit/test_zz_scratch_*.py).
- The account has a 5-hour usage window and no overage credits. Be economical: read large files by line range (sed -n / Read offset), grep before reading, do not re-read files you already have in context, and commit each finding as soon as it is verified so an interruption loses nothing.

HOW TO WORK EACH FINDING
1. The audit is from 2026-10-07; the code has moved since (hundreds of upstream commits). The finding TEXT is its identity, line numbers are only hints. Re-locate the code at your worktree's HEAD and re-confirm the defect first-hand. If it is already fixed, the code is gone, or it does not reproduce, SKIP it and say why.
2. Bugs: first write a regression test that FAILS on the current code, then fix, then show it passes. Behaviour-preserving refactors/deletions: make sure existing tests cover the behaviour you must keep; add a characterization test if they do not.
3. Follow the verifier's corrected proposal and the production-safety conditions in the brief where present; they override the original proposal. If a safety review says 'no', skip the item and explain.
4. One commit per finding (or a tight group of findings that share one root cause). Commit message: "<area>: <what changed> (<finding ids>)", a blank line, 2-6 lines on why and how it was verified, then exactly these trailer lines:
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   Claude-Session: https://claude.ai/code/session_01C4SLLAQhop8AA9rJJusAYj
   Stage specific paths with \`git add <paths>\` (wholesale \`git add -A/-u/.\` is refused by a repo hook).

HARD CONSTRAINTS
- Do NOT modify: frozen kernel trees; epyc-root MEASUREMENT.md, measurement/, agents/shared/, artifacts/operator/; the autopilot evaluator-fingerprinted files scripts/autopilot/eval_tower.py, scripts/autopilot/rubric_scoring.py, src/autopilot_core/tier_specs.py, orchestration/eval_registry.yaml (any byte change splits the AP-55 evaluator regime — pending an operator decision). If a fix needs one of these, stop on that item and report exactly what edit is needed.
- epyc-orchestrator: tests/fixtures/ni63_capacity_child/source_clone.py byte-pins ~30 source files (SOURCE_PINS). If you modify a pinned file, update its (git blob sha1, sha256) entry: \`git hash-object <f>\` and \`sha256sum <f>\`.
- Do not reformat code you did not otherwise change (no blanket ruff format). Run \`ruff check\` on the files you changed and fix what you introduced.
- Bloat matters to the operator: prefer deletion and reuse over new code; no speculative abstractions; keep comments concise and factual in the repo's style (an origin note is 1-3 lines, not an essay). Report net LOC per commit.
- Live paths on the operator's host (coordination with session workspace-58, 2026-10-24): make NO structural refactor of epyc-orchestrator scripts/server/orchestrator_stack.py, scripts/region-lock, src/runtime/*region_lock*, scripts/gitnexus-analyze.sh — a bug fix there is allowed as its own commit. Never touch llama.cpp trees. In epyc-inference-research, scripts/benchmark/ and scripts/kernel_rnd/autokernel/ are pinned by SHA by running jobs: changes are fine on this branch, but say in your report which files changed so the merge can re-pin deliberately.
- Process safety: never pkill/pgrep/killall by name pattern; kill only PIDs you started. Never touch /mnt/raid0.
- Kernel (llama.cpp) defects are not patched in these repos: per the standing operator rule (2026-10-24) they are recorded as a recommendation for the champion fold (a CH-xx item in /workspace/epyc-root/handoffs/active/autokernel-champion-aggregate.md); report them, do not edit that file.

TESTING
- Run tests with: ${r.test}   (at most -n 2; never the full suite — the box is shared by ~6 agents and a full baseline run). Pick the test files that exercise the code you touched (grep tests for the module/symbol names) plus the files the brief names.
- Baseline failures exist (host-dependent tests). Reference list: ${r.baseline}. To decide whether a failure is yours, run the same test id in the base checkout ${r.base} (read-only, unmodified ${BASE_BRANCH} head). A failure that also happens there is pre-existing; one that does not is yours to fix before you finish.
- A repo hook blocks writes outside /workspace/** and /tmp/** and refuses unresolvable redirect targets (e.g. a path held in a shell variable); write scratch files under ${S}/${p.id}/.

FINAL REPORT (your final message is data for the integrator; be complete and precise)
- Per finding id: status (done | skipped-already-fixed | skipped-not-reproducible | skipped-unsafe | blocked-needs-operator), one-line reason, commit hash(es), tests added, net LOC.
- The exact test commands you ran and their pass/fail counts, and any failure you believe is pre-existing with the evidence.
- Anything the integrator must know (cross-package edits you needed, files outside your package's area you touched, follow-ups).
`
}

const packages = args.packages

const results = await pipeline(
  packages,
  async (p) => {
    const reports = []
    for (let i = 0; i < p.stages.length; i++) {
      const ids = p.stages[i]
      const prior = reports.length ? `\n\nEARLIER STAGE(S) IN THIS WORKTREE ALREADY RAN; their reports:\n${reports.join('\n---\n')}\n` : ''
      const extra = p.priorReports ? `\n\nREPORTS FROM EARLIER, ALREADY-COMPLETED STAGES (files):\n${p.priorReports.join('\n')}\n` : ''
      const rep = await agent(
        `${rules(p)}\nYOUR TASK (stage ${i + 1} of ${p.stages.length}): implement these findings from the brief, in this order: ${ids.join(', ')}. ${p.stageNotes ? p.stageNotes[i] || '' : ''}${prior}${extra}`,
        { label: `impl:${p.id}${p.stages.length > 1 ? '.' + (i + 1) : ''}`, phase: 'Implement', model: p.model })
      if (!rep) { log(`${p.id} stage ${i + 1} returned nothing (likely usage limit); skipping its later stages`); reports.push('(stage returned nothing: interrupted)'); return reports }
      reports.push(rep)
    }
    return reports
  },
  async (reports, p) => {
    if (reports.some(r => r.startsWith('(stage returned nothing'))) return { id: p.id, reports, review: null, interrupted: true }
    const review = await agent(
      `${rules(p)}\nYOUR TASK: you are the ADVERSARIAL REVIEWER for package ${p.id}. The implementer(s) committed their work on branch wt/${p.id.toLowerCase()} in ${p.wt}. Review \`git -C ${p.wt} log ${BASE_BRANCH}..HEAD\` and \`git -C ${p.wt} diff ${BASE_BRANCH}...HEAD\` commit by commit against the brief. Hunt for: correctness bugs the change introduced; behaviour changes that were not intended or not flagged; regression tests that would pass even without the fix (prove each new bug test fails on the parent commit by checking out the parent's version of the source file into a temp copy, or by reverting the source hunk temporarily and restoring it); deletions that still have a live reference anywhere in the three repos (re-grep, including string/subprocess/Makefile/yaml/doc-instructed uses); concurrency and error-path mistakes; production risk; needless added code or prose (bloat). FIX what you find with additional commits (same commit format), and run the relevant tests. Do not rewrite or squash existing commits.\n\nIMPLEMENTER REPORTS:\n${reports.join('\n---\n')}${p.priorReports ? '\n\nEARLIER STAGE REPORT FILES: ' + p.priorReports.join(', ') : ''}\n\nFINAL REPORT: list each issue you found (commit, problem, fix commit or why left), the tests you ran with counts, and a verdict per finding id: accept | accept-with-fixes | reject (explain; rejected commits must be reverted by you with a revert commit).`,
      { label: `review:${p.id}`, phase: 'Review' })
    return { id: p.id, reports, review }
  },
)
return results.filter(Boolean)
