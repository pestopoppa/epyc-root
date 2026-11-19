"""Opt-in current guard bindings. Does not replace native boundary checks."""
import json
import hashlib
import os
import sys
from pathlib import Path

REVISION = 'current-guard-v3'
FRAMING_SHA = '9c782023a139941349fb664e79c666df5ea894a231395761053bae2dd03a3225'
FRAMING_RAW_SHA = '7cbf105def05e9f874080f6def041754b19c109c7c9ddab5b2d64bf4666a33ee'
PROJECTION = {
    'scripts/vidya/canonical.py': 'cda6809d24382cbbfa80308c9f8df4eca353f458039816753b1c20156adf1434',
    'scripts/vidya/adapters/kv_prefix_fork.py': 'e6ead7b654defc820abefb71b997c12b93b49bc1dc0ac036e2b5e72b50b4895d',
    'scripts/vidya/claim_tuple.py': '6ae969f7029c1a6356593fd2432eca2320931f22aa4a8c4e3a388a72b81944e7',
}
SCRATCH = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency')
R7_ID = 'kpf18-g3-r12-integration-cpu-r7'
R7_PINS = {
    'framing_result': '2b7eae2083bd5a116c8bd60db07a9a398154e8eb2d3b6098924a14d2eeeb8edf',
    'complete_marker': '2ebad10619e3a90c58bcc9e636205381ebc6beef7e76c4dec556a68e5e7f4691',
    'source_manifest': '4998ee152cedd2dd5079e8442b51293c9201bb0f1d655fe5ce92e47b331bbd1d',
    'root_source_manifest': 'e6beebeaeb9b996437fcfaef2dac56bc178e601a1bc6ea77cd6cfedd8cc5c19b',
}


def retained_r7(inputs, sealed_input):
    """Consume accepted metadata only; never replay X1 or claim live native custody."""
    records = {}
    for key, expected in R7_PINS.items():
        path = sealed_input(inputs.get(key, ''), expected)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('retained R7 prerequisite drift: ' + key)
        records[key] = data
    result = json.loads(records['framing_result'])
    complete = json.loads(records['complete_marker'])
    bridge = result.get('bridge_result', {})
    expected_result = {
        'schema': 'kpf18.r7.scheduled-result.v1', 'id': R7_ID,
        'status': 'COMPLETE', 'rc': 0, 'child_rc': 0,
        'cleanup_verified': True, 'work_started': True, 'partial': False,
        'controlled_cutoff': False, 'controlled_deadline': False,
        'controlled_storage_cutoff': False,
        'source_manifest_sha256': R7_PINS['source_manifest'],
        'root_source_manifest_sha256': R7_PINS['root_source_manifest'],
        'raw_sha256': FRAMING_RAW_SHA,
        'ledger_sha256': 'a6b18b1b96bc773fa74559c9bfc28248287c1dfcf08deb7ef07278d95d9f304a',
    }
    expected_bridge = {
        'framing_pass': True, 'grid_count': 1128, 'event_count': 8,
        'raw_sha256': expected_result['raw_sha256'],
        'ledger_sha256': expected_result['ledger_sha256'],
        'source_seal_sha256': R7_PINS['root_source_manifest'],
        'layouts_sha256': '546cd4eab6d500235b0702cf448f444cb0cbf3b564adefb018e430d3295ab39e',
        'fork_bindings_sha256': 'eacbebf58017d8f44da91df7db08cff8291e3a1b947448aa599fae6b067c2de7',
        'historical_r6_verdict': 'INVALID unchanged',
        'stages': ['draft_first_decode', 'draft_initial', 'target_prefix', 'target_suffix'],
    }
    expected_complete = {'schema': 'kpf18.r7.complete.v1', 'id': R7_ID,
                         'result_path': str(Path(inputs['framing_result'])),
                         'result_sha256': R7_PINS['framing_result']}
    for actual, expected in ((result, expected_result), (bridge, expected_bridge),
                             (complete, expected_complete)):
        if not isinstance(actual, dict) or any(
                type(actual.get(k)) is not type(v) or actual.get(k) != v
                for k, v in expected.items()):
            raise ValueError('retained R7 framing not valid')
    return {'framing_mode': 'retained-r7-v1', 'accepted_result_sha256': R7_PINS['framing_result']}


