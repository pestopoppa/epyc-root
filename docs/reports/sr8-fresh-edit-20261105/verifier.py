#!/usr/bin/env python3
"""Strict, side-effect-free semantic checker for the SR-8 synthetic edit fixture.

It interprets a small arithmetic-only AST subset. Generated Python is never executed.
Unsupported but otherwise valid Python yields UNKNOWN, never PASS.
"""
import ast
import operator
import re

class Unsupported(Exception):
    pass

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.FloorDiv: operator.floordiv, ast.Div: operator.truediv}


def verify(task, content):
    try:
        if not isinstance(content, str):
            raise Unsupported('non-text response')
        matches = list(re.finditer(r'<<<FILE:\s*([^>\n]+?)>>>\s*\n(.*?)\n<<<END>>>', content, re.S))
        if not matches:
            return {'status': 'FAIL', 'reason': 'no file envelopes'}
        # Only whitespace may appear outside the specified envelopes.
        remainder = re.sub(r'<<<FILE:\s*([^>\n]+?)>>>\s*\n(.*?)\n<<<END>>>', '', content, flags=re.S)
        names = [m.group(1).strip() for m in matches]
        if remainder.strip() or len(names) != len(set(names)) or set(names) != set(task['expected_files']):
            return {'status': 'FAIL', 'reason': 'unexpected, duplicate, missing, or extra envelope content'}
        modules = {}
        for match in matches:
            name = match.group(1).strip()
            if '/' in name or not name.endswith('.py'):
                raise Unsupported('unsafe path')
            tree = ast.parse(match.group(2), filename=name)
            functions, imports = {}, {}
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    a = node.args
                    if (node.decorator_list or node.returns or a.posonlyargs or a.kwonlyargs or a.vararg or a.kwarg or a.defaults or a.kw_defaults or len(node.body) != 1 or not isinstance(node.body[0], ast.Return) or node.name in functions):
                        raise Unsupported('unsupported function shape')
                    functions[node.name] = node
                elif isinstance(node, ast.ImportFrom):
                    if node.level or node.module not in {p[:-3] for p in task['expected_files']}:
                        raise Unsupported('external import')
                    for alias in node.names:
                        if alias.name == '*' or (alias.asname or alias.name) in imports:
                            raise Unsupported('wildcard or duplicate import')
                        imports[alias.asname or alias.name] = (node.module, alias.name)
                else:
                    raise Unsupported('unsupported top-level statement')
            modules[name[:-3]] = (functions, imports)

        def call(module, name, args, depth=0):
            if depth > 12 or module not in modules:
                raise Unsupported('invalid call depth or module')
            funcs, imports = modules[module]
            if name not in funcs:
                if name not in imports:
                    raise Unsupported('missing function')
                target_module, target_name = imports[name]
                return call(target_module, target_name, args, depth + 1)
            f = funcs[name]
            if len(args) != len(f.args.args):
                raise Unsupported('argument mismatch')
            env = dict(zip((a.arg for a in f.args.args), args))
            def expr(node):
                if isinstance(node, ast.Constant) and type(node.value) in (int, float) and abs(node.value) < 10**9:
                    return node.value
                if isinstance(node, ast.Name) and node.id in env:
                    return env[node.id]
                if isinstance(node, ast.BinOp) and type(node.op) in OPS:
                    return OPS[type(node.op)](expr(node.left), expr(node.right))
                if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
                    v = expr(node.operand)
                    return -v if isinstance(node.op, ast.USub) else v
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
                    return call(module, node.func.id, [expr(a) for a in node.args], depth + 1)
                raise Unsupported('unsupported expression')
            return expr(f.body[0].value)
        for check in task['checks']:
            actual = call(check['module'], check['function'], check['args'])
            if actual != check['expected']:
                return {'status': 'FAIL', 'reason': 'semantic mismatch', 'check': check, 'actual': actual}
        return {'status': 'PASS', 'reason': 'all sealed semantic checks passed'}
    except (Unsupported, SyntaxError, ValueError, ZeroDivisionError, OverflowError, RecursionError, KeyError, TypeError) as exc:
        return {'status': 'UNKNOWN', 'reason': str(exc)}
