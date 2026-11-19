#!/usr/bin/env python3
"""Source-bound progressive FINAL contract repair; no copied producer tree.

Load producer objects from Git, refuse drift, and apply only the declared contract
edits in memory. Corpus, observation rendering and scorer remain producer code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

SOURCE_REPO = Path('/mnt/raid0/llm/epyc-orchestrator')
SOURCE_COMMIT = 'fe2c0b9e3b5c127aef300229a66a9e5197a8a93a'
PREFIX = 'scripts/benchmark/'
VARIANT = 'progressive-final-contract-v2'
CONTRACT = '''Final submission contract (available from turn 1): wait until Q7 is revealed
(turn 7 or later) before calling FINAL. Earlier FINAL calls are rejected and do
not end the episode. Submit exactly these keys: lead, site, region, budget_k,
lead_rate, mult_pct, loaded_budget_k. Use strings for lead/site/region and integers
for the other fields. Continue researching and preserve the needed facts until Q7.
'''
FEEDBACK = '\\nError: premature FINAL rejected; wait until Q7 (turn 7). Continue researching.'


def source(name):
    return subprocess.check_output(['git', '-C', str(SOURCE_REPO), 'show',
                                    f'{SOURCE_COMMIT}:{PREFIX}{name}.py']).decode()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('source contract drift: expected exactly one patch site')
    return text.replace(old, new, 1)


def repaired_fixture(text):
    text = replace_once(text, 'INTRO = """You are working',
                        'INTRO = ' + repr(CONTRACT) + ' + """You are working')
    # Reject before recording history, so the error survives into the next prompt.
    text = replace_once(text, '        turns.append({"code": code, "obs": obs, "reply": reply})\n        if r["final"]:',
                        '        if r["final"] and t < 7:\n'
                        '            obs += ' + repr(FEEDBACK.replace('\\n', '\n')) + '\n'
                        '            turns.append({"code": code, "obs": obs, "reply": reply})\n'
                        '            continue\n'
                        '        turns.append({"code": code, "obs": obs, "reply": reply})\n'
                        '        if r["final"]:')
    return text


def load_driver(*, fixture_transform=repaired_fixture, variant=VARIANT, extra_binding=None):
    names = ('repl_composite_fixture', 'run_repl_composite', 'run_repl_preview',
             'repl_preview_fixture', 'own_port_proof')
    texts = {n: source(n) for n in names}
    fixture = fixture_transform(texts['repl_composite_fixture'])
    binding = {'variant': variant, 'source_commit': SOURCE_COMMIT,
               'producer_sha256': {n: hashlib.sha256(t.encode()).hexdigest() for n, t in texts.items()},
               'fixture_contract_sha256': hashlib.sha256(fixture.encode()).hexdigest(),
               'wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    if extra_binding:
        binding.update(extra_binding)
    binding['variant_sha256'] = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
    modules = {}

    def load(name):
        if name not in modules:
            m = types.ModuleType(name)
            m.__file__ = f'{SOURCE_REPO}/{PREFIX}{name}.py'
            modules[name] = m
            sys.modules[name] = m
            code = fixture if name == 'repl_composite_fixture' else texts[name]
            # Replace file-based dependency resolution with pinned Git object loading.
            if name == 'run_repl_composite':
                start = code.index('def _load(')
                end = code.index('\n\n', code.index('    return m', start))
                code = code[:start] + 'def _load(name):\n    return _pinned_load(name)\n' + code[end:]
                m._pinned_load = load
            if name == 'run_repl_preview':
                start = code.index('_spec = importlib.util.spec_from_file_location')
                end = code.index('\n', code.index('_spec.loader.exec_module(fx_mod)', start))
                code = code[:start] + 'fx_mod = _pinned_load("repl_preview_fixture")' + code[end:]
                start = code.index('    ops = importlib.util.spec_from_file_location')
                end = code.index('\n', code.index('    ops.loader.exec_module(m)', start))
                code = code[:start] + '    m = _pinned_load("own_port_proof")' + code[end:]
                m._pinned_load = load
            exec(compile(code, m.__file__, 'exec'), m.__dict__)
        return modules[name]

    driver = load('run_repl_composite')
    # Bind both result JSON and every retained cell record to the variant.
    original_row = driver.row_of

    def row_of(*args):
        return {**original_row(*args), 'contract_binding': binding}

    driver.row_of = row_of
    return driver, binding


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    driver, binding = load_driver()
    return run_bound(driver, binding, argv)


def run_bound(driver, binding, argv):
    if argv == ['--binding']:
        print(json.dumps(binding, indent=2))
        return 0
    if '--cell-dir' in argv:
        cells = Path(argv[argv.index('--cell-dir') + 1])
        marker = cells / 'contract-binding.json'
        if cells.exists() and any(cells.iterdir()):
            if not marker.exists() or json.loads(marker.read_text()) != binding:
                raise ValueError('refusing unbound or different-variant cell directory')
        cells.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps(binding, sort_keys=True) + '\n')
    rc = driver.main(argv)
    for option in ('--out', '--smoke-out'):
        if option in argv:
            path = Path(argv[argv.index(option) + 1])
            result = json.loads(path.read_text())
            result['contract_binding'] = binding
            path.write_text(json.dumps(result, indent=1) + '\n')
    return rc


if __name__ == '__main__':
    sys.exit(main())
