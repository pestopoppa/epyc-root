"""Live-LLM adapter for the compliance suite.

Wraps `runner.run_compliance_suite()` with an httpx-backed `llm_call`
that posts to a standard llama-server `/v1/chat/completions` endpoint.

Phase 3 (per handoffs/active/agent-file-prose-compression.md): replace
the deterministic fake LLM in runner.py with this live adapter to measure
real per-model compression-tolerance.

Usage:
    # Smoke against one model at one level:
    python3 tests/compliance/agent_file/live_runner.py \\
        --base-url http://localhost:8080 \\
        --model-id qwen3-coder-30b-a3b-q4 \\
        --agent-file agents/shared/ENGINEERING_STANDARDS.md \\
        --level mild \\
        --output data/compliance/2026-05-06-smoke.json

The runner loads the agent file, sends agent-file + each task prompt to
the model, and scores the response per the existing forbidden_actions /
procedure / instruction_recall task pools.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict
from pathlib import Path

import urllib.request
import urllib.error

# Make repo root importable.
_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tests.compliance.agent_file.runner import run_compliance_suite  # noqa: E402

logger = logging.getLogger(__name__)


def make_live_llm_call(
    base_url: str,
    model: str = "default",
    max_tokens: int = 512,
    temperature: float = 0.0,
    timeout_s: float = 90.0,
):
    """Build an LLMCall closure that posts to /v1/chat/completions.

    The agent file is sent as a system message; the task prompt is the
    user message. Temperature 0 for reproducibility on smoke runs.
    """

    def call(agent_file_text: str, prompt: str) -> str:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": agent_file_text},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=f"{base_url.rstrip('/')}/v1/chat/completions",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            logger.warning("live llm_call URLError: %s", e)
            return ""
        except Exception as e:  # noqa: BLE001
            logger.warning("live llm_call failed: %s", e)
            return ""

        try:
            d = json.loads(body)
        except json.JSONDecodeError:
            logger.warning("non-JSON response: %s", body[:200])
            return ""

        try:
            return d["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            logger.warning("unexpected response shape: %s", json.dumps(d)[:200])
            return ""

    return call


def health_check(base_url: str, timeout_s: float = 5.0) -> bool:
    """Probe /health (or /) for readiness."""
    for path in ("/health", "/v1/models", "/"):
        try:
            req = urllib.request.Request(url=f"{base_url.rstrip('/')}{path}", method="GET")
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                if 200 <= resp.status < 400:
                    return True
        except Exception:
            continue
    return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="live_compliance", description=__doc__)
    p.add_argument("--base-url", default="http://localhost:8080")
    p.add_argument("--model-id", default="live-model", help="Identifier recorded in the result")
    p.add_argument("--agent-file", required=True, help="Path to the agent file under test")
    p.add_argument("--level", default="none", choices=["none", "mild", "medium", "aggressive"])
    p.add_argument("--max-tokens", type=int, default=512)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--timeout", type=float, default=90.0)
    p.add_argument("--output", help="Optional JSON output path")
    p.add_argument("--max-tasks", type=int, default=0,
                   help="Limit to N tasks per pool (0 = all). Useful for quick smokes.")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not health_check(args.base_url):
        print(f"ERROR: server at {args.base_url} not reachable", file=sys.stderr)
        return 2

    print(f"=== live compliance smoke ===")
    print(f"  base_url     : {args.base_url}")
    print(f"  model_id     : {args.model_id}")
    print(f"  agent_file   : {args.agent_file}")
    print(f"  level        : {args.level}")
    print(f"  max_tokens   : {args.max_tokens}")
    print(f"  temperature  : {args.temperature}")
    if args.max_tasks:
        print(f"  max_tasks    : {args.max_tasks} per pool")
    print()

    llm_call = make_live_llm_call(
        base_url=args.base_url,
        model=args.model_id,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        timeout_s=args.timeout,
    )

    # Optionally truncate task pools for fast smoke. Patch in-place via runner.
    if args.max_tasks > 0:
        from tests.compliance.agent_file import (
            forbidden_actions, procedure_correctness, instruction_recall,
        )
        forbidden_actions.TASKS = forbidden_actions.TASKS[:args.max_tasks]
        procedure_correctness.TASKS = procedure_correctness.TASKS[:args.max_tasks]
        instruction_recall.TASKS = instruction_recall.TASKS[:args.max_tasks]
        print(f"  task pools truncated to {args.max_tasks} each")
        print()

    started = time.perf_counter()
    suite = run_compliance_suite(
        model_id=args.model_id,
        agent_file_path=args.agent_file,
        level=args.level,
        llm_call=llm_call,
    )
    elapsed = time.perf_counter() - started

    d = suite.to_dict()
    d["elapsed_sec"] = round(elapsed, 1)
    d["base_url"] = args.base_url

    print(f"\n=== results ({elapsed:.1f}s) ===")
    print(f"  token_count          : {d['token_count']}")
    print(f"  compliance_pass_rate : {d['compliance_pass_rate']}")
    print(f"  procedure_pass_rate  : {d['procedure_pass_rate']}")
    print(f"  recall_pass_rate     : {d['recall_pass_rate']}")
    print()

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w") as f:
            json.dump(d, f, indent=2, default=str)
        print(f"  written: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
