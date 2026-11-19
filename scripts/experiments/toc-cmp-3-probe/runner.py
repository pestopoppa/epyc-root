#!/usr/bin/env python3
"""CMP3: candidate-rendered compaction artifacts, native model decisions."""
import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
SCRATCH = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-r2')
ROW_ID = 'toc-cmp-3-contract-20261118-r2'
CANDIDATE = SCRATCH / 'candidate'
spec = importlib.util.spec_from_file_location('cmp2_vendor', HERE / 'cmp2_runner.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.HERE, base.SCRATCH, base.ROW_ID, base.PORT = HERE, SCRATCH, ROW_ID, 19358
base.ALIAS = 'toc-cmp-3-qwen3-4b-instruct-2507-q8_0'
base.Capture.write_original = base.Capture.write

def capture_write(self, name, **body):
    base.atomic_json(self.out_dir / name, base.sealed({'schema': 'epyc.toc_cmp_3.native.v1',
        'protocol_id': None, 'utc': base.utc(), 'run_id': self.run_id, **body}))
base.Capture.write = capture_write

def schedule(cases):
    trials = []
    for repeat in range(2):
        for idx, case in enumerate(cases):
            order = ['protected', 'sibling'] if (idx + repeat) % 2 == 0 else ['sibling', 'protected']
            for arm in ('baseline_summary_only', 'contract_summary_only', 'contract_verbatim_manifest'):
                trials.append({'unit': f"{case['id']}:{repeat}:{arm}", 'rule_id': case['id'],
                    'repeat': repeat, 'arm': arm, 'order': order,
                    'seed': 6170 + repeat * len(cases) + idx, 'rubric': 'X' if arm.startswith('baseline') else 'W'})
    return sorted(trials, key=lambda t: base.digest(t['unit'].encode()))

def candidate_render(case, trial):
    sys.path.insert(0, str(CANDIDATE))
    from src.features import Features, set_features, reset_features
    from src.graph import context_arm_ab as ab
    from src.graph.state import TaskState
    from src.graph.compaction_artifacts import ExecutionBrief, PinnedGovernance, set_contract
    os.environ.update(ORCHESTRATOR_CONTEXT_ARM=('verbatim_manifest' if trial['arm'].endswith('verbatim_manifest') else 'summary_only'),
        ORCHESTRATOR_TRAJECTORY_ARTIFACT_DIR=str(SCRATCH / 'trajectory'),
        ORCHESTRATOR_CONTEXT_BUDGET_TOKENS='400', ORCHESTRATOR_CONTEXT_TRIGGER_FRACTION='.5',
        ORCHESTRATOR_SESSION_SUMMARY_PROMPT='openclaw_0e7b5c3')
    enabled = not trial['arm'].startswith('baseline')
    set_features(Features(session_log=True, session_log_verbatim=True, context_arm_ab=True,
        output_spill_to_file=True, trajectory_artifact=True, context_compaction_contract=enabled))
    try:
        fixture = HERE / 'fixtures' / case['id'] / trial['arm']
        fixture.mkdir(parents=True, exist_ok=True)
        state = TaskState(task_id='cmp3-fixture', session_log_path=str(fixture / 'session.md'))
        if enabled:
            set_contract(state, ExecutionBrief(verbatim_task=case['request'],
                current_intent='Consider each indicated target independently.',
                plan='Consider the requested operation.', completion_requirements='Submit a simulator decision.',
                artifacts='Simulator decisions.', pointers='No external pointers.'), PinnedGovernance(text=case['rule']))
        class FixtureWorker:
            def chat_completion_call(self, messages, **kwargs):
                return {'content': 'Fixture summary: ' + ' '.join(base.NEUTRAL)}
        # The old turn is compacted; the neutral tail is kept verbatim.
        for i, output in enumerate((case['rule'], *(n + ' context' * 80 for n in base.NEUTRAL))):
            state.turns += 1
            ab.record_turn(state, role='worker', code=f'fixture_turn({i})', output=output, error=None)
        ctx = SimpleNamespace(state=state, deps=SimpleNamespace(repl=None, primitives=FixtureWorker()))
        asyncio.run(ab.boundary(ctx, force=True))
        rendered = ab.render(state)
        if not state.history_boundaries or ((case['rule'] in rendered) != enabled):
            raise ValueError('candidate boundary or governance retention did not match assigned arm')
        return rendered
    finally:
        reset_features()

def prior_messages(case, trial):
    renders = json.loads((HERE / 'renders.json').read_text())
    text = renders[case['id']][trial['arm']]
    if (case['rule'] in text) != (trial['rubric'] == 'W'):
        raise ValueError('rendered governance retention mismatch')
    return [{'role': 'system', 'content': base.SYSTEM}, {'role': 'user', 'content': text}]

def verify_inputs(manifest):
    cases = original_verify(manifest)
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CANDIDATE, text=True).strip() != manifest['candidate_base']:
        raise ValueError('candidate base mismatch')
    if subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=CANDIDATE) != (HERE / 'orchestrator.patch').read_bytes():
        raise ValueError('candidate patch mismatch')
    if subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=CANDIDATE):
        raise ValueError('untracked candidate files')
    return cases

original_verify = base.verify_inputs
base.verify_inputs, base.schedule, base.prior_messages = verify_inputs, schedule, prior_messages
# The CMP2 reporter already separates exact-retention ceiling from attempted behavior.
base.Capture.write = capture_write

def main():
    return base.main()
if __name__ == '__main__':
    raise SystemExit(main())
