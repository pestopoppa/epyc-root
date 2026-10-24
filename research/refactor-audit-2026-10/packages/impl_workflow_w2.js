export const meta = {
  name: 'epyc-refactor-impl',
  description: 'Implement audited work packages in isolated git worktrees, then adversarially review each diff',
  phases: [
    { title: 'Implement', detail: 'one implementer per package stage, in its own worktree' },
    { title: 'Review', detail: 'adversarial reviewer re-checks and fixes the package diff' },
  ],
}

function input(p, key, envName) {
  const value = p[key] || globalThis.process?.env?.[envName]
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`Missing ${key}: provide args.packages[].${key} or ${envName}`)
  }
  const normalized = value.trim()
  if (['worktree', 'baseCheckout', 'scratchRoot', 'python', 'regionLock'].includes(key) && !normalized.startsWith('/')) {
    throw new Error(`Invalid ${key}: expected an absolute host path from args.packages[].${key} or ${envName}`)
  }
  if (key === 'branch' && (!/^refactor\/[A-Za-z0-9._/-]+$/.test(normalized) || normalized.includes('..'))) {
    throw new Error(`Invalid branch: expected a safe refactor/* branch from args.packages[].branch or ${envName}`)
  }
  if (key === 'baseRef' && (!/^[A-Za-z0-9._/-]+$/.test(normalized) || normalized.startsWith('-') || normalized.includes('..'))) {
    throw new Error(`Invalid baseRef: expected a safe git ref from args.packages[].baseRef or ${envName}`)
  }
  if (key === 'id' && !/^[A-Za-z0-9._-]+$/.test(normalized)) throw new Error('Invalid package id: use letters, digits, dot, underscore, or hyphen')
  return normalized
}

function shellQuote(value) {
  return `'${value.replaceAll("'", "'\\''")}'`
}

function agentConfig(p) {
  const model = input(p, 'model', 'EPYC_REFACTOR_MODEL')
  const reasoning_effort = input(p, 'reasoningEffort', 'EPYC_REFACTOR_REASONING_EFFORT')
  if (!['low', 'medium', 'high', 'xhigh', 'max', 'ultra'].includes(reasoning_effort)) {
    throw new Error('Invalid reasoningEffort: use low, medium, high, xhigh, max, or ultra')
  }
  return { model, reasoning_effort }
}

function repoCtx(p) {
  if (p.repo === 'O') {
    const base = input(p, 'baseCheckout', 'EPYC_REFACTOR_ORCHESTRATOR_BASE')
    const python = input(p, 'python', 'EPYC_REFACTOR_ORCHESTRATOR_PYTHON')
    const worktree = input(p, 'worktree', 'EPYC_REFACTOR_ORCHESTRATOR_WORKTREE')
    const regionLock = input(p, 'regionLock', 'EPYC_REGION_LOCK')
    const scratch = `${input(p, 'scratchRoot', 'EPYC_REFACTOR_SCRATCH_ROOT')}/${p.id}`
    const inner = `cd ${shellQuote(worktree)} && CI=true ORCHESTRATOR_MOCK_MODE=1 ${shellQuote(python)} -m pytest -q -p no:cacheprovider -o addopts="" -n 2 <test paths>`
    return {
      name: 'epyc-orchestrator',
      base, python,
      test: `${shellQuote(regionLock)} run --cpu-list 0-95 --role build --tag refactor-${p.id} -- bash -c ${shellQuote(inner)}`,
      baseline: `Use a separate detached parent worktree at ${scratch}/baseline from ${input(p, 'baseRef', 'EPYC_REFACTOR_ORCHESTRATOR_BASE_REF')}; never run baseline tests in the shared base checkout. Record failures in ${scratch}/orch_baseline_failing_ids.txt.`,
    }
  }
  const base = input(p, 'baseCheckout', 'EPYC_REFACTOR_RESEARCH_BASE')
  const python = input(p, 'python', 'EPYC_REFACTOR_RESEARCH_PYTHON')
  const worktree = input(p, 'worktree', 'EPYC_REFACTOR_RESEARCH_WORKTREE')
  const regionLock = input(p, 'regionLock', 'EPYC_REGION_LOCK')
  const scratch = `${input(p, 'scratchRoot', 'EPYC_REFACTOR_SCRATCH_ROOT')}/${p.id}`
  const inner = `cd ${shellQuote(worktree)} && ${shellQuote(python)} -m pytest -q -p no:cacheprovider -n 2 <test paths>`
  return {
    name: 'epyc-inference-research',
    base, python,
    test: `${shellQuote(regionLock)} run --cpu-list 0-95 --role build --tag refactor-${p.id} -- bash -c ${shellQuote(inner)}`,
    baseline: `Use a separate detached parent worktree at ${scratch}/baseline from ${input(p, 'baseRef', 'EPYC_REFACTOR_RESEARCH_BASE_REF')}; never run baseline tests in the shared base checkout. Record failures in ${scratch}/ak_baseline_failing_ids.txt.`,
  }
}

