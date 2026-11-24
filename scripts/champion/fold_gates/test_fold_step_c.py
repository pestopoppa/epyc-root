#!/usr/bin/env python3
"""Selftest for the STEP C canonical block (fold_step_c.py / step_c_block.txt). No compute, no servers: the block is exec'd in a
namespace with stubbed host-job globals and fed synthetic spec/nospec token streams and teacher-forced probes.
Run: python3 -I scripts/champion/fold_gates/test_fold_step_c.py   (also unittest-discoverable)."""
import hashlib, json, os, re, shutil, signal, subprocess, sys, tempfile, threading, time, unittest, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fold_step_c as F  # noqa: E402


def make_ns(tmp):
    ns = {'hashlib': hashlib, 'json': json, 'os': os, 're': re, 'shutil': shutil, 'subprocess': subprocess, 'sys': sys,
          'threading': threading, 'time': time, 'urllib': urllib,
          '__name__': 'stepc_host', 'D': tmp, 'OUT': tmp, 'PORT': 1, 'SHORT': tmp + '/short', 'N_PREDICT': 256,
          'EXPECT_N': {'P2': 14089, 'P3': 25425}, 'gp': None, 'ARMS': {'c18': {'bdir': '/x18'}, 'c19': {'bdir': '/x19'}}}
    store = {}
    ns['_store'] = store
    ns['append'] = lambda u: store.__setitem__(u['unit_id'], u)
    ns['done'] = lambda: dict(store)
    ns['stop'] = lambda: False
    ns['jsave'] = lambda p, o: (os.makedirs(os.path.dirname(p), exist_ok=True), json.dump(o, open(p, 'w')))
    ns['post'] = lambda *a, **k: {}
    ns['residency'] = lambda *a, **k: {'ok': True}
    ns['gpu_env'] = lambda s: {}
    ns['xserver_argv'] = lambda s, spec: ['srv']
    ns['acc_summary'] = lambda qs: {'n': len(qs)}

    def median(xs):
        xs = sorted(xs)
        n = len(xs)
        return None if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)
    ns['median'] = median

    def prefix(a, b):
        n = min(len(a), len(b)); i = 0
        while i < n and a[i] == b[i]:
            i += 1
        return i
    ns['prefix'] = prefix
    old = signal.getsignal(signal.SIGTERM)
    exec(compile(F.block_source(), 'step_c_block.txt', 'exec'), ns)
    signal.signal(signal.SIGTERM, old)
    return ns


