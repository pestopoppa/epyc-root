"""Per-model agent-file compression-tolerance compliance suite.

Three task classes per the handoff:
- forbidden_actions: prompts that try to trick the model into violating a directive.
- procedure_correctness: multi-step procedures where order matters.
- instruction_recall: direct queries about specific clauses.

Scoring runner (`runner.py`) takes (model_id, agent_file_path, level) and returns
a result dict with token_count, compliance_pass_rate, recall_pass_rate,
procedure_pass_rate. Inference itself is out-of-scope here — the runner accepts
an injected `llm_call` callable so tests can use a deterministic fake.

Per handoffs/active/agent-file-prose-compression.md Phase 2.
"""
