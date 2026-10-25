#!/usr/bin/env python3
"""Grant-only synthetic producer and parent integration; no servers or network."""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'regression/fixtures/bundle_gate_c5.original.sh'
NEW = ROOT / 'bundle_gate_c5.sh'
PRODUCER = ROOT / 'regression/fixtures/greedy_compare_c5.py'


def function(text, name):
    start = text.index(name + '() {')
    return text[start:text.index('\n}\n', start) + 3]


with tempfile.TemporaryDirectory(prefix='c5-r2-', dir=os.environ.get('TMPDIR', '/mnt/raid0/llm/tmp')) as scratch:
    tmp = Path(scratch)
    old, new = OLD.read_text(), NEW.read_text()
    helper = function(new, 'bundle_gate_verdict_rc')
    (tmp / 'helper.sh').write_text(helper)
    spec = importlib.util.spec_from_file_location('actual_c5_producer', PRODUCER)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    build = tmp / 'build'
    (build / 'bin').mkdir(parents=True)
    (build / 'bin/llama-server').touch()
    producer.frozen_prompt = lambda: [42]
    producer.server_argv = lambda *args: (['intercepted-no-server'], {'LD_LIBRARY_PATH': str(build / 'bin')})

    def generated(mode, outcome):
        """Run the real main/classify/smoke serializer, replacing only external arms."""
        def fake_arm(name, build, ops, args, prompts):
            result = {'arm': name, 'build': str(build), 'env_ops': ops,
                      'prompts': {}, 'completed': True, 'confirmed_dead': True,
                      'requested_fused_env': {}, 'proc_fused_env': {},
                      'refusal_logged': False, 'tmp_new_files': [], 'foreign_flash_next': []}
            for prompt, _ in prompts:
                tokens = [10, 20, 30]
                if name == 'C5DEF' and mode == 'identity' and outcome == 'DIVERGES':
                    tokens = [10, 21, 30]
                if name == 'C5OFF' and mode == 'identity' and outcome == 'LENGTH':
                    tokens = [10, 20]
                result['prompts'][prompt] = {'tokens': tokens, 'top2': [],
                    'predicted_per_token_ms': 4 if name == 'C5ON' else 1}
            if mode == 'smoke' and name == 'C5ON':
                if outcome == 'INCONCLUSIVE':
                    for p in result['prompts'].values():
                        p['predicted_per_token_ms'] = 2
                if outcome == 'FAIL':
                    result['tmp_new_files'] = ['synthetic-write']
            return result
        producer.run_arm = fake_arm
        out = tmp / ('producer-' + mode + '-' + outcome)
        args = ['fixture', '--out', str(out), '--execute']
        arms = ['CHAMP', 'C5DEF', 'C5OFF'] if mode == 'identity' else ['C5DEF', 'C5ON']
        for arm in arms:
            args += ['--arm', arm + '=' + str(build)]
        args += ['--expect-identical', 'C5DEF,C5OFF'] if mode == 'identity' else ['--prompts', 'p1,p2', '--smoke-arm', 'C5ON', '--tmp-watch', str(tmp)]
        saved = sys.argv
        try:
            sys.argv = args
            with contextlib.redirect_stdout(io.StringIO()):
                rc = producer.main()
        finally:
            sys.argv = saved
        return json.loads((out / 'greedy.json').read_text()), rc

    identity, rc = generated('identity', 'PASS')
    assert rc == 0
    diverges, rc = generated('identity', 'DIVERGES')
    assert rc == 1 and diverges['verdict_vs_CHAMP']['C5DEF']['p1'].startswith('DIVERGES')
    length, rc = generated('identity', 'LENGTH')
    assert rc == 1 and length['verdict_vs_CHAMP']['C5OFF']['p1'].startswith('LENGTH')
    smoke, rc = generated('smoke', 'PASS')
    assert rc == 0
    inconclusive, rc = generated('smoke', 'INCONCLUSIVE')
    assert rc == 5
    failed_smoke, rc = generated('smoke', 'FAIL')
    assert rc == 1

    def check(name, mode, document, expected, child=0, raw=None):
        path = tmp / 'result.json'
        path.unlink(missing_ok=True)
        if document is not None or raw is not None:
            path.write_text(raw if raw is not None else json.dumps(document))
        result = subprocess.run(['bash', '-c', 'source "$1"; bundle_gate_verdict_rc "$2" "$3" "$4"',
                                 'fixture', str(tmp / 'helper.sh'), str(child), str(path), mode], capture_output=True, text=True)
        assert result.returncode == expected, (name, result.returncode, expected, result.stdout, result.stderr)
        print('PASS:', name, 'rc=' + str(result.returncode), flush=True)

    check('native identity PASS', 'identity', identity, 0)
    check('native DIVERGES despite child rc0', 'identity', diverges, 1)
    check('native LENGTH despite child rc0', 'identity', length, 1)
    check('native smoke PASS', 'smoke', smoke, 0)
    check('native smoke FAIL despite child rc0', 'smoke', failed_smoke, 1)
    check('native INCONCLUSIVE child5', 'smoke', inconclusive, 5, child=5)
    check('native INCONCLUSIVE child0', 'smoke', inconclusive, 5)
    check('child7 preserved', 'smoke', smoke, 7, child=7)
    check('PASS incompatible child5', 'smoke', smoke, 1, child=5)
    check('identity child5 is failure', 'identity', identity, 5, child=5)
    for mode, base in [('identity', identity), ('smoke', smoke)]:
        check(mode + ' missing file', mode, None, 1)
        check(mode + ' malformed', mode, None, 1, raw='{"schema":')
        check(mode + ' duplicate', mode, None, 1, raw='{"schema":1,' + json.dumps(base)[1:])
        for constant in ['NaN', 'Infinity', '-Infinity', '1e999']:
            check(mode + ' nonfinite ' + constant, mode, None, 1, raw=json.dumps(base)[:-1] + ',"extra":' + constant + '}')
        for field in ['completed', 'confirmed_dead']:
            bad = copy.deepcopy(base); bad['results'][0][field] = False
            check(mode + ' arm ' + field, mode, bad, 1)
        bad = copy.deepcopy(base); del bad['results'][0]['prompts']['p1']
        check(mode + ' missing prompt', mode, bad, 1)
        bad = copy.deepcopy(base); bad['verdict'] = 'FAIL'
        check(mode + ' contradictory envelope verdict', mode, bad, 1)
        for field in ['schema', 'results']:
            bad = copy.deepcopy(base); del bad[field]
            check(mode + ' missing ' + field, mode, bad, 1)
    bad = copy.deepcopy(identity); bad['results'][1]['prompts']['p1']['tokens'][0] = 99
    check('identity flag contradicts token evidence', 'identity', bad, 1)
    bad = copy.deepcopy(identity); bad['identity']['C5DEF'] = False
    check('identity contradictory false flag', 'identity', bad, 1)
    bad = copy.deepcopy(identity); del bad['verdict_vs_CHAMP']['C5DEF']['p3']
    check('identity missing verdict prompt', 'identity', bad, 1)
    for ratio in [2.99, None, True]:
        bad = copy.deepcopy(smoke); bad['smoke']['ratio'] = ratio
        check('smoke PASS invalid engagement ' + str(ratio), 'smoke', bad, 1)
    bad = copy.deepcopy(smoke); bad['smoke']['ratio'] = 3
    check('smoke existing inclusive boundary 3', 'smoke', bad, 0)
    bad = copy.deepcopy(inconclusive); bad['smoke']['ratio'] = 3
    check('INCONCLUSIVE contradicts engagement', 'smoke', bad, 1)
    for field, value in [('completed', False), ('confirmed_dead', False), ('tmp_new_files', ['write']), ('refusal_logged', True)]:
        bad = copy.deepcopy(smoke); bad['smoke'][field] = value
        check('smoke summary ' + field, 'smoke', bad, 1)
    bad = copy.deepcopy(smoke); bad['results'][1]['tmp_new_files'] = ['write']
    check('smoke summary contradicts arm writes', 'smoke', bad, 1)

    comparison = {'schema': 'epyc.fold.gate_compare.v1', 'surface': 'q38fn', 'comparison': {
        'schema': 'epyc.autokernel.serving_ab.v2', 'metric': 'aggregate_tok_s', 'pairs': 5,
        'anchor_samples': [10, 11, 12, 13, 14], 'candidate_samples': [9, 10, 11, 12, 13],
        'anchor_tok_s': 12, 'candidate_tok_s': 11, 'effect_pct': -8.333333333333337,
        'noise_floor_pct': None, 'floor_unit': None, 'decisive': None}}
    check('q38fn negative sign is accepted without invented floor', 'gate_compare', comparison, 0)
    check('q38fn missing file', 'gate_compare', None, 1)
    check('q38fn malformed', 'gate_compare', None, 1, raw='{"comparison":')
    check('q38fn nested duplicate', 'gate_compare', None, 1,
          raw=json.dumps(comparison).replace('"pairs": 5', '"pairs": 5, "pairs": 5'))
    for constant in ['NaN', 'Infinity', '-Infinity', '1e999']:
        check('q38fn nonfinite ' + constant, 'gate_compare', None, 1,
              raw=json.dumps(comparison).replace('"anchor_tok_s": 12', '"anchor_tok_s": ' + constant))
    for location in ['envelope', 'comparison']:
        bad = copy.deepcopy(comparison)
        (bad if location == 'envelope' else bad['comparison'])['verdict'] = 'FAIL'
        check('q38fn unsupported verdict ' + location, 'gate_compare', bad, 1)
    for key, value in [('decisive', False), ('noise_floor_pct', 3), ('anchor_tok_s', 0), ('candidate_samples', [9] * 4), ('anchor_samples', [True] * 5)]:
        bad = copy.deepcopy(comparison); bad['comparison'][key] = value
        check('q38fn invalid ' + key, 'gate_compare', bad, 1)
    for key in ['decisive', 'noise_floor_pct', 'floor_unit', 'anchor_samples']:
        bad = copy.deepcopy(comparison); del bad['comparison'][key]
        check('q38fn missing ' + key, 'gate_compare', bad, 1)
    check('q38fn child7', 'gate_compare', comparison, 7, child=7)

    # Execute each actual parent steps body. Only its child command is intercepted;
    # helper Python retains its absolute path and real JSON checking implementation.
    for outcome, fixture in [('DIVERGES', diverges), ('LENGTH', length)]:
        fixture_path = tmp / (outcome + '.json'); fixture_path.write_text(json.dumps(fixture))
        for label, source, expected in [('old', old, 0), ('new', new, 1)]:
            run = tmp / (label + '-' + outcome); run.mkdir()
            body = function(source, 'steps')
            needle = '/usr/bin/python3 -I "$GC"'
            assert body.count(needle) == 2
            body = body.replace(needle, 'fake_child')
            script = tmp / 'parent.sh'
            script.write_text('''set -uo pipefail
source "$1/helper.sh"
RUN=$2; FIXTURE=$3; ITEMS=c; D=$1; GC=intercepted; CHAMP=anchor; CAND=candidate; CS_CPUS=0; CS_PORT=1
say() { :; }
has() { [ "$1" = c ]; }
ncpus() { echo 1; }
fake_child() {
 local output='' prev=0 arg
 for arg in "$@"; do
   if [ "$prev" = 1 ]; then output=$arg; prev=0; continue; fi
   [ "$arg" = --out ] && prev=1
 done
 mkdir -p "$output"; cp "$FIXTURE" "$output/greedy.json"
 echo 'IDENTITY intercepted actual producer record, child rc0'
 return 0
}
''' + body + '\nsteps exec\n')
            result = subprocess.run(['bash', str(script), str(tmp), str(run), str(fixture_path)], capture_output=True, text=True)
            assert result.returncode == expected, (label, outcome, result.returncode, expected, result.stdout, result.stderr)
            print('PASS: actual', label, 'steps with producer', outcome, 'and child rc0 ->', result.returncode, flush=True)
    print('PASS: synthetic native-producer and parent regression; no server/API/network/build/real gate', flush=True)