function rules(p) {
  if (!['O', 'R'].includes(p.repo)) throw new Error(`Invalid repo for ${p.id}: use O or R`)
  const worker = agentConfig(p)
  const worktree = input(p, 'worktree', p.repo === 'O' ? 'EPYC_REFACTOR_ORCHESTRATOR_WORKTREE' : 'EPYC_REFACTOR_RESEARCH_WORKTREE')
  const baseRef = input(p, 'baseRef', p.repo === 'O' ? 'EPYC_REFACTOR_ORCHESTRATOR_BASE_REF' : 'EPYC_REFACTOR_RESEARCH_BASE_REF')
  const scratchRoot = input(p, 'scratchRoot', 'EPYC_REFACTOR_SCRATCH_ROOT')
  const branch = input(p, 'branch', 'EPYC_REFACTOR_BRANCH')
  input(p, 'id', 'EPYC_REFACTOR_PACKAGE_ID')
  const evaluatorConstraint = p.id === 'P5'
    ? 'P5 may change the four autopilot evaluator-fingerprinted files together on its branch under the approved single-era-event plan; this does not authorize merge or deploy.'
    : 'Do not modify the four autopilot evaluator-fingerprinted files; only approved package P5 may change them together under the single-era-event plan.'
  const r = repoCtx(p)
  return `
SETTING
- Follow the host coordination in the refactoring handoff: at most two workers, cheapest capable model and effort, CPU claims for tests/builds/server, no pushes from package agents, and no production kernel/service changes. This package uses ${worker.model} at ${worker.reasoning_effort} effort for implementation and review; it must be the cheapest setting capable of the work.
- Package ${p.id}, repo ${r.name}, worktree ${worktree} on branch ${branch}, based on ${baseRef}. Read the package brief at ${scratchRoot}/pkg/${p.id}.md first.
- Edit and commit ONLY inside ${worktree}. Base checkout ${r.base} is read-only. Do not push, modify main, use another package worktree, or touch frozen kernels or live services. Keep scratch under ${scratchRoot}/${p.id}/.

RESUMPTION (read first)
- Resume by inspecting \`git -C ${shellQuote(worktree)} log --oneline ${shellQuote(`${baseRef}..HEAD`)}\` and status. A finding is done only when its change and verification are present; an ID in a commit subject alone is not evidence. Inspect partial edits, then finish and verify or discard them. Delete stray scratch tests.
- Be economical: read large files by line range, grep before reading, do not re-read files already in context, and commit each finding as soon as it is verified so an interruption loses nothing.

HOW TO WORK EACH FINDING
1. The audit is from 2026-10-07; the code has moved since (hundreds of upstream commits). The finding TEXT is its identity, line numbers are only hints. Re-locate the code at your worktree's HEAD and re-confirm the defect first-hand. If it is already fixed, the code is gone, or it does not reproduce, SKIP it and say why.
2. Bugs: first write a regression test that FAILS on the current code, then fix, then show it passes. Behaviour-preserving refactors/deletions: make sure existing tests cover the behaviour you must keep; add a characterization test if they do not.
3. Follow the verifier's corrected proposal and the production-safety conditions in the brief where present; they override the original proposal. If a safety review says 'no', skip the item and explain.
4. One commit per finding (or a tight group of findings that share one root cause). Commit message: "<area>: <what changed> (<finding ids>)", a blank line, 2-6 lines on why and how it was verified. Do not invent author or session trailers.
   Stage specific paths with \`git add <paths>\` (wholesale \`git add -A/-u/.\` is refused by a repo hook).

HARD CONSTRAINTS
- Do NOT modify: frozen kernel trees; epyc-root MEASUREMENT.md, measurement/, agents/shared/, artifacts/operator/. ${evaluatorConstraint} If another package needs a locked file, stop that item and report the requested change.
- epyc-orchestrator: tests/fixtures/ni63_capacity_child/source_clone.py byte-pins ~30 source files (SOURCE_PINS). If you modify a pinned file, update its (git blob sha1, sha256) entry: \`git hash-object <f>\` and \`sha256sum <f>\`.
- Do not reformat code you did not otherwise change (no blanket ruff format). Run \`ruff check\` on the files you changed and fix what you introduced.
- Bloat matters to the operator: prefer deletion and reuse over new code; no speculative abstractions; keep comments concise and factual in the repo's style (an origin note is 1-3 lines, not an essay). Report net LOC per commit.
- The launcher changes child cwd, so commands must include an explicit inner \`cd ${worktree} &&\`. Keep tests targeted and at most two workers. Inference kernels and production services remain untouched.
- Process safety: never pkill/pgrep/killall by name pattern; kill only PIDs you started.
- Live paths: do not structurally refactor epyc-orchestrator \`scripts/server/orchestrator_stack.py\`, \`scripts/region-lock\`, \`src/runtime/*region_lock*\`, or \`scripts/gitnexus-analyze.sh\`; a bug fix is allowed as its own commit. Research \`scripts/benchmark/\` and \`scripts/kernel_rnd/autokernel/\` are pinned by running jobs; if changed, list them so merge can re-pin.
- Kernel (llama.cpp) defects are not patched in these repos: per the standing operator rule (2026-10-24) they are recorded as a recommendation for the champion fold (a CH-xx item in /workspace/epyc-root/handoffs/active/autokernel-champion-aggregate.md); report them, do not edit that file.

TESTING
- Run tests with: ${r.test}. This command includes the required CPU region claim. Pick only relevant files; never run the full suite. To check a failure against the parent, create a separate detached worktree at the base ref and run there; never test in the shared base checkout. Baseline: ${r.baseline}.
- Required package inputs: \`worktree\`, \`baseCheckout\`, \`baseRef\`, \`branch\`, \`scratchRoot\`, \`python\`, \`regionLock\`, \`model\`, and \`reasoningEffort\`, or corresponding \`EPYC_REFACTOR_*\` / \`EPYC_REGION_LOCK\` environment values. Missing or unsafe values raise a named error before work starts. All path inputs must be absolute host paths.

FINAL REPORT (your final message is data for the integrator; be complete and precise)
- Per finding id: status (done | skipped-already-fixed | skipped-not-reproducible | skipped-unsafe | blocked-needs-operator), one-line reason, commit hash(es), tests added, net LOC.
- The exact test commands you ran and their pass/fail counts, and any failure you believe is pre-existing with the evidence.
- Anything the integrator must know (cross-package edits you needed, files outside your package's area you touched, follow-ups).
`
}

