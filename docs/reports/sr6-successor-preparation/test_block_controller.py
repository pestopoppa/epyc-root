import tempfile
import unittest
from pathlib import Path
from block_controller import BlockError, execute_block
from native_worker import canonical, capture_request, digest
from server_lifecycle import LifecycleError

class FakeProcess:
    next_pid = 300
    def __init__(self):
        self.pid = FakeProcess.next_pid; FakeProcess.next_pid += 1; self.alive = True
    def poll(self): return None if self.alive else 0
    def terminate(self): self.alive = False
    def wait(self, timeout): return 0
    def kill(self): self.alive = False

class TestBlockController(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.spawns = []; self.posts = []
        prompt = {'id': 'p1', 'rendered': 'hello', 'rendered_sha256': digest(b'hello'), 'seed': 5}
        sampler = {'temperature': 0.3}
        self.kw = dict(output=Path(self.tmp.name), block={'window':'w1', 'block':0,
                       'prompts':[prompt], 'arm_order':['composed3','composed4','mtp3','mtp4','mtp4_repeat']},
                       sampler=sampler, sampler_sha256=digest(canonical(sampler)),
                       admission_check=lambda: True, spawn=self.spawn,
                       verify_ready_and_identity=lambda process, arm: {'server_record_sha256': 'a'*64},
                       post=self.post)
    def spawn(self, arm):
        p = FakeProcess(); self.spawns.append((arm, p)); return p
    def post(self, server, payload):
        self.posts.append((server.arm, payload)); return 200, b'{}'
    def test_runs_five_distinct_servers_and_preserves_matching_requests(self):
        result = execute_block(**self.kw)
        self.assertEqual(result['state'], 'CAPTURED_ONLY'); self.assertEqual(result['attempts'], 5)
        self.assertEqual(len({p.pid for _,p in self.spawns}), 5)
        self.assertTrue(all(not p.alive for _,p in self.spawns))
        self.assertTrue(all(payload == self.posts[0][1] for _, payload in self.posts))
        self.assertTrue((self.kw['output']/'w1-0.block-start.json').exists())
    def test_interrupted_never_replays(self):
        self.kw['post'] = lambda server, payload: (503, b'error')
        with self.assertRaises(BlockError): execute_block(**self.kw)
        self.assertEqual(len(self.spawns), 1)
        with self.assertRaises(BlockError): execute_block(**self.kw)
        self.assertEqual(len(self.spawns), 1)
    def test_existing_attempt_refuses_before_spawn(self):
        capture_request(self.kw['output'], window='other', block=2, arm='mtp3',
                        prompt=self.kw['block']['prompts'][0], sampler={'temperature': 0.3},
                        server_record_sha256='a'*64, post=lambda _: (200, b'ok'))
        with self.assertRaises(BlockError): execute_block(**self.kw)
        self.assertFalse(self.spawns)
    def test_unrelated_exposure_does_not_prevent_fresh_prompt(self):
        prompt = dict(self.kw['block']['prompts'][0], id='other', rendered='different', rendered_sha256=digest(b'different'))
        capture_request(self.kw['output'], window='other', block=2, arm='mtp3',
                        prompt=prompt, sampler={'temperature': 0.3},
                        server_record_sha256='a'*64, post=lambda _: (200, b'ok'))
        self.assertEqual(execute_block(**self.kw)['state'], 'CAPTURED_ONLY')
    def test_same_rendered_prompt_with_new_id_refused(self):
        prompt = dict(self.kw['block']['prompts'][0], id='other')
        capture_request(self.kw['output'], window='other', block=2, arm='mtp3',
                        prompt=prompt, sampler={'temperature': 0.3},
                        server_record_sha256='a'*64, post=lambda _: (200, b'ok'))
        with self.assertRaises(BlockError): execute_block(**self.kw)
        self.assertFalse(self.spawns)
    def test_duplicate_rendered_prompt_in_block_refused(self):
        prompt = dict(self.kw['block']['prompts'][0], id='other', seed=6)
        self.kw['block']['prompts'].append(prompt)
        with self.assertRaises(BlockError): execute_block(**self.kw)
        self.assertFalse(self.spawns)
    def test_invalid_inventory_refuses_before_spawn(self):
        (self.kw['output']/'bad.exposure.json').write_text('{')
        with self.assertRaises(BlockError): execute_block(**self.kw)
        self.assertFalse(self.spawns)
    def test_sampler_mismatch_refuses_before_marker(self):
        self.kw['sampler_sha256'] = 'b'*64
        with self.assertRaises(BlockError): execute_block(**self.kw)
        self.assertFalse(list(self.kw['output'].iterdir()))
    def test_bad_rendered_hash_refuses(self):
        self.kw['block']['prompts'][0]['rendered_sha256'] = 'b'*64
        with self.assertRaises(BlockError): execute_block(**self.kw)
        self.assertFalse(self.spawns)
    def test_admission_refusal_never_spawns_and_burns_block(self):
        self.kw['admission_check'] = lambda: False
        with self.assertRaises(LifecycleError): execute_block(**self.kw)
        self.assertFalse(self.spawns)
        with self.assertRaises(BlockError): execute_block(**self.kw)
    def test_missing_identity_stops_before_request(self):
        self.kw['verify_ready_and_identity'] = lambda process, arm: {'other': 1}
        with self.assertRaises(BlockError): execute_block(**self.kw)
        self.assertEqual(len(self.spawns), 1); self.assertFalse(self.spawns[0][1].alive); self.assertFalse(self.posts)

if __name__ == '__main__': unittest.main()
