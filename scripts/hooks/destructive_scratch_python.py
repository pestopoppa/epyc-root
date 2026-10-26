"""Project Python syntax into actual delete calls; constants/comments are data.

This is static, bounded inspection, never execution. Unknown dynamic code keeps
the parent scanner's fail-open policy. There is no language-wide exemption.
"""
from __future__ import annotations

import ast
import os
import shlex


def scan_python(text, roots, origin, scan_shell, depth=0):
    if depth >= 8:
        return None
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    names = {}
    values = {}

    def qualified(node):
        if isinstance(node, ast.Name):
            return names.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return qualified(node.value) + "." + node.attr
        return ""

    def literal(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            return values.get(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            a, b = literal(node.left), literal(node.right)
            return a + b if a is not None and b is not None else a
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            a, b = literal(node.left), literal(node.right)
            return os.path.join(a, b) if a is not None and b is not None else a
        if isinstance(node, ast.JoinedStr):
            parts = []
            for part in node.values:
                value = literal(part.value) if isinstance(part, ast.FormattedValue) else literal(part)
                if value is None:
                    break
                parts.append(value)
            return "".join(parts) or None
        if isinstance(node, ast.Call):
            name = qualified(node.func)
            if name in ("pathlib.Path", "Path") and node.args:
                return literal(node.args[0])
            if name == "os.path.join":
                args = [literal(x) for x in node.args]
                prefix = []
                for arg in args:
                    if arg is None:
                        break
                    prefix.append(arg)
                if prefix:
                    return os.path.join(*prefix)
            if isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath":
                base = literal(node.func.value)
                args = [literal(x) for x in node.args]
                if base is not None and all(x is not None for x in args):
                    return os.path.join(base, *args)
        return None

    def protected(value):
        if value is None or not os.path.isabs(value):
            return None
        path = os.path.realpath(value)
        for root in roots:
            if path == root or path.startswith(root + "/"):
                return root
        return None

    def visit(node):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and node.value is not None:
                    values[target.id] = literal(node.value)
                    value_name = qualified(node.value)
                    if value_name:
                        names[target.id] = value_name
                    else:
                        names.pop(target.id, None)
        if isinstance(node, ast.Call):
            name = qualified(node.func)
            argument = None
            if name in ("shutil.rmtree", "rmtree", "os.unlink", "os.remove", "os.rmdir", "os.removedirs"):
                argument = node.args[0] if node.args else next(
                    (kw.value for kw in node.keywords if kw.arg in ("path", "filename")), None)
            elif isinstance(node.func, ast.Attribute) and node.func.attr in ("unlink", "rmdir"):
                argument = node.func.value
            root = protected(literal(argument))
            if root:
                return f"{origin} invokes {name} on a target under protected root {root}"
            if name in ("os.system", "os.popen", "subprocess.run", "subprocess.call",
                        "subprocess.check_call", "subprocess.check_output", "subprocess.Popen") and node.args:
                first = node.args[0]
                command = literal(first)
                if isinstance(first, (ast.List, ast.Tuple)):
                    argv = [literal(x) for x in first.elts]
                    command = shlex.join(argv) if all(x is not None for x in argv) else None
                if command is not None:
                    reason = scan_shell(command)
                    if reason:
                        return reason
            # Constant dynamic-code invocations are executable, unlike JSON data.
            if name in ("exec", "eval") and node.args:
                code = literal(node.args[0])
                if code is not None and code != text:
                    reason = scan_python(code, roots, origin, scan_shell, depth + 1)
                    if reason:
                        return reason
        for child in ast.iter_child_nodes(node):
            reason = visit(child)
            if reason:
                return reason
        return None

    return visit(tree)