function reviewPrompt(p, reports) {
  const branch = input(p, 'branch', 'EPYC_REFACTOR_BRANCH')
  const worktree = input(p, 'worktree', p.repo === 'O' ? 'EPYC_REFACTOR_ORCHESTRATOR_WORKTREE' : 'EPYC_REFACTOR_RESEARCH_WORKTREE')
  const baseRef = input(p, 'baseRef', p.repo === 'O' ? 'EPYC_REFACTOR_ORCHESTRATOR_BASE_REF' : 'EPYC_REFACTOR_RESEARCH_BASE_REF')
  return `${rules(p)}\nYOUR TASK: adversarially review package ${p.id} on branch ${branch} in ${worktree}. Inspect \`git -C ${shellQuote(worktree)} log ${shellQuote(`${baseRef}..HEAD`)}\` and \`git -C ${shellQuote(worktree)} diff ${shellQuote(`${baseRef}...HEAD`)}\` commit by commit against the brief. Check for correctness regressions, unintended behavior, regression tests that pass without the fix (prove each fails against a safe isolated parent worktree), live references to deletions across the three repos, concurrency/error-path issues, production risk, and needless code. Fix issues with additional commits; do not rewrite or squash. Revert rejected commits and remove their introduced artifacts.\n\nIMPLEMENTER REPORTS:\n${reports.join('\n---\n')}${p.priorReports ? '\n\nEARLIER STAGE FILES: ' + p.priorReports.join(', ') : ''}\n\nFINAL REPORT: list issues found and a verdict per finding id: accept | accept-with-fixes | reject, with reasons and test commands/counts.`
}

const packages = args.packages

for (const p of packages) {
  p.id = input(p, 'id', 'EPYC_REFACTOR_PACKAGE_ID')
  if (!['O', 'R'].includes(p.repo)) throw new Error(`Invalid repo for ${p.id}: use O or R`)
  rules(p)
}

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
        { label: `impl:${p.id}${p.stages.length > 1 ? '.' + (i + 1) : ''}`, phase: 'Implement', ...agentConfig(p) })
      if (!rep) { log(`${p.id} stage ${i + 1} returned nothing (likely usage limit); skipping its later stages`); reports.push('(stage returned nothing: interrupted)'); return reports }
      reports.push(rep)
    }
    return reports
  },
  async (reports, p) => {
    if (reports.some(r => r.startsWith('(stage returned nothing'))) return { id: p.id, reports, review: null, interrupted: true }
    const review = await agent(
      reviewPrompt(p, reports),
      { label: `review:${p.id}`, phase: 'Review', ...agentConfig(p) })
    return { id: p.id, reports, review }
  },
)
return results.filter(Boolean)
