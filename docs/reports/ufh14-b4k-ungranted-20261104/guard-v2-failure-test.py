"""Exact guard-v2 job run() failure/history test; backend boundary is fake, no networking."""
import importlib.util, json, socket, sys, tempfile, types, urllib.request
from pathlib import Path
JOB = Path('/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/b4k-guard-v2-20261104/job.py')
EXPECTED_SHA = '8b1d8c2ff844e2aa1e011bd198c894675015e5b75aabdcb724c0042acc113b61'
import hashlib
source_sha = hashlib.sha256(JOB.read_bytes()).hexdigest()
assert source_sha == EXPECTED_SHA, source_sha
prompts=[]; stop_path=None
# These guards make any accidental network attempt a hard test failure.
def forbidden(*a, **kw): raise AssertionError('network boundary called')
socket.socket = forbidden
urllib.request.urlopen = forbidden
backends = types.ModuleType('src.backends')
backends.serving_calls = types.SimpleNamespace(stage_caller=lambda **kw: None)
llama = types.ModuleType('src.backends.llama_server')
class Backend:
    def __init__(self, config): pass
    def infer_stream_text(self, role, req, on_chunk):
        prompts.append(req.prompt)
        if len(prompts) == 2: stop_path.unlink(missing_ok=True)
        return types.SimpleNamespace(success=False, output='SHOULD_NOT_ENTER_HISTORY', error='fake-error',
            prompt_tokens=5, cached_prompt_tokens=0, tokens_generated=0, reasoning_content='',
            failure_reason='fake-failure-reason', completion_reason='error')
llama.LlamaServerBackend=Backend; llama.ServerConfig=lambda **kw: kw
model=types.ModuleType('src.model_server'); model.InferenceRequest=lambda **kw: types.SimpleNamespace(**kw)
registry=types.ModuleType('src.registry_loader')
registry.RegistryLoader=lambda **kw: types.SimpleNamespace(get_role=lambda role: role)
sys.modules.update({'src.backends':backends,'src.backends.llama_server':llama,
                    'src.model_server':model,'src.registry_loader':registry})
spec=importlib.util.spec_from_file_location('guard_v2_job_under_test',JOB)
job=importlib.util.module_from_spec(spec); spec.loader.exec_module(job)
with tempfile.TemporaryDirectory(prefix='guard-v2-failure-history-') as td:
    run_dir=Path(td); stop_path=run_dir/'STOP'; stop_path.write_text('release after two warm failures')
    job.D=run_dir
    result=job.run(run_dir)
    rows=[json.loads(line) for line in (run_dir/'calls.jsonl').read_text().splitlines()]
    err_rows=[json.loads(line) for line in (run_dir/'errors.log').read_text().splitlines()]
    assert result == 0, result
    assert len(rows)>2 and all(not row['ok'] for row in rows), len(rows)
    assert all(row['error']=='fake-error' and row['failure_reason']=='fake-failure-reason' for row in rows)
    assert len(err_rows)==len(rows), (len(err_rows),len(rows))
    assert all('SHOULD_NOT_ENTER_HISTORY' not in prompt for prompt in prompts)
    assert len(prompts)==len(rows)
print(json.dumps({'result':'PASS','source_sha256':source_sha,'fake_backend_calls':len(rows),
                  'error_rows':len(err_rows),'failed_outputs_in_history':False,'network_calls':0,
                  'entrypoint_check_server_called':False}))
