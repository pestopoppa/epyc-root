"""Contextual suggestions appended to tool output (S3a).

After each tool execution, generates 2-3 likely next commands based on:
1. Tool co-occurrence patterns (hardcoded from S2a log mining)
2. Frecency file data (from S1 FrecencyStore)

Feature-gated by REPL_SUGGESTIONS env var (default OFF).
Gated on Omega improvement before shipping (REPL >= direct on >= 5/10 suites).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_FEATURE_FLAG_VALUES = {"1", "true", "on"}

# Co-occurrence matrix from S2a autopilot log mining (2026-04-09).
# Maps tool_name -> [(next_tool, probability, suggestion_text)]
# Only includes transitions with >= 10% probability.
TOOL_COOCCURRENCE: dict[str, list[tuple[str, float, str]]] = {
    "web_search": [
        ("web_search", 0.85, "web_search(<related query>)"),
        ("search_wikipedia", 0.10, "search_wikipedia(<topic>)"),
    ],
    "search_wikipedia": [
        ("web_search", 0.60, "web_search(<refinement>)"),
    ],
    "peek": [
        ("grep", 0.40, "grep(<pattern>, file_path=<file>)"),
        ("peek", 0.30, "peek(2000, file_path=<next file>)"),
        ("code_search", 0.20, "code_search(<query>)"),
    ],
    "grep": [
        ("peek", 0.50, "peek(2000, file_path=<matched file>)"),
        ("grep", 0.30, "grep(<refined pattern>)"),
    ],
    "list_dir": [
        ("peek", 0.60, "peek(2000, file_path=<file>)"),
        ("list_dir", 0.20, "list_dir(<subdir>)"),
    ],
    "web_fetch": [
        ("web_search", 0.40, "web_search(<follow-up>)"),
        ("peek", 0.30, "peek(2000, file_path=<downloaded file>)"),
    ],
}


def _feature_enabled() -> bool:
    """Check whether contextual suggestions are enabled via env var."""
    return os.environ.get("REPL_SUGGESTIONS", "").strip().lower() in _FEATURE_FLAG_VALUES


def generate_suggestions(
    tool_name: str,
    frecency_store=None,
    max_suggestions: int = 3,
) -> str:
    """Generate suggestion block for tool output.

    Returns empty string if feature disabled or no suggestions available.
    """
    if not _feature_enabled():
        return ""

    suggestions: list[str] = []
    frecency_line: str = ""

    # 1. Frecency-boosted file hint (for file-oriented tools) — reserve 1 slot
    if frecency_store and tool_name in ("peek", "grep", "list_dir"):
        try:
            top_files = frecency_store.top_k(5)
            if top_files:
                names = ", ".join(f.rsplit("/", 1)[-1] for f in top_files[:3])
                frecency_line = f"  # Recent: {names}"
        except Exception:
            pass  # Graceful degradation

    # 2. Co-occurrence based suggestions (leave room for frecency if present)
    cooc_limit = max_suggestions - (1 if frecency_line else 0)
    cooccurrences = TOOL_COOCCURRENCE.get(tool_name, [])
    for _next_tool, _prob, template in cooccurrences[:cooc_limit]:
        suggestions.append(f"  {template}")

    if frecency_line:
        suggestions.append(frecency_line)

    if not suggestions:
        return ""

    return "\n[Suggested next]\n" + "\n".join(suggestions[:max_suggestions])


class _SuggestionsMixin:
    """Mixin that appends contextual suggestions to tool output.

    Feature flag: REPL_SUGGESTIONS env var (1/true/on to enable, default off).
    """

    def _maybe_append_suggestions(self, tool_name: str, observation: str) -> str:
        """Append suggestions to observation if feature enabled."""
        frecency = getattr(self, "_frecency_store", None)
        block = generate_suggestions(
            tool_name=tool_name,
            frecency_store=frecency,
        )
        if block:
            return observation + block
        return observation
