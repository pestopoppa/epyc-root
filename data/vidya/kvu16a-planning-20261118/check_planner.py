"""Run the current AutoKernel planner against native replay on the full ledger."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path.cwd()
SCRATCH = Path(__file__).resolve().parent
RUN = Path('/mnt/raid0/llm/tmp/kvu/kvu16a-row-r3-20261104/native-load-tfz4cs9a')
SIDECAR = RUN / 'kvu16a_sampled_load.beliefs.jsonl'
BASE = SCRATCH / 'canonical.snapshot.jsonl'
CANONICAL = Path('/mnt/raid0/llm/state/vidya/ledger.jsonl')
RESEARCH = Path(os.environ.get('KVU16A_RESEARCH', SCRATCH)).resolve()
sys.path[:0] = [str(RESEARCH), str(RESEARCH / 'scripts/kernel_rnd'),
                str(ROOT / 'scripts/vidya')]
from scripts.kernel_rnd.autokernel.loop import actors, belief_context
from adapters import kvu16a_native
from ledger import Ledger
from fold import fold
from loop_beliefs import DEFAULT_MAX_CLAIMS, DEFAULT_MAX_BYTES, _now

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def json_write(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')

def main():
    out = Path(tempfile.mkdtemp(prefix='planner-', dir=SCRATCH))
    existing = os.environ.get('KVU16A_EXISTING_LEDGER')
    ledger = Path(existing).resolve() if existing else out / 'reprojected.jsonl'
    if not existing:
        ledger.write_bytes(BASE.read_bytes())
    inputs = {str(p): sha(p) for p in (SIDECAR, RUN/'result.json', RUN/'plan.json',
                                       RUN/'samples.jsonl', RUN/'server.log', CANONICAL, BASE)}
    native_row, = kvu16a_native.native_rows(SIDECAR)
    native = kvu16a_native.project(native_row)
    cid = f'clm_{native.measurement_id}'
    stamp = _now()
    argv = [sys.executable, '-B', str(ROOT/'scripts/vidya/cli.py'), '--ledger', str(ledger),
            '--json', 'ingest', 'kvu16a-sampled-load', '--path', str(SIDECAR), '--as-of', stamp]
    if not existing:
        ingest = json.loads(subprocess.check_output(argv, text=True))
        assert ingest['frames_emitted'] == 3 and not ingest['refused'] and ingest['rows_projected'] == 1
        json_write(out/'ingest.json', ingest)
        retry = json.loads(subprocess.check_output([*argv, '--dry-run', '--only-new'], text=True))
        assert retry['frames_emitted'] == 0 and retry['frames_skipped'] == 3
    amended_sha = sha(ledger)
    assert ledger.read_bytes().startswith(BASE.read_bytes())
    snapshots = []
    for path in (BASE, ledger):
        records = Ledger(path).read_all()
        state = fold([record.frame for record in records], as_of=stamp)
        belief = state.beliefs[cid]
        snapshots.append((len(records), str(belief.pro), set(belief.pro_paths), belief.pro_sources))
    print(snapshots, flush=True)
    assert snapshots[1][0] >= snapshots[0][0] + 3 and snapshots[1][1:] == snapshots[0][1:]
    if not existing:
        assert snapshots[1][0] == snapshots[0][0] + 3

    captures = {}
    argv_log = []
    cases = {
        'matching-gpu': (native.applicability['model_file'], 'Q8_0', 'gpu', ledger),
        'same-weights-cpu': (native.applicability['model_file'], 'Q8_0', 'cpu', ledger),
        'unrelated-gpu': ('Qwen3.6-35B-A3B-Q4_K_M.gguf', 'Q4_K_M', 'gpu', ledger),
        'legacy-baseline-gpu': (native.applicability['model_file'], 'Q8_0', 'gpu', BASE),
    }

    def child(argv, **kwargs):
        assert '--max-claims' not in argv and '--max-bytes' not in argv
        argv_log.append(argv)
        kwargs['env'] = {**(kwargs.get('env') or os.environ),
                         'VIDYA_READ_LOG': str(out/'reads.jsonl')}
        return subprocess.run([argv[0], '-B', *argv[1:]], **kwargs)

    def stop(self, prompt, backend, env, context, *, belief):
        belief_context.require_ready(belief)
        captures[context['check']] = belief, prompt
        return actors.Abstain(reason='KVU-16a context pre-backend check'), []

    with (patch.object(actors.AgentPlanner, '_proposal_from_agent', stop),
          patch.object(actors, '_run_agent', side_effect=AssertionError('planner entered the backend'))):
        for name, (model, quant, backend, path) in cases.items():
            case = out/name
            case.mkdir()
            index = case/'index.yaml'
            index.write_text('[]\n')
            alarms = case/'alarm.yaml'
            alarms.write_text(f'backend: file\nfile:\n  path: "{case / "alarms.jsonl"}"\n')
            config = belief_context.BeliefConfig(root=ROOT, ledger=path, index=index,
                      known_good=case/'known-good.json', alarm_config=alarms, alarm_state=case/'alarm-state.json')
            planner = actors.AgentPlanner(workspace=case/'workspace', belief=config, belief_runner=child)
            context = {'check': name, 'current_regime': {'model': {'path': model}, 'quant': quant, 'backend': backend}}
            assert isinstance(planner.propose(context), actors.Abstain)
            ready, prompt = captures[name]
            json_write(case/"ready.json", ready.answer)
            (case/"prompt.txt").write_text(prompt + "\n")
            print(name, ready.answer["targets"], ready.evidence["tiers_shown"],
                  ready.section in prompt, cid in ready.section, cid in prompt, flush=True)
            assert ready.section in prompt
            assert ready.ledger_state['ledger_path'] == str(path)
            targets = ready.answer['targets']
            assert (targets[0]['model_file'], targets[0]['backend']) == (model, backend)
            claims = [item for item in ready.evidence['claims'] if item['claim_id'] == cid]
            if name == 'legacy-baseline-gpu':
                assert not claims or claims[0]['value'] is None
                assert 'sampled_healthy_non_kv_bytes: ' + str(int(native.value)) + ' bytes' not in prompt
            elif name != 'matching-gpu':
                assert not claims and cid not in prompt
            else:
                assert cid in prompt
                claim, = claims
                assert (claim['tier'], claim['grade'], claim['value'], claim['unit'], claim['reps']) == (
                    'target', 'Judged/Located', native.value, native.unit, native.reps)
                assert str(int(native.value)) + ' bytes' in prompt
                assert 'Startup coverage UNKNOWN (unknown sample count: 1)' in prompt
                assert 'not a lifetime peak or bound' in prompt
            json_write(case/'ready.json', ready.answer)
            (case/'prompt.txt').write_text(prompt + '\n')
            receipt = case/actors.ACTOR_REPLY_DIR/belief_context.RECEIPT_LOG
            assert receipt.is_file()

    assert {p: sha(Path(p)) for p in inputs} == inputs and sha(ledger) == amended_sha
    json_write(out/'summary.json', {'claim_id': cid, 'value': native.value, 'unit': native.unit,
       'reps': native.reps, 'max_claims': DEFAULT_MAX_CLAIMS, 'max_bytes': DEFAULT_MAX_BYTES,
       'created_at': stamp, 'modified_ledger_sha256': amended_sha, 'source_inputs_sha256': inputs,
       'commands': argv_log, 'cases': list(cases), 'research_reader_sha256': sha(Path(belief_context.__file__)),
       'research_actors_sha256': sha(Path(actors.__file__)), 'root_reader_sha256': sha(ROOT/'scripts/vidya/loop_beliefs.py'),
       'root_adapter_sha256': sha(ROOT/'scripts/vidya/adapters/kvu16a_projection.py')})
    print(out)

if __name__ == '__main__':
    main()
