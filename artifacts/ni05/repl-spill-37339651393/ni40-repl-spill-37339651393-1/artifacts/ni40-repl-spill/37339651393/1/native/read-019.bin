"""Code and document search via NextPLAID multi-vector retrieval.

Provides mixin with: code_search, doc_search.

These tools complement recall() (episodic memory) by searching actual source
code and documentation using token-level ColBERT matching — finding specific
function names, class definitions, and code patterns rather than past routing
decisions.

Phase 5 architecture: two NextPLAID containers with specialized models.
  :8088  nextplaid-code   LateOn-Code (130M, 128-dim, INT8)   → code index (AST-chunked)
  :8089  nextplaid-docs   GTE-ModernColBERT-v1 (149M, 128-dim, INT8) → docs index
         (answerai-colbert-small-v1 was retired 2026-02-20; the model is declared in
         orchestration/launch_manifest.yaml `nextplaid-docs`, which is authoritative)

Degrades gracefully: if docs container down, falls back to code container.

code_search() routes through the ColGREP CLI binary
(github.com/lightonai/next-plaid) by default. ColGREP is the same ColBERT
family with hybrid FTS5 keyword fusion + tree-sitter chunking, runs as a
single Rust binary, and falls back to CPU on hosts without CUDA. To opt
back into NextPLAID for code_search, set REPL_COLGREP=0 (also accepts
"false"/"off"). doc_search() always uses NextPLAID (ColGREP is code-focused).

Default flipped 2026-04-29 after a 14-query paired A/B showed colgrep
top-1 = 10/14 (71%) vs NextPLAID top-1 = 2/14 (14%) on canonical
production-code queries. See handoffs/active/repl-turn-efficiency.md S7.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]


logger = logging.getLogger(__name__)

CODE_SEARCH_URL = "http://localhost:8088"
DOC_SEARCH_URL = "http://localhost:8089"
VALID_INDICES = frozenset({"code", "docs"})

# ColGREP CLI integration (default ON; set REPL_COLGREP=0 to use NextPLAID).
# Subprocess-per-query: every call pays full ONNX runtime + ColBERT model
# load (~770 ms p50, ~2.3 s worst-case). Acceptable for human-paced REPL;
# if soak telemetry shows the hit is real for high-frequency tool loops,
# see handoffs/active/repl-turn-efficiency.md "Cold-Start Daemon Gate".
COLGREP_VERSION = "1.2.0"
COLGREP_EXPECTED_SHA256 = "833e52aa6c40d090142fa132e3c75d3e792a4707474682a2496e3471f646f956"
COLGREP_BIN = f"/mnt/raid0/llm/UTILS/bin/colgrep-{COLGREP_VERSION}"
COLGREP_DEFAULT_PATH = str(_REPO_ROOT / "src")
COLGREP_TIMEOUT_S = 10


def _colgrep_enabled() -> bool:
    """ColGREP is the default code_search engine. Explicit opt-out via REPL_COLGREP=0."""
    return os.environ.get("REPL_COLGREP", "1").lower() not in ("0", "false", "off")


class _CodeSearchMixin:
    """Mixin providing multi-vector code/doc search tools.

    Required attributes (provided by REPLEnvironment.__init__):
        config: REPLConfig
        artifacts: dict
        _exploration_calls: int
        _exploration_log: ExplorationLog
        _research_context: ResearchContext
        _last_research_node: str | None
    """

    _code_client: Any = None  # Lazy-loaded, :8088
    _docs_client: Any = None  # Lazy-loaded, :8089

    def _init_nextplaid_client(self, url: str) -> Any:
        """Create and health-check a NextPLAID client. Returns None if unavailable."""
        try:
            from next_plaid_client import NextPlaidClient

            client = NextPlaidClient(url)
            health = client.health()
            if health.status != "healthy":
                logger.warning("NextPLAID at %s unhealthy: %s", url, health.status)
                return None
            return client
        except ImportError:
            logger.debug("next-plaid-client not installed")
            return None
        except Exception as e:
            logger.debug("NextPLAID at %s unavailable: %s", url, e)
            return None

    def _get_nextplaid_client(self, index: str = "code") -> Any:
        """Return the appropriate NextPLAID client for the given index.

        Routing:
            code → :8088 (_code_client)
            docs → :8089 (_docs_client), falls back to :8088 if unavailable
        """
        if index == "code":
            if self._code_client is None:
                self._code_client = self._init_nextplaid_client(CODE_SEARCH_URL)
            return self._code_client

        # docs index → try dedicated docs container first
        if self._docs_client is None:
            self._docs_client = self._init_nextplaid_client(DOC_SEARCH_URL)
        if self._docs_client is not None:
            return self._docs_client

        # Fallback: docs container down → use code container (lower quality but functional)
        logger.info("Docs container (:8089) unavailable, falling back to code container (:8088)")
        if self._code_client is None:
            self._code_client = self._init_nextplaid_client(CODE_SEARCH_URL)
        return self._code_client

    def _code_search(self, query: str, limit: int = 5) -> str:
        """Search project source code for relevant passages.

        Uses multi-vector (ColBERT) retrieval with token-level matching.
        Finds specific function names, class definitions, and code patterns —
        not just semantic similarity.

        Unlike recall() which searches episodic memories (past routing decisions),
        code_search() finds actual source code in the project.

        Args:
            query: Natural language or code pattern to search for.
                   e.g., "escalation policy implementation",
                         "def embed_task_ir", "FAISS index configuration"
            limit: Maximum results to return (default 5).

        Returns:
            JSON with matching code passages, file paths, and line ranges.
        """
        # BEP/DCP harness (Phase 1, #7): ColGREP/NextPLAID are indexed over the production
        # corpus and cannot search an arbitrary scratch repo. When ORCHESTRATOR_EDIT_ROOT is
        # active, search the (small) scratch task-root directly so the model + DCP discover the
        # files they actually edit. Default-off: falls through to ColGREP exactly as before.
        from src.repl_environment.task_root import task_root_active

        if task_root_active():
            return self._task_root_code_search(query, limit=limit)
        if _colgrep_enabled():
            return self._colgrep_search(query, limit=limit)
        return self._nextplaid_search(query, index="code", limit=limit)

    def _task_root_code_search(self, query: str, limit: int) -> str:
        """Index-free code search over the scratch task-root (#7). Returns a ColGREP-JSON-shaped
        string (path/score/start_line/end_line) so `parse_colgrep_json` consumes it unchanged.
        Used only when ORCHESTRATOR_EDIT_ROOT is active (small scratch repos)."""
        import json
        import re

        from src.repl_environment.task_root import get_task_root

        root = get_task_root()
        terms = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
        code_exts = {
            ".py", ".txt", ".md", ".cfg", ".toml", ".json", ".yaml", ".yml", ".js", ".ts",
            # DCP-10a: C/C++/Go/Rust/Java task roots (ContextBench C/C++ arm).
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".go", ".rs", ".java",
        }
        full_file_line_limit = 80
        context_padding = 20
        hits: list[dict] = []

        def _matched_window(lines: list[str]) -> tuple[int, int]:
            if not lines:
                return (1, 1)
            if len(lines) <= full_file_line_limit:
                return (1, len(lines))
            first_ln = 1
            for i, line in enumerate(lines, 1):
                if any(t in line.lower() for t in terms):
                    first_ln = i
                    break
            return (
                max(1, first_ln - context_padding),
                min(len(lines), first_ln + context_padding),
            )

        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.suffix not in code_exts:
                continue
            rel = p.relative_to(root)
            if any(part.startswith(".") for part in rel.parts):  # skip .git, etc.
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            low = text.lower()
            rel_s = str(rel)
            name_score = sum(2 for t in terms if t in rel_s.lower())
            body_score = sum(low.count(t) for t in terms)
            score = name_score * 5 + body_score
            if score <= 0:
                continue
            start_ln, end_ln = _matched_window(text.splitlines())
            hits.append(
                {
                    "path": rel_s,
                    "score": float(score),
                    "start_line": start_ln,
                    "end_line": end_ln,
                }
            )
        hits.sort(key=lambda h: -h["score"])
        return json.dumps(hits[:limit])

    def _doc_search(self, query: str, limit: int = 5) -> str:
        """Search project documentation for relevant sections.

        Searches markdown docs, handoffs, model registry, and config files.
        For source code, use code_search() instead.

        Args:
            query: What to look for in documentation.
            limit: Maximum results (default 5).

        Returns:
            JSON with matching doc passages and metadata.
        """
        # INF-78 OAB-1: unavailable in a task_root-scoped request (no-op otherwise).
        from src.repl_environment.task_root import scope_refusal as _scope_refusal

        _scope_denial = _scope_refusal('doc_search')
        if _scope_denial is not None:
            return f"[ERROR: {_scope_denial}]"
        # AP-54: the docs index covers project docs and handoffs; refused while
        # the eval knowledge fence is armed (no-op otherwise).
        from src.repl_environment.knowledge_fence import check_tool_call

        fence_denial = check_tool_call("doc_search", {})
        if fence_denial is not None:
            return self._maybe_wrap_tool_output(
                json.dumps({"results": [], "error": fence_denial})
            )
        return self._nextplaid_search(query, index="docs", limit=limit)

    def _nextplaid_search(self, query: str, index: str, limit: int) -> str:
        """Internal: execute search against a NextPLAID index."""
        lock = getattr(self, "_state_lock", None)
        if lock:
            with lock:
                self._exploration_calls += 1
        else:
            self._exploration_calls += 1

        if index not in VALID_INDICES:
            output = json.dumps(
                {"results": [], "error": f"Invalid index '{index}'. Valid: {sorted(VALID_INDICES)}"}
            )
            return self._maybe_wrap_tool_output(output)

        client = self._get_nextplaid_client(index)
        if client is None:
            output = json.dumps({"results": [], "error": "NextPLAID not available"})
            return self._maybe_wrap_tool_output(output)

        try:
            from next_plaid_client.models import SearchParams

            params = SearchParams(top_k=min(limit, 20))
            result = client.search_with_encoding(index, queries=[query], params=params)

            results = []
            if result.results:
                qr = result.results[0]  # Single query → first QueryResult
                for doc_id, score, meta in zip(qr.document_ids, qr.scores, qr.metadata):
                    if len(results) >= limit:
                        break
                    entry = {
                        "file": meta.get("file", "unknown"),
                        "lines": f"{meta.get('start_line', '?')}-{meta.get('end_line', '?')}",
                        "score": round(float(score), 3),
                    }
                    # Include AST metadata when available (Phase 5)
                    unit_name = meta.get("unit_name")
                    if unit_name:
                        entry["unit"] = f"{meta.get('unit_type', '')}:{unit_name}"
                        sig = meta.get("signature", "")
                        if sig:
                            entry["signature"] = sig[:100]
                    results.append(entry)

            # Frecency boost for search results (feature-flagged)
            import os as _os

            if results and _os.environ.get("REPL_FRECENCY", "").lower() in ("1", "true", "on"):
                try:
                    from src.repl_environment.file_recency import FrecencyStore

                    _frecency = getattr(self, "_frecency_store", None)
                    if _frecency is None:
                        _frecency = FrecencyStore()
                        self._frecency_store = _frecency
                    for r in results:
                        boost = _frecency.get_score(r["file"])
                        r["score"] = round(r["score"] * (1 + 0.3 * boost), 3)
                    results.sort(key=lambda r: r["score"], reverse=True)
                except Exception:
                    logger.debug("Frecency boost failed", exc_info=True)

            response = {"results": results, "index": index, "query": query}

            self._exploration_log.add_event(
                "code_search" if index == "code" else "doc_search",
                {"query": query, "index": index},
                response,
            )

            # Track in research context
            tool_name = "code_search" if index == "code" else "doc_search"
            node_id = self._research_context.add(
                tool=tool_name,
                query=query[:100],
                content=json.dumps(results[:3]),
                parent_id=self._last_research_node,
            )
            self._last_research_node = node_id

            output = json.dumps(response, indent=2)
            return self._maybe_wrap_tool_output(output)

        except Exception as e:
            logger.warning("NextPLAID search failed: %s", e)
            output = json.dumps({"results": [], "error": str(e)})
            return self._maybe_wrap_tool_output(output)

    def _record_colgrep_telemetry(
        self,
        *,
        query: str,
        limit: int,
        latency_ms: int,
        fallback: bool,
        reason: str | None = None,
        returncode: int | None = None,
        result_count: int | None = None,
    ) -> None:
        """Persist ColGREP timing/fallback telemetry for soak-gate analysis."""
        event = {
            "engine": "colgrep",
            "query": query[:200],
            "limit": limit,
            "latency_ms": latency_ms,
            "fallback": fallback,
        }
        if reason:
            event["fallback_reason"] = reason
        if returncode is not None:
            event["returncode"] = returncode
        if result_count is not None:
            event["result_count"] = result_count

        telemetry = self.artifacts.setdefault("_code_search_telemetry", [])
        if isinstance(telemetry, list):
            telemetry.append(event)
        else:
            self.artifacts["_code_search_telemetry"] = [event]

        if fallback:
            logger.warning(
                "ColGREP code_search fallback reason=%s latency_ms=%d returncode=%s",
                reason or "unknown",
                latency_ms,
                returncode,
            )
        else:
            logger.info(
                "ColGREP code_search success latency_ms=%d result_count=%s",
                latency_ms,
                result_count,
            )

    def _colgrep_search(self, query: str, limit: int) -> str:
        """Internal: execute code_search via the ColGREP CLI binary.

        Subprocess-per-query (no daemon mode upstream). Falls back to
        NextPLAID on missing binary, timeout, or non-zero exit so callers
        always get a valid response shape.
        """
        started = time.perf_counter()
        lock = getattr(self, "_state_lock", None)
        if lock:
            with lock:
                self._exploration_calls += 1
        else:
            self._exploration_calls += 1

        bin_path = os.environ.get("REPL_COLGREP_BIN", COLGREP_BIN)
        proj_path = os.environ.get("REPL_COLGREP_PATH", COLGREP_DEFAULT_PATH)
        if not shutil.which(bin_path) and not os.path.isfile(bin_path):
            logger.warning("ColGREP binary not found at %s, falling back to NextPLAID", bin_path)
            self._record_colgrep_telemetry(
                query=query,
                limit=limit,
                latency_ms=round((time.perf_counter() - started) * 1000),
                fallback=True,
                reason="missing_binary",
            )
            return self._nextplaid_search(query, index="code", limit=limit)

        env = {**os.environ, "NEXT_PLAID_FORCE_CPU": "1"}
        # alpha=0.95 weights semantic ColBERT over FTS5 keyword. Default 0.75
        # over-ranks __init__.py re-exports for symbol queries in this corpus
        # (validated 2026-04-29: alpha 0.95 recovers correct top-1 on
        # FinalSignal/ASTSecurityVisitor/create_repl_environment).
        alpha = os.environ.get("REPL_COLGREP_ALPHA", "0.95")
        cmd = [
            bin_path,
            "search",
            query,
            "-k",
            str(min(limit, 20)),
            "--alpha",
            alpha,
            "--json",
            proj_path,
        ]
        try:
            proc = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=COLGREP_TIMEOUT_S,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "ColGREP timed out after %ds, falling back to NextPLAID", COLGREP_TIMEOUT_S
            )
            self._record_colgrep_telemetry(
                query=query,
                limit=limit,
                latency_ms=round((time.perf_counter() - started) * 1000),
                fallback=True,
                reason="timeout",
            )
            return self._nextplaid_search(query, index="code", limit=limit)
        except OSError as e:
            logger.warning("ColGREP subprocess failed: %s, falling back to NextPLAID", e)
            self._record_colgrep_telemetry(
                query=query,
                limit=limit,
                latency_ms=round((time.perf_counter() - started) * 1000),
                fallback=True,
                reason="oserror",
            )
            return self._nextplaid_search(query, index="code", limit=limit)

        if proc.returncode != 0:
            logger.warning("ColGREP exit %d: %s", proc.returncode, proc.stderr[:500])
            self._record_colgrep_telemetry(
                query=query,
                limit=limit,
                latency_ms=round((time.perf_counter() - started) * 1000),
                fallback=True,
                reason="nonzero_exit",
                returncode=proc.returncode,
            )
            return self._nextplaid_search(query, index="code", limit=limit)

        try:
            raw = json.loads(proc.stdout) if proc.stdout.strip() else []
        except json.JSONDecodeError as e:
            logger.warning("ColGREP JSON parse failed: %s", e)
            self._record_colgrep_telemetry(
                query=query,
                limit=limit,
                latency_ms=round((time.perf_counter() - started) * 1000),
                fallback=True,
                reason="bad_json",
                returncode=proc.returncode,
            )
            return self._nextplaid_search(query, index="code", limit=limit)

        results = []
        for item in raw[:limit]:
            unit = item.get("unit", {}) if isinstance(item, dict) else {}
            file_path = unit.get("file", "unknown")
            try:
                rel = os.path.relpath(file_path, proj_path)
            except ValueError:
                rel = file_path
            entry = {
                "file": rel,
                "lines": f"{unit.get('line', '?')}-{unit.get('end_line', '?')}",
                "score": round(float(item.get("score", 0.0)), 3),
            }
            unit_name = unit.get("name")
            unit_type = unit.get("unit_type")
            if unit_name and unit_type and unit_type != "rawcode":
                entry["unit"] = f"{unit_type}:{unit_name}"
                sig = unit.get("signature") or ""
                if sig:
                    entry["signature"] = sig[:100]
            results.append(entry)

        # Frecency boost (same flag as NextPLAID path)
        if results and os.environ.get("REPL_FRECENCY", "").lower() in ("1", "true", "on"):
            try:
                from src.repl_environment.file_recency import FrecencyStore

                _frecency = getattr(self, "_frecency_store", None)
                if _frecency is None:
                    _frecency = FrecencyStore()
                    self._frecency_store = _frecency
                for r in results:
                    boost = _frecency.get_score(r["file"])
                    r["score"] = round(r["score"] * (1 + 0.3 * boost), 3)
                results.sort(key=lambda r: r["score"], reverse=True)
            except Exception:
                logger.debug("Frecency boost failed", exc_info=True)

        latency_ms = round((time.perf_counter() - started) * 1000)
        self._record_colgrep_telemetry(
            query=query,
            limit=limit,
            latency_ms=latency_ms,
            fallback=False,
            returncode=proc.returncode,
            result_count=len(results),
        )

        response = {
            "results": results,
            "index": "code",
            "query": query,
            "engine": "colgrep",
            "latency_ms": latency_ms,
        }
        self._exploration_log.add_event(
            "code_search",
            {
                "query": query,
                "index": "code",
                "engine": "colgrep",
                "latency_ms": latency_ms,
                "fallback": False,
            },
            response,
        )
        node_id = self._research_context.add(
            tool="code_search",
            query=query[:100],
            content=json.dumps(results[:3]),
            parent_id=self._last_research_node,
        )
        self._last_research_node = node_id

        output = json.dumps(response, indent=2)
        return self._maybe_wrap_tool_output(output)
