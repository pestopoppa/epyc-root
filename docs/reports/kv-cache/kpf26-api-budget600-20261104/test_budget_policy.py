import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

D = Path(__file__).parent

class BudgetPolicyTests(unittest.TestCase):
    def invoke(self, root, native_cap=180.0, fraction=0.4):
        scout = types.SimpleNamespace(PER_CALL_TIMEOUT_S=native_cap, REQUEST_BUDGET_FRACTION=fraction)
        limits = types.ModuleType('src.backends.context_limits')
        limits.ContextLimitResolver = Mock()
        limits.set_context_limit_resolver = Mock()
        package = types.ModuleType('src.api.routes.chat_pipeline'); package.scout_stage = scout
        uvicorn = types.ModuleType('uvicorn'); uvicorn.run = Mock()
        env = {'PRIVATE_PORT':'18976','PRIVATE_API':'18076','KPF26_POLICY_OUTPUT':str(root/'policy.json')}
        with patch.dict(sys.modules, {'src.backends.context_limits':limits,'src.api.routes.chat_pipeline':package,'uvicorn':uvicorn}), patch.dict(os.environ, env):
            runpy.run_path(str(D/'private_api.py'), run_name='__main__')
        return scout, uvicorn

    def test_private_policy_changes_only_cap_and_records_effective_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); scout, uvicorn = self.invoke(root)
            self.assertEqual(scout.PER_CALL_TIMEOUT_S, 600.0)
            self.assertEqual(scout.REQUEST_BUDGET_FRACTION, 0.4)
            policy = json.loads((root/'policy.json').read_text())
            self.assertEqual(policy['api_request_timeout_s'], 1800.0)
            self.assertEqual(min(policy['configured_scout_budget_s'],policy['request_budget_fraction']*policy['api_request_timeout_s']),600.0)
            self.assertIn('actual effective',policy['scope'])
            uvicorn.run.assert_called_once_with('src.api:app',host='127.0.0.1',port=18076)

    def test_changed_native_fraction_refuses_before_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(AssertionError): self.invoke(Path(tmp),fraction=0.5)
            self.assertFalse((Path(tmp)/'policy.json').exists())

    def test_rebind_changes_timeout_but_preserves_fixed_scorer(self):
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); packet = root/'packet';packet.mkdir()
            req = {'scope_root':'old','spec':{'budget_s':600}}; api={'task_root':'old','timeout_s':600,'scouts':{'budget_s':600}}
            (packet/'request.json').write_text(json.dumps(req));(packet/'api.json').write_text(json.dumps(api));(packet/'expected.json').write_text('{"fixed":"scorer"}')
            raw=(packet/'expected.json').read_bytes()
            m={'tasks':[{'request':{'path':'request.json'}}],'api_request':{'path':'api.json'},'provenance':{},'arm_timeout_s':900}
            (packet/'manifest.json').write_text(json.dumps(m))
            with patch.object(sys,'argv',['rebind_packet',str(packet),'18976']):runpy.run_path(str(D/'rebind_packet.py'),run_name='__main__')
            final=json.loads((packet/'api.json').read_text());self.assertEqual(final['timeout_s'],1800);self.assertEqual(final['scouts']['budget_s'],600)
            self.assertEqual((packet/'expected.json').read_bytes(),raw)
            manifest=json.loads((packet/'manifest.json').read_text());self.assertEqual(manifest['api_request']['sha256'],hashlib.sha256((packet/'api.json').read_bytes()).hexdigest())

if __name__ == '__main__': unittest.main()
