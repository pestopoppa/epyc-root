# Deterministic arithmetic tool: implementation handoff

The 2026-08-12 worker probe had two arithmetic errors on both LFM quants; that result does not establish a tool-routing capability. The tool is not implemented or deployed by this document. Implementation belongs in `epyc-orchestrator`, not this umbrella repository.

## Integration points verified 2026-11-02

- `src/tools/__init__.py::register_all_tools` registers web, file, code, data and knowledge tools. `src/tools/code` provides test and lint operations; it is not a calculator.
- Follow the existing `Tool` / `ToolRegistry` registration pattern in `src/tools/code/lint.py::register_lint_tool`; register the arithmetic handler through the built-in registration path. Inspect current allowlisting and worker tool exposure before claiming a worker can invoke it: registration alone does not establish routing.
- `src/tools/base.py::with_timeout` cannot kill a runaway worker thread. A handler must bound its own work; a timeout alone is not a resource limit.

## Proposed minimum contract

A pure calculator accepts one arithmetic expression string and returns an explicit success/result or error. Parse a small allowlisted grammar (numeric literals, parentheses, unary signs and basic binary arithmetic); do not use `eval`, `exec`, attribute access, calls, names, comprehensions or arbitrary Python. Define decimal and division semantics explicitly in the schema. Bound expression length, syntax-tree nodes and depth, literal digits, intermediate magnitude and output size *before or during* evaluation. Reject invalid syntax, division by zero, unsupported operators, oversized inputs and results without returning an invented numeric answer. Keep the handler free of filesystem, network and subprocess access.

## Required verification before closing the handoff

1. Unit-test exact valid arithmetic including `17*23 = 391`, parentheses, signs and the documented division semantics; include invalid and resource-boundary cases and injection attempts.
2. Test registration and invocation through the actual registry, including error propagation and the worker's real tool exposure. Prove the worker receives and can call the tool, rather than inferring this from registration.
3. Evaluate representative arithmetic requests end to end, retaining tool-call attempts, parse failures and wrong or missing results. A correct calculator invocation does not prove that the model selects the tool or translates a word problem correctly.
4. Wire any new measurement source into the belief substrate per the root guidance; retain the existing worker quality task until its separate protocol is satisfied.
