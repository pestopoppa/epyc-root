"""Exercise the unapplied API patch against the pinned APP checkout."""
import importlib.util
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

APP = Path('/mnt/raid0/llm/epyc-orchestrator')
HERE = Path(__file__).parent
sys.path.insert(0, str(APP / 'tests/unit'))
from test_repl_executor import basic_request, basic_routing, mock_primitives, mock_state
from src.api.routes.chat_utils import RoutingResult
from src.graph.state import TaskResult
from src.roles import Role


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    import subprocess
    for name in ('src/api/models/requests.py', 'src/api/routes/chat_pipeline/repl_executor.py'):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((APP / name).read_bytes())
    subprocess.run(['patch', '-s', '-p1', '-d', str(tmp_path), '-i', str(HERE / 'request-optin.patch')], check=True)
    requests = load('document_search_requests_candidate', tmp_path / 'src/api/models/requests.py')
    executor = load('document_search_executor_candidate', tmp_path / 'src/api/routes/chat_pipeline/repl_executor.py')
    monkeypatch.setitem(sys.modules, 'src.api.routes.chat_pipeline.repl_executor', executor)
    return requests, executor


def test_opt_in_requires_repl_and_rejects_bundle(candidate):
    request, _ = candidate
    assert request.ChatRequest(prompt='hi').document_search is False
    with pytest.raises(ValidationError, match='requires force_mode'):
        request.ChatRequest(prompt='hi', document_search=True)
    with pytest.raises(ValidationError, match='cannot be combined'):
        request.ChatRequest(prompt='hi', document_search=True, force_mode='repl', context_bundle={})
    assert request.ChatRequest(prompt='hi', document_search=True, force_mode='repl').document_search


@pytest.mark.asyncio
async def test_absent_document_fails_closed(candidate, basic_routing, mock_primitives, mock_state):
    request, executor = candidate
    with pytest.raises(HTTPException) as exc:
        await executor._execute_repl_body(request.ChatRequest(prompt='hi', document_search=True, force_mode='repl'), basic_routing, mock_primitives, mock_state, time.perf_counter(), Role.WORKER_GENERAL, None)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize('enabled', [False, True])
async def test_request_opt_in_reaches_document_repl(candidate, mock_primitives, mock_state, enabled):
    request, executor = candidate
    doc = MagicMock()
    doc.document_result.to_searchable_text.return_value = 'Searchable text'
    doc.injection_flags = None
    routing = RoutingResult(task_id='test', task_ir={}, use_mock=False, routing_strategy='document', formalization_applied=False, document_result=doc)
    req = request.ChatRequest(prompt='hi', force_mode='repl', document_search=enabled)
    with patch('src.repl_document.DocumentREPLEnvironment') as repl_class, patch('src.repl_document.DocumentContext') as context_class, patch.object(executor, 'run_task', return_value=TaskResult(answer='ok', success=True, turns=1, role_history=['worker_general'])):
        context_class.from_document_result.return_value.sections = []
        context_class.from_document_result.return_value.figures = []
        repl_class.return_value.artifacts = {}
        repl_class.return_value._tool_invocations = 0
        repl_class.return_value.tool_registry = None
        await executor._execute_repl(req, routing, mock_primitives, mock_state, time.perf_counter(), Role.WORKER_GENERAL)
        assert repl_class.call_args.kwargs['document_search_enabled'] is enabled