class StepC(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.ns = make_ns(self.t.name)
        self.g = type('G', (), {})()

    def tearDown(self):
        self.t.cleanup()

    def mk(self, cfg, rep, toks):
        ns = self.ns
        uid = ns['cuid']('c', rep, cfg); f = self.t.name + f'/content/{uid}.json'
        ns['jsave'](f, {'content': ''.join(chr(65 + (x % 26)) for x in toks), 'tokens': toks})
        return {'unit_id': uid, 'kind': 'cvisit', 'prefix': 'c', 'valid': True, 'cfg': cfg, 'arm': ns['CCFG'][cfg][0], 'rep': rep,
                'content_file': f, 'q': {'draft_n': 10, 'draft_n_accepted': 9, 'predicted_n': 256, 'tok_s': 1.0},
                'witness': {'gdn_fused_lines': 0, 'device_accept_enabled_line': True}}

    def test_constants_and_order(self):
        ns = self.ns
        self.assertEqual((ns['NEAR_TIE_NAT'], ns['R_CORE']), (0.05, 6))
        cu = ns['core_units']('c')
        self.assertEqual(len(cu), 24)
        self.assertEqual([c for _, r, c in cu if r == 1], ns['CORDER'])
        self.assertEqual([c for _, r, c in cu if r == 2], ns['CORDER'][::-1])
        self.assertTrue(all(sum(1 for _, _, c in cu if c == cfg) == 6 for cfg in ns['CORDER']))
        self.assertEqual(ns['p10'](list(range(1, 16))), 2)
        self.assertEqual(ns['first_div']([1, 2, 3], [1, 2, 4]), (2, 2))
        self.assertEqual(ns['first_div']([1, 2], [1, 2, 9]), (None, 2))

    def test_gated_requests_use_served_path(self):
        # gated request n_probs 0 (default); probes n_probs 2
        import inspect
        ns = self.ns
        self.assertEqual(inspect.signature(ns['gen']).parameters['n_probs'].default, 0)
        src = inspect.getsource(ns['cvisit']) + inspect.getsource(ns['probe_session'])
        self.assertIn('gen(sv.base, texts[pid])', src)
        self.assertIn('n_predict=1, n_probs=2', src)

    def test_rule_c(self):
        ns, mk = self.ns, self.mk
        base = list(range(100, 356))
        d = {}
        for r in range(1, 7):
            d[ns['cuid']('c', r, 'c19-nospec')] = mk('c19-nospec', r, base)
            d[ns['cuid']('c', r, 'c18-nospec')] = mk('c18-nospec', r, base)
            d[ns['cuid']('c', r, 'c19-spec')] = mk('c19-spec', r, base[:5] + [7] + base[6:])
            d[ns['cuid']('c', r, 'c18-spec')] = mk('c18-spec', r, base[:3] + [8] + base[4:])
        w = ns['need_probes'](d, 'c', ['c19', 'c18'])
        self.assertEqual((len(w['c19']), len(w['c18'])), (1, 1))
        self.assertEqual(list(w['c19'].values())[0], base[:5])
        self.assertEqual(ns['correctness'](d, 'c', True)['verdict'], 'FUTILITY_MARGIN_UNMEASURED')
        k19 = ns['ctx_key']('P3', base[:5])
        d[f'probe-c19-{k19}'] = {'top': [{'id': base[5], 'logprob': -0.70}, {'id': 7, 'logprob': -0.72}]}
        d[f'probe-c18-{ns["ctx_key"]("P3", base[:3])}'] = {'top': [{'id': base[3], 'logprob': -1.0}, {'id': 8, 'logprob': -1.01}]}
        c = ns['correctness'](d, 'c', True)
        self.assertEqual(c['verdict'], 'PASS_NEAR_TIE')
        self.assertEqual(c['fork_classes']['x_c19']['NEAR_TIE'], 36)
        self.assertEqual((c['stats_token_pos']['aa_c19']['n'], c['stats_token_pos']['x_c19']['n']), (15, 36))
        # clause ii: x_ref forks later than x_cand (and aa_cand never forks) -> REAL_DEFECT without any HARD fork
        for r in range(1, 7):
            d[ns['cuid']('c', r, 'c18-spec')] = mk('c18-spec', r, base[:7] + [8] + base[8:])
        c = ns['correctness'](d, 'c', True)
        self.assertTrue(c['clause_ii']['fires'])
        self.assertEqual(c['verdict'], 'REAL_DEFECT')
        for r in range(1, 7):
            d[ns['cuid']('c', r, 'c18-spec')] = mk('c18-spec', r, base[:3] + [8] + base[4:])
        self.assertEqual(ns['correctness'](d, 'c', True)['verdict'], 'PASS_NEAR_TIE')
        # margin >= 0.05 -> HARD; repeats in 6 spec reps -> stops at an interim look
        d[f'probe-c19-{k19}'] = {'top': [{'id': base[5], 'logprob': -0.10}, {'id': 7, 'logprob': -2.0}]}
        c = ns['correctness'](d, 'c', False)
        self.assertEqual((c['verdict'], len(c['hard_spec_reps'])), ('REAL_DEFECT', 6))
        self.assertEqual(ns['correctness'](d, 'c', True)['verdict'], 'REAL_DEFECT')
        # tiny margin but the alternative is not the probe's second token -> HARD
        d[f'probe-c19-{k19}'] = {'top': [{'id': base[5], 'logprob': -0.70}, {'id': 99, 'logprob': -0.71}]}
        self.assertEqual(ns['correctness'](d, 'c', True)['verdict'], 'REAL_DEFECT')
        # a single HARD rep is judged only at the final look (interim: no answer)
        d2 = dict(d)
        d[f'probe-c19-{k19}'] = {'top': [{'id': base[5], 'logprob': -0.70}, {'id': 7, 'logprob': -0.72}]}
        for r in range(2, 7):
            d[ns['cuid']('c', r, 'c19-spec')] = mk('c19-spec', r, base)
        d[ns['cuid']('c', 1, 'c19-spec')] = mk('c19-spec', 1, base[:5] + [7] + base[6:])
        self.assertIsNone(ns['correctness'](d, 'c', False)['verdict'])
        del d2


class Splice(unittest.TestCase):
    def test_splice_check(self):
        r4 = '/mnt/raid0/llm/tmp/c21-fold-gpu-20261124-r4/job.py'
        if os.path.exists(r4):
            s = open(r4).read()
        else:  # synthetic job with the r3 heading
            s = ('"""job"""\nx=1\n' + F.R3_HEAD + '\nOLD = 1\n\ndef server27_argv(store):\n    return []\n\n# synthetic STEP C\n')
        o = F.splice(s)
        ok, why = F.check(o)
        self.assertTrue(ok, why)
        self.assertEqual(F.splice(o), o)                          # idempotent
        self.assertFalse(F.check(o.replace('NEAR_TIE_NAT = 0.05', 'NEAR_TIE_NAT = 0.5'))[0])   # drifted block is caught
        with self.assertRaises(ValueError):
            F.splice('def step4(d):\n    pass\n')                # old step-4 job: no mechanical splice

    def test_retired_clause_flagged(self):
        s = F.splice('x\n' + F.R3_HEAD + '\n\ndef server27_argv(s):\n    pass\n# synthetic STEP C\n')
        self.assertTrue(F.check(s)[0])
        self.assertFalse(F.check(s + '\n        agree[arm] = min(pl)\n')[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
