"""Single-turn Python BFCL V3 native-call bridge; scoring stays upstream.

No gold is included in HTTP requests. Multi-turn, Java, JS and SQL require their
own upstream execution paths and are rejected here, never assigned a score.
"""
import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen

from openai_tool_calls import adapt_openai_tool_calls

UPSTREAM = '70b6a4a2144597b1f99d1f4d3185d35d7ee532a4'
CATEGORIES = frozenset({'simple', 'multiple', 'parallel', 'parallel_multiple'})
PACKAGE = 'berkeley-function-call-leaderboard'


class OfficialV3:
    """Load the unmodified official package from a commit-pinned worktree."""

    def __init__(self, checkout):
        checkout = Path(checkout).resolve()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(checkout), *args], text=True).strip()
        if git('rev-parse', 'HEAD') != UPSTREAM:
            raise ValueError('BFCL source commit mismatch')
        if git('status', '--porcelain', '--untracked-files=all', '--', f'{PACKAGE}/bfcl'):
            raise ValueError('BFCL package has local changes')
        package = checkout / PACKAGE
        # Refuse a previously imported package from another source tree.
        for name, module in list(sys.modules.items()):
            if name == 'bfcl' or name.startswith('bfcl.'):
                origin = getattr(module, '__file__', None)
                if origin and not Path(origin).resolve().is_relative_to(package):
                    raise ValueError('another BFCL package is already imported')
        sys.path.insert(0, str(package))
        try:
            self.utils = importlib.import_module('bfcl.model_handler.utils')
            self.checker = importlib.import_module('bfcl.eval_checker.ast_eval.ast_checker').ast_checker
            self.mapping = importlib.import_module('bfcl.model_handler.constant').GORILLA_TO_OPENAPI
            self.style = importlib.import_module('bfcl.model_handler.model_style').ModelStyle.OpenAI
        finally:
            sys.path.remove(str(package))

    def request(self, case, category, model):
        if category not in CATEGORIES or case['id'].rsplit('_', 1)[0] != category:
            raise ValueError('requires a single-turn Python AST category')
        questions = case['question']
        if len(questions) != 1:
            raise ValueError('multi-turn execution is not implemented by this bridge')
        tools = self.utils.convert_to_tool(case['function'], self.mapping, self.style)
        reverse = {}
        for original, tool in zip(case['function'], tools, strict=True):
            wire_name = tool['function']['name']
            if wire_name in reverse:
                raise ValueError('function name collision after official conversion')
            reverse[wire_name] = original['name']
        return {'model': model, 'messages': copy.deepcopy(questions[0]),
                'tools': tools, 'tool_choice': 'auto', 'temperature': 0,
                'seed': 20261031, 'max_tokens': 4096, 'stream': False}, reverse

    def score(self, case, category, gold, completion, model):
        _, reverse = self.request(case, category, model)
        if gold['id'] != case['id']:
            raise ValueError('case/gold ID mismatch')
        choices = completion.get('choices') if isinstance(completion, dict) else None
        if not isinstance(choices, list) or len(choices) != 1:
            return {'status': 'parse_error', 'valid': None, 'error': 'expected exactly one choice'}
        parsed = adapt_openai_tool_calls(choices[0])
        if not parsed.ok:
            return {'status': 'parse_error', 'valid': None, 'error': parsed.error}
        # Reverse only declared exact wire names. Never replace all underscores,
        # coerce argument types, reorder calls or repair unknown function names.
        calls = [{reverse.get(name, name): args} for call in parsed.calls for name, args in call.items()]
        verdict = self.checker(copy.deepcopy(case['function']), calls,
                               copy.deepcopy(gold['ground_truth']), 'Python', category,
                               'epyc-native-original-names')
        return {'status': 'scored', 'valid': verdict['valid'], 'official': verdict}


def capture(endpoint, payload, timeout=60):
    """POST an input-only request; let transport errors remain infrastructure errors."""
    request = Request(endpoint, data=json.dumps(payload, allow_nan=False).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())
