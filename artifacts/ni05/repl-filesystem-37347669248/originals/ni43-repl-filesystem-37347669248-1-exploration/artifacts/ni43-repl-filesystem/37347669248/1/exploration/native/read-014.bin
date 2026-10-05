"""AST-based security validation for the REPL sandbox."""

from __future__ import annotations

import ast
import re

#: A ``str.format`` replacement field whose field name reaches a dunder, e.g.
#: ``{0.get.__closure__[0]}``: format-string field access is attribute access that no
#: ast.Attribute node ever shows.
_DUNDER_FORMAT_FIELD = re.compile(r"\{[^{}]*__[^{}]*\}")


class ASTSecurityVisitor(ast.NodeVisitor):
    """AST visitor that checks for dangerous code patterns.

    This is more robust than regex because it analyzes the parsed syntax tree,
    making it immune to string concatenation tricks like:
        getattr(__builtins__, '__im' + 'port__')('os')
    """

    # Forbidden module imports
    FORBIDDEN_MODULES = frozenset(
        {
            "os",
            "sys",
            "subprocess",
            "socket",
            "shutil",
            "pathlib",
            "tempfile",
            "multiprocessing",
            "threading",
            "ctypes",
            "pickle",
            "importlib",
            "builtins",
            "code",
            "codeop",
            "runpy",
            "pkgutil",
        }
    )

    # Forbidden built-in function calls
    FORBIDDEN_CALLS = frozenset(
        {
            "__import__",
            "eval",
            "exec",
            "compile",
            "open",
            "getattr",
            "setattr",
            "delattr",
            "hasattr",
            "globals",
            "locals",
            "vars",
            "dir",
            "input",
            "breakpoint",
            "memoryview",
        }
    )

    # Forbidden attribute accesses (dunder attributes for escaping sandbox)
    FORBIDDEN_ATTRS = frozenset(
        {
            "__class__",
            "__bases__",
            "__subclasses__",
            "__mro__",
            "__dict__",
            "__globals__",
            "__locals__",
            "__code__",
            "__builtins__",
            "__closure__",
            "__func__",
            "__self__",
            "__module__",
            "__qualname__",
            "__annotations__",
            "__reduce__",
            "__reduce_ex__",
            "__getstate__",
            "__setstate__",
            # Non-dunder introspection that walks from a function or generator to
            # live objects: closure cells (``fn.__closure__[0].cell_contents``) and
            # frames (``gen.gi_frame.f_globals``, ``tb.tb_frame.f_back.f_locals``).
            "cell_contents",
            "f_globals",
            "f_back",
            "f_locals",
            "gi_frame",
            "tb_frame",
            "cr_frame",
        }
    )

    # Attribute getters by NAME STRING: ``operator.attrgetter('get.__closure__')(x)``
    # walks a dotted path at runtime, so no ast.Attribute node shows the dunder
    # (``string.Formatter().get_field`` is the same primitive). Referencing them at
    # all (call, alias, or import) is refused.
    FORBIDDEN_GETTERS = frozenset({"attrgetter", "methodcaller", "get_field"})

    # String-format entry points whose templates can perform attribute access.
    FORMAT_ATTRS = frozenset({"format", "format_map", "vformat"})

    # Dunders that customize how an object is SERIALIZED. Defining one lets a
    # value smuggle a callable + args into a pickle stream, to be invoked at
    # unpickle time outside this sandbox. FORBIDDEN_ATTRS already covers reading
    # them (an ast.Attribute); this covers *defining* them, which is an
    # ast.FunctionDef inside a ClassDef and therefore a different node type.
    # Layer 4 of the checkpoint pickle boundary — see safe_pickle.py.
    FORBIDDEN_METHOD_DEFS = frozenset(
        {
            "__reduce__",
            "__reduce_ex__",
            "__getstate__",
            "__setstate__",
            "__getnewargs__",
            "__getnewargs_ex__",
        }
    )

    def __init__(self):
        self.violations: list[str] = []
        # A dunder-reaching format template is only dangerous if something formats it,
        # and the template may be bound to a name first (``s = '{0.__class__}'`` ...
        # ``s.format(x)``), so both halves are tracked and flagged when both occur.
        self._format_used = False
        self._dunder_templates: list[str] = []
        self._format_flagged = False

    def _flag_dunder_format(self) -> None:
        if self._format_used and self._dunder_templates and not self._format_flagged:
            self._format_flagged = True
            self.violations.append(
                f"str.format template reaching a dunder: {self._dunder_templates[0][:80]!r}"
            )

    def visit_Constant(self, node: ast.Constant) -> None:
        """Track string constants whose format fields reach a dunder."""
        if isinstance(node.value, str) and _DUNDER_FORMAT_FIELD.search(node.value):
            self._dunder_templates.append(node.value)
            self._flag_dunder_format()
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Reject bare references to name-string attribute getters."""
        if node.id in self.FORBIDDEN_GETTERS:
            self.violations.append(f"{node.id}")
        self.generic_visit(node)

    def _check_method_def(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if node.name in self.FORBIDDEN_METHOD_DEFS:
            self.violations.append(f"def {node.name}(...)")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Reject definitions of serialization-hook dunders."""
        self._check_method_def(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Reject async definitions of serialization-hook dunders."""
        self._check_method_def(node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Reject `__reduce__ = fn`, which binds a hook without a FunctionDef."""
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in self.FORBIDDEN_METHOD_DEFS:
                self.violations.append(f"{target.id} = ...")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Reject custom metaclasses.

        A metaclass ``__new__`` receives the class namespace as an ordinary dict
        and can install a serialization hook under a COMPUTED key
        (``ns["__redu" + "ce__"] = fn``), which no static key check can see. The
        key computation is not itself the vulnerability — installing the dict as
        a class namespace is, and that has exactly two routes: ``type(n, b, d)``
        (rejected in visit_Call) and a metaclass. Closing both makes computed
        keys inert. Custom metaclasses have no legitimate use in analysis code.
        """
        for keyword in node.keywords:
            if keyword.arg == "metaclass":
                self.violations.append("class ... (metaclass=...)")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Extend dunder-subscript checks to serialization hooks."""
        target = getattr(node, "slice", None)
        if (
            isinstance(target, ast.Constant)
            and isinstance(target.value, str)
            and target.value in self.FORBIDDEN_METHOD_DEFS
        ):
            self.violations.append(f"['{target.value}']")
        return self._visit_subscript_forbidden_attrs(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        """Reject any dict literal keyed by a serialization-hook name.

        Closes the indirection path where the namespace is built first and only
        later used to create a class, so the hook name never appears next to a
        `type(...)` call: `d = {'__reduce__': fn}` … `type('C', (), d)`.
        """
        for key in node.keys:
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and key.value in self.FORBIDDEN_METHOD_DEFS
            ):
                self.violations.append(f"{{'{key.value}': ...}}")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Check regular imports: import os"""
        for alias in node.names:
            module = alias.name.split(".")[0]
            if module in self.FORBIDDEN_MODULES:
                self.violations.append(f"import {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from imports: from os import path"""
        if node.module:
            module = node.module.split(".")[0]
            if module in self.FORBIDDEN_MODULES:
                self.violations.append(f"from {node.module} import ...")
        for alias in node.names:
            if alias.name in self.FORBIDDEN_GETTERS:
                self.violations.append(f"from {node.module} import {alias.name}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for forbidden functions."""
        # Check direct calls: eval(...)
        if isinstance(node.func, ast.Name):
            if node.func.id in self.FORBIDDEN_CALLS:
                self.violations.append(f"{node.func.id}()")

        # Check attribute calls: obj.__class__()
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in self.FORBIDDEN_ATTRS:
                self.violations.append(f".{node.func.attr}()")

        # Dynamic class creation is a general sandbox-escape primitive and can
        # bind a serialization hook with no FunctionDef and no Assign:
        #   type('C', (), {'__reduce__': fn})        <- literal namespace
        #   d = {...}; type('C', (), d)              <- namespace via variable
        # Matching only the literal form left the variable form open, so the
        # 3-argument form is rejected outright. The 1-argument form (`type(x)`,
        # ubiquitous in analysis code) is untouched.
        if isinstance(node.func, ast.Name) and node.func.id == "type" and len(node.args) == 3:
            self.violations.append("type(name, bases, dict) dynamic class creation")

        # dict(__reduce__=fn) builds a hook-bearing namespace with no ast.Dict
        # node at all, so visit_Dict never sees it.
        if isinstance(node.func, ast.Name) and node.func.id == "dict":
            for keyword in node.keywords:
                if keyword.arg in self.FORBIDDEN_METHOD_DEFS:
                    self.violations.append(f"dict({keyword.arg}=...)")

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check attribute access for forbidden dunder attributes."""
        if node.attr in self.FORBIDDEN_ATTRS:
            self.violations.append(f".{node.attr}")
        if node.attr in self.FORBIDDEN_GETTERS:
            self.violations.append(f".{node.attr}")
        if node.attr in self.FORMAT_ATTRS:
            self._format_used = True
            self._flag_dunder_format()
        self.generic_visit(node)

    def _visit_subscript_forbidden_attrs(self, node: ast.Subscript) -> None:
        """Check subscript access for string-based dunder bypass attempts.

        Catches patterns like: obj['__class__'] or obj["__globals__"]
        """
        if isinstance(node.slice, ast.Constant):
            if isinstance(node.slice.value, str):
                if node.slice.value in self.FORBIDDEN_ATTRS:
                    self.violations.append(f"['{node.slice.value}']")
        self.generic_visit(node)
