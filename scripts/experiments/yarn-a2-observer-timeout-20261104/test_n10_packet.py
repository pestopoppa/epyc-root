import hashlib, importlib.util, json, unittest
from pathlib import Path
P=Path('/mnt/raid0/llm/tmp/yarn/a2-n10-20261104')
spec=importlib.util.spec_from_file_location('a2_n10_runtime',P/'runtime_entry.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)

class N10PacketTest(unittest.TestCase):
 def test_exact_historical_prompt_and_untouched_target(self):
  inp=runtime.load_inputs();self.assertEqual(inp['bad'],[])
  needle=next(n for n in inp['needles'] if n['stage']=='400k' and n['needle']=='N10')
  baseline=next(json.loads(l) for l in (P/'a1-needle-400k.jsonl').read_text().splitlines() if json.loads(l)['id']=='N10')
  messages=runtime.chain_messages(inp['segments'],runtime.stage_chain('400k'),needle['question'])
  self.assertEqual(hashlib.sha256(json.dumps(messages).encode()).hexdigest(),baseline['prompt_sha256'])
  self.assertEqual(needle['expected'],baseline['expected'])
  self.assertEqual(baseline['timings']['prompt_n']+baseline['timings']['cache_n'],399470)
  prior=json.loads((P/'prior-exposure.json').read_text());self.assertEqual(prior['prior_400k_exposures_seen'],0)
  self.assertEqual(sum(e['state']=='exposure_pending' for e in prior['old_qualification_exposures']),1)
 def test_same_one_shot_and_replay_guard(self):
  job=(P/'job_entry.py').read_text();complete=(P/'complete_entry.py').read_text()
  self.assertNotIn('FILLER_SMOKE',job);self.assertNotIn('FILLER_DRYRUN',job)
  self.assertIn("N10 already exposed or attempted; no replay",job)
  self.assertIn("'unit':'A2-N10-400K'",job)
  self.assertIn("one_witness_complete",complete)
if __name__=='__main__':unittest.main()
