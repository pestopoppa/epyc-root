"""BFCL V3 native single-turn bridge and multi-turn replay; scoring stays upstream.

No gold is included in HTTP requests. Multi-turn replay uses official state
and irrelevance checks. Live multi-turn requests and SQL remain unsupported.
"""
import copy
import importlib
import json
import keyword
import uuid
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen

from openai_tool_calls import adapt_openai_tool_calls

UPSTREAM = '70b6a4a2144597b1f99d1f4d3185d35d7ee532a4'
LANGUAGES = {'simple': 'Python', 'multiple': 'Python', 'parallel': 'Python',
             'parallel_multiple': 'Python', 'java': 'Java', 'javascript': 'JavaScript'}
CATEGORIES = frozenset(LANGUAGES)
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
            self.multi = importlib.import_module('bfcl.eval_checker.multi_turn_eval.multi_turn_checker')
            self.execution = importlib.import_module('bfcl.eval_checker.multi_turn_eval.multi_turn_utils')
            self.mapping = importlib.import_module('bfcl.model_handler.constant').GORILLA_TO_OPENAPI
            self.style = importlib.import_module('bfcl.model_handler.model_style').ModelStyle.OpenAI
        finally:
            sys.path.remove(str(package))

    def request(self, case, category, model):
        if category not in CATEGORIES or case['id'].rsplit('_', 1)[0] != category:
            raise ValueError('requires a supported single-turn AST category')
        questions = case['question']
        if len(questions) != 1:
            raise ValueError('multi-turn execution is not implemented by this bridge')
        # Match the official OpenAI FC handler: language values are requested as
        # strings, then interpreted only by the upstream language type converter.
        # Keep the original schema intact for checking and repeat requests.
        functions = self.utils.func_doc_language_specific_pre_processing(
            copy.deepcopy(case['function']), category)
        tools = self.utils.convert_to_tool(functions, self.mapping, self.style)
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
                               copy.deepcopy(gold['ground_truth']), LANGUAGES[category], category,
                               'epyc-native-original-names')
        return {'status': 'scored', 'valid': verdict['valid'], 'official': verdict}


    def score_multi_turn(self, case, category, gold, turns):
        """Replay turn/substep/native completions with official state checks.

        State persists across turns, but fresh namespaces isolate evaluations.
        The pinned checker checks state and irrelevance, not response/order.
        Live multi-turn requests are not constructed by this replay method.
        """
        categories = {'multi_turn_base', 'multi_turn_composite',
                      'multi_turn_long_context', 'multi_turn_miss_func',
                      'multi_turn_miss_param'}
        if category not in categories or case['id'].rsplit('_', 1)[0] != category:
            raise ValueError('requires a supported multi-turn category')
        if gold['id'] != case['id']:
            raise ValueError('case/gold ID mismatch')
        if len(gold['ground_truth']) != len(case['question']):
            raise ValueError('case/gold turn count mismatch')
        if not isinstance(turns, list) or len(turns) != len(case['question']):
            return {'status': 'parse_error', 'valid': None, 'error': 'turn count mismatch'}
        allowed = set()
        for class_name in case['involved_classes']:
            module = importlib.import_module(self.execution.CLASS_FILE_PATH_MAPPING[class_name])
            cls = getattr(module, class_name)
            allowed.update(name for name in dir(cls)
                           if not name.startswith('_') and callable(getattr(cls, name)))
        decoded = []
        for turn in turns:
            if not isinstance(turn, list):
                return {'status': 'parse_error', 'valid': None, 'error': 'turn must be a substep list'}
            steps = []
            for raw in turn:
                choices = raw.get('choices') if isinstance(raw, dict) else None
                if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                    return {'status': 'parse_error', 'valid': None, 'error': 'expected exactly one choice'}
                choice = choices[0]
                message = choice.get('message')
                if (choice.get('finish_reason') == 'stop' and isinstance(message, dict)
                        and message.get('tool_calls') in (None, [])):
                    continue
                parsed = adapt_openai_tool_calls(choice)
                if not parsed.ok:
                    return {'status': 'parse_error', 'valid': None, 'error': parsed.error}
                for call in parsed.calls:
                    for name, args in call.items():
                        # Official conversion interpolates names/keys into eval.
                        if name not in allowed or name == 'xargs' or any(not key.isidentifier() or keyword.iskeyword(key) for key in args):
                            return {'status': 'parse_error', 'valid': None, 'error': 'unsupported method or invalid keyword'}
                steps.append(self.utils.convert_to_function_call([
                    {name: json.dumps(args, allow_nan=False)}
                    for call in parsed.calls for name, args in call.items()]))
            decoded.append(steps)
        namespace = 'epyc_replay_' + uuid.uuid4().hex
        try:
            state = self.multi.multi_turn_checker(
                decoded, copy.deepcopy(gold['ground_truth']), copy.deepcopy(case), category, namespace)
            irrelevance = (self.multi.multi_turn_irrelevance_checker(decoded, gold['ground_truth'])
                           if category in {'multi_turn_miss_func', 'multi_turn_miss_param'}
                           else {'valid': True})
            return {'status': 'scored', 'valid': state['valid'] and irrelevance['valid'],
                    'official': {'state': state, 'irrelevance': irrelevance}}
        finally:
            for name in list(vars(self.execution)):
                if name.startswith(namespace + '_'):
                    delattr(self.execution, name)


def capture(endpoint, payload, timeout=60):
    """POST an input-only request; let transport errors remain infrastructure errors."""
    request = Request(endpoint, data=json.dumps(payload, allow_nan=False).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())
