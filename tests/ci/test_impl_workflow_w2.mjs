import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { chmod, mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const source = await readFile(new URL('../../research/refactor-audit-2026-10/packages/impl_workflow_w2.js', import.meta.url), 'utf8')
const promptOnly = source.split('const packages = args.packages')[0].replace('export const meta', 'const meta')
const { input, agentConfig, repoCtx, rules, reviewPrompt, shellQuote } = new Function('process', `${promptOnly}\nreturn { input, agentConfig, repoCtx, rules, reviewPrompt, shellQuote }`)(process)

assert.throws(() => input({}, 'worktree', 'EPYC_REFACTOR_WORKTREE'), /Missing worktree.*EPYC_REFACTOR_WORKTREE/)
assert.throws(() => input({ worktree: 'relative/path' }, 'worktree', 'EPYC_REFACTOR_WORKTREE'), /expected an absolute host path/)
assert.throws(() => agentConfig({}), /Missing model.*EPYC_REFACTOR_MODEL/)
assert.deepEqual(agentConfig({ model: 'gpt-6-luna', reasoningEffort: 'low' }), { model: 'gpt-6-luna', reasoning_effort: 'low' })

const sandbox = await mkdtemp(join(tmpdir(), 'refactor-prompt-'))
try {
  const regionLock = join(sandbox, 'region-lock')
  const python = join(sandbox, 'python stub')
  await writeFile(regionLock, '#!/bin/bash\nwhile [ "$1" != "--" ]; do shift; done\nshift\nexec "$@"\n')
  await writeFile(python, '#!/bin/bash\nprintf "%s\\n" "$PWD"\n')
  await chmod(regionLock, 0o755)
  await chmod(python, 0o755)
  const common = {
    baseRef: 'origin/main', scratchRoot: join(sandbox, 'scratch'), python, regionLock,
    model: 'gpt-6-luna', reasoningEffort: 'low',
  }
  const orchestrator = {
    ...common, id: 'O7', repo: 'O', worktree: join(sandbox, "work 'tree/o7"),
    baseCheckout: '/workspace/repos/epyc-orchestrator', branch: 'refactor/test-hazards',
  }
  const research = {
    ...common, id: 'AK1', repo: 'R', worktree: join(sandbox, "work 'tree/ak1"),
    baseCheckout: '/workspace/repos/epyc-inference-research', branch: 'refactor/autokernel-loop-bugs',
  }
  for (const p of [orchestrator, research]) await mkdir(p.worktree, { recursive: true })

  const prompt = rules(orchestrator)
  assert.match(prompt, /at most two workers/)
  assert.match(prompt, /Do not push, modify main/)
  assert.match(prompt, /ID in a commit subject alone is not evidence/)
  assert.match(prompt, /gpt-6-luna at low effort/)
  assert.match(prompt, /Do not modify the four autopilot evaluator-fingerprinted files/)
  assert.doesNotMatch(prompt, /claude\/vigilant-thompson|Claude-Session|Co-Authored-By: Claude|\/tmp\/claude-0/)
  assert.match(repoCtx(orchestrator).baseline, /separate detached parent worktree/)

  for (const p of [orchestrator, research]) {
    const command = repoCtx(p).test.replace('<test paths>', 'tests/example.py')
    assert.equal(execFileSync('/bin/bash', ['-c', command], { encoding: 'utf8' }).trim(), p.worktree)
    const review = reviewPrompt(p, ['checked'])
    assert.match(review, /gpt-6-luna at low effort/)
    assert.match(review, /diff 'origin\/main\.\.\.HEAD'/)
    assert.match(review, /fails against a safe isolated parent worktree/)
    assert.match(review, /Revert rejected commits and remove their introduced artifacts/)
  }
  assert.throws(() => rules({ ...research, branch: 'main' }), /Invalid branch/)
  assert.throws(() => rules({ ...research, baseRef: 'main; echo unsafe' }), /Invalid baseRef/)
  assert.throws(() => rules({ ...research, repo: 'unknown' }), /Invalid repo/)

  const p5 = rules({ ...orchestrator, id: 'P5', branch: 'refactor/p5-batched-era' })
  assert.match(p5, /P5 may change the four autopilot evaluator-fingerprinted files together/)
  assert.match(p5, /does not authorize merge or deploy/)
  assert.match(prompt, /Do not modify the four autopilot evaluator-fingerprinted files/)
  console.log('prompt input, quoting, and isolation checks passed')
} finally {
  await rm(sandbox, { recursive: true, force: true })
}