def prepare(seal, admission, captured):
    if seal.get('guard_revision') != REVISION or seal.get('binding_revision') != 'retained-bindings-v2':
        raise ValueError('explicit current guard revision required')
    admission.recheck(seal, captured)
    config = seal['execution']
    if config.get('mode', 'official') == 'publisher-smoke':
        grant = captured[2]
        if not isinstance(grant, tuple) or len(grant) != 2:
            raise ValueError('captured publisher result required')
        root = Path(grant[1]).parent
    else:
        root = Path(config.get('output_root', ''))
        if not root.is_absolute() or not root.is_relative_to(SCRATCH) or root == SCRATCH:
            raise ValueError('sealed private output root required')
    # Contract already binds the publisher path. Check all components again at
    # every access, including for official output, without creating anything.
    def output_root():
        admission.recheck(seal, captured)
        if not root.is_absolute():
            raise ValueError('absolute output required')
        for part in (root, *root.parents):
            if part.is_symlink() or not part.is_dir():
                raise ValueError('unsafe current output root')
        for alias in ('KPF_COMPOSITION_OUTPUT', 'KPF_OUTPUT_ROOT'):
            if alias in os.environ and os.environ[alias] != str(root):
                raise ValueError('redirected current output alias')
        return root

    output_root()
    def bind(driver):
        argv = sys.argv[1:]
        if (argv.count('--out') != 1 or any(arg.startswith('--out=') for arg in argv)
                or argv.index('--out') + 1 >= len(argv)
                or argv[argv.index('--out') + 1] != str(output_root())):
            raise ValueError('driver argv must name admitted output')
        guard = driver.guard
        origin = str(Path(guard.__file__).resolve())
        if origin not in seal['sources']:
            raise ValueError('unsealed retained guard')
        if getattr(guard, '_current_guard_bound', False):
            raise ValueError('current guard already bound')
        if driver.OUT != output_root():
            raise ValueError('driver output differs from admitted output')
        def sources():
            admission.recheck(seal, captured)
        def boundary():
            # Current admission replaces historical row/lock authority. Retain
            # the existing sampled reserve policy on the admitted filesystem.
            root = output_root()
            guard.output_reserve.check(guard.shutil.disk_usage(root).free,
                                       guard.output_reserve.owned_bytes(root))
            return int(os.environ['FILLER_END'])
        if config.get('mode', 'official') == 'official':
            retained_context = getattr(driver, 'RowflowContext', None)
            if not isinstance(retained_context, type):
                raise ValueError('retained full-run context required')
            class CurrentRowflowContext(retained_context):
                def check_boundary(self):
                    # Keep the retained terminal exception/latch, delegation,
                    # controller wrapper and unwind path. Only admission moves
                    # from the historical adapter to the captured current gate.
                    if self.terminal_refusal is not None:
                        self._refuse(self.terminal_refusal)
                    try:
                        boundary()
                        if self._original.out != output_root():
                            raise ValueError('context output differs from admitted output')
                        self._original.check_boundary()
                    except Exception as error:
                        self._refuse(f'current boundary refusal: {type(error).__name__}: {error}', error)
            driver.RowflowContext = CurrentRowflowContext
        # ContextBoundary resolves boundary/attempt_root through the retained
        # guard globals, so its original context checks and HWM cap survive.
        # Select the existing smoke function before main selects gate.ITEMS.
        # No environment flag is created and no driver bytes are rewritten.
        if config.get('mode', 'official') == 'publisher-smoke':
            driver.item3 = driver.item3_smoke
        gate_main = driver.gate.main
        def gate_entry():
            label = "publisher smoke" if config.get("mode", "official") == "publisher-smoke" else "current official gate"
            if config.get("mode", "official") == "official" and os.environ.get("KPF_SMOKE") == "1":
                raise ValueError("official gate refuses smoke selection")
            # The retained parser accepts other commands and write targets.
            # Admit only the sealed item3 recipe, before parser side effects.
            args = sys.argv[1:]
            if not args or args[0] != 'item3':
                raise ValueError(label + ' requires item3')
            values = {}
            allowed = {'--out', '--argv-file', '--prompt-set', '--fork-bin',
                       '--window-id', '--gpu-window-id', '--port', '--budget-min',
                       '--load-timeout-s', '--launch-prefix', '--card'}
            i = 1
            while i < len(args):
                option = args[i]
                if option == '--dry-run' and option not in values:
                    values[option] = True
                    i += 1
                    continue
                if (option not in allowed or option in values or i + 1 >= len(args)
                        or args[i + 1].startswith('--')):
                    raise ValueError('unsupported ' + label + ' argument')
                values[option] = args[i + 1]
                i += 2
            if values.get('--out') != str(output_root()) or driver.OUT != root:
                raise ValueError(label + ' output changed')
            if values.get('--fork-bin') != config['artifacts']['server']:
                raise ValueError(label + ' server mismatch')
            for option in ('--argv-file', '--prompt-set'):
                name = values.get(option)
                if name not in seal['sources'] or not Path(name).is_file():
                    raise ValueError(label + ' requires sealed prepared inputs')
            # Retained DEFAULT_PREFIX pins CPUs 184-191. Each admitted
            # run must inherit its admitted CPU mask; even a sealed
            # server path does not constrain an arbitrary prefix executable.
            if values.get('--launch-prefix', '') != '':
                raise ValueError(label + ' launch prefix must be empty')
            boundary()
            original_argv = sys.argv
            try:
                sys.argv = list(original_argv)
                if '--launch-prefix' not in values:
                    sys.argv.extend(['--launch-prefix', ''])
                # The keeper's exclusive GPU writer was captured before driver
                # import and rechecked by boundary() above. The retained gate
                # otherwise acquires a competing device claim of its own.
                # Caller-supplied claim bypasses remain outside allowed argv.
                sys.argv.extend(['--no-device-claim',
                                 'current captured keeper GPU writer; rechecked before gate entry'])
                return gate_main()
            finally:
                sys.argv = original_argv
        driver.gate.main = gate_entry
        def sealed_input(name, expected=None):
            path = Path(name)
            if (not path.is_absolute() or not path.is_file()
                    or str(path) not in seal['sources']
                    or (expected is not None and seal['sources'][str(path)] != expected)):
                raise ValueError('unsealed current prerequisite: ' + str(path))
            return path

        def enrollment():
            boundary()
            inputs = config.get('enrollment', {})
            mode = inputs.get('framing_mode', 'historical-r14')
            receipt = {}
            if mode == 'retained-r7-v1':
                receipt = retained_r7(inputs, sealed_input)
            elif mode == 'historical-r14':
                replay = sealed_input(inputs.get('framing_result', ''), FRAMING_SHA)
                result = json.loads(replay.read_text())
                if result.get('framing_pass') is not True or result.get('raw_sha256') != FRAMING_RAW_SHA:
                    raise ValueError('historical framing not valid')
            else:
                raise ValueError('unknown framing enrollment mode')
            canonical = Path(inputs.get('canonical_export', ''))
            for name, expected in PROJECTION.items():
                sealed_input(str(canonical / name), expected)
            # Preserve the retained framing/projection contract, with explicit
            # sealed locations instead of vanished historical directories.
            boundary()
            return {'canonical_export': str(canonical),
                    'scope': 'diagnostic; no new enrollment receipt', **receipt}

        preload = getattr(driver, 'load_preload_models', None)
        def load_preload(receipt, manifest):
            boundary()
            expected_receipt = sealed_input(config.get('preload_receipt', ''))
            expected_manifest = sealed_input(str(driver.BASE / 'ORIGINAL-MODELS.json'))
            if Path(receipt) != expected_receipt or Path(manifest) != expected_manifest:
                raise ValueError('redirected preload prerequisite')
            # Retained verifier still pins receipt digest, metadata, model
            # paths and stat tuples; neither wrapper reads model contents.
            models = preload(receipt, manifest)
            boundary()
            return models

        if preload is not None:
            driver.load_preload_models = load_preload
            if 'preload_receipt' in config:
                driver.RETAINED_PRELOAD_RECEIPT = Path(config['preload_receipt'])
        guard.tests_and_enrollment = enrollment
        guard.BIN = Path(config['artifacts']['server'])
        guard.boundary = boundary
        guard.sources = sources
        guard.attempt_root = output_root
        guard._current_guard_bound = True
    return output_root, bind
