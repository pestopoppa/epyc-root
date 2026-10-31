#!/usr/bin/env python3
"""Compare a candidate template against retained CT-12.4 rendered prompts."""
import argparse
import json
from pathlib import Path
import sys
import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('template', nargs='?', type=Path, default=HERE / 'chat_template.jinja')
args = parser.parse_args()
env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
env.filters['tojson'] = lambda x, indent=None, ensure_ascii=False: json.dumps(x, ensure_ascii=ensure_ascii, indent=indent)
def raise_exception(message):
    raise jinja2.exceptions.TemplateError(message)
env.globals['raise_exception'] = raise_exception
template = env.from_string(args.template.read_text(encoding='utf-8'))
fixtures = json.loads((HERE / 'ct12-4-goldens.json').read_text(encoding='utf-8'))['cases']
failed = []
for case in fixtures:
    request = case['request']
    # /apply-template consumes top-level reasoning_effort; only kwargs reach Jinja.
    actual = template.render(messages=request['messages'], add_generation_prompt=True,
                             bos_token='', eos_token='<|endoftext|>',
                             **request.get('chat_template_kwargs', {}))
    if actual.encode('utf-8') != case['expected_prompt'].encode('utf-8'):
        failed.append(case['id'])
        print('FAIL', case['id'])
    else:
        print('PASS', case['id'])
print(f'{len(fixtures)-len(failed)}/{len(fixtures)} matched')
sys.exit(bool(failed))
