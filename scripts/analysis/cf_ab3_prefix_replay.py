#!/usr/bin/env python3
"""CF-AB-3: offline prefix-stability replay for the CF-AB-1 arms (zero inference).

Given trajectories that carry the per-turn prompt pieces INCLUDING tool outputs,
render the prompt each arm (A0 control, A1, A3, A4, A5) would send at every turn and
report per turn (a) the common-prefix length with the previous turn's prompt and the
implied re-prefill fraction, and (b) an UPPER BOUND on what a shift/chunk path could
recover: tokens outside the common prefix that lie in a run of >= MIN_RUN tokens
identical to some run of the previous prompt (no live role can use shift reuse today).

Input trajectory (JSON object per file, or JSONL of turns):
  {"base": "<system+task text>", "window": 65536,
   "turns": [{"assistant": "<text>", "tool_results": [{"tool": "...", "args": "...",
              "text": "...", "error": false}]}, ...]}
Turn t's prompt contains turns 0..t-1 (assistant text + tool results) after ``base``.

Token unit: chars/4 ESTIMATE (``CHARS_PER_TOKEN``); the shift column therefore uses
MIN_RUN*4 characters.  A trajectory whose records lack tool-result text cannot be
rendered: ``load()`` raises ``Blocked`` (the CF-AB-3 blocked record) rather than
inventing text.  Arm constants are the CF-AB-1 declared parameters; A1's k is a flag.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CHARS_PER_TOKEN = 4
MIN_RUN = 256
SHINGLE = 64


class Blocked(Exception):
    """The corpus does not carry what the replay needs."""


def est_tokens(s: str) -> int:
    return -(-len(s) // CHARS_PER_TOKEN)


def load(path: Path) -> dict[str, Any]:
    d = json.loads(path.read_text())
    if not d.get("turns") or any(
        "text" not in r for t in d["turns"] for r in t.get("tool_results", [])
    ) or not any(t.get("tool_results") for t in d["turns"]):
        raise Blocked(f"{path}: no tool-result text in the trajectory")
    return d


def _stub(r: dict[str, Any], pointer: bool = True) -> str:
    ptr = f" peek({len(r['text'])}, file_path=<spill>)" if pointer else ""
    return f"[{r['tool']}({r.get('args', '')}) output elided: {len(r['text'])} chars{ptr}]"


def _headtail(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    h = cap // 2
    return text[:h] + f"\n[... {len(text) - cap} chars omitted ...]\n" + text[len(text) - (cap - h):]


def render(arm: str, traj: dict[str, Any], t: int, *, k: int = 8) -> str:
    """The prompt for turn ``t`` under ``arm`` (history = turns < t)."""
    results = [(i, j, r) for i in range(t) for j, r in enumerate(traj["turns"][i].get("tool_results", []))]
    n = len(results)
    age = {(i, j): n - 1 - idx for idx, (i, j, _) in enumerate(results)}  # 0 = newest
    window = traj.get("window", 65536)
    full_len = len(traj["base"]) + sum(
        len(traj["turns"][i].get("assistant", "")) + sum(len(r["text"]) for r in traj["turns"][i].get("tool_results", []))
        for i in range(t))
    frac = est_tokens("x" * full_len) / window  # fraction of window the unmanaged prompt would use
    parts = [traj["base"]]
    for i in range(t):
        turn = traj["turns"][i]
        parts.append(turn.get("assistant", ""))
        for j, r in enumerate(turn.get("tool_results", [])):
            a = age[(i, j)]
            txt = r["text"]
            if arm == "A0":
                pass
            elif arm == "A1":  # protected first/last zones + deterministic stubs older than k results
                if a >= k and i > 0 and not r.get("error"):
                    txt = _stub(r, pointer=False)
            elif arm == "A3":  # elide old results from 0.60 of window; hard 0.85 stubs all but recent 30% (>=2 turns)
                recent_turns = max(2, int(0.30 * t))
                if frac >= 0.60 and (t - i) > recent_turns:
                    txt = _headtail(txt, 1024) if frac < 0.85 else _stub(r)
            elif arm == "A4":  # age-tiered half-life, active from 0.50, newest 4 verbatim
                if frac >= 0.50 and a >= 4:
                    cap = 4096 if a <= 7 else 2048 if a <= 15 else 1024 if a <= 31 else 512 if a <= 63 else 256
                    txt = _headtail(txt, cap)
            elif arm == "A5":  # hard mask: K newest verbatim, errors exempt
                if a >= 5 and not r.get("error"):
                    txt = _stub(r)
            else:
                raise ValueError(arm)
            parts.append(txt)
    return "\n".join(parts)


def common_prefix(a: str, b: str) -> int:
    n = min(len(a), len(b))
    lo, hi = 0, n
    while lo < hi:  # binary search on prefix equality (slice compare is C-speed)
        mid = (lo + hi + 1) // 2
        if a[:mid] == b[:mid]:
            lo = mid
        else:
            hi = mid - 1
    return lo


def shift_recoverable_chars(prev: str, cur: str, prefix: int, min_chars: int | None = None) -> int:
    """Chars of ``cur`` beyond ``prefix`` inside matching runs >= min_chars of ``prev`` (upper bound)."""
    min_chars = min_chars or MIN_RUN * CHARS_PER_TOKEN
    index: dict[str, list[int]] = {}
    for p in range(0, max(0, len(prev) - SHINGLE + 1)):
        index.setdefault(prev[p:p + SHINGLE], []).append(p)
    covered, i, total = 0, prefix, 0
    while i < len(cur) - SHINGLE + 1:
        best = 0
        for p in index.get(cur[i:i + SHINGLE], ())[:16]:
            L = SHINGLE
            while i + L < len(cur) and p + L < len(prev) and cur[i + L] == prev[p + L]:
                L += 1
            best = max(best, L)
        if best >= min_chars:
            total += best
            i += best
        else:
            i += 1
    return total


def replay(traj: dict[str, Any], arms=("A0", "A1", "A3", "A4", "A5")) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for arm in arms:
        rows, prev = [], None
        for t in range(len(traj["turns"]) + 1):
            cur = render(arm, traj, t)
            if prev is not None:
                pre = common_prefix(prev, cur)
                tail = len(cur) - pre
                shift = shift_recoverable_chars(prev, cur, pre)
                rows.append({
                    "turn": t, "prompt_tok_est": est_tokens(cur), "common_prefix_tok_est": pre // CHARS_PER_TOKEN,
                    "reprefill_fraction": tail / len(cur) if cur else 0.0,
                    "shift_recoverable_fraction_of_tail": shift / tail if tail else 0.0,
                    "reprefill_after_shift_bound": (tail - shift) / len(cur) if cur else 0.0,
                })
            prev = cur
        out[arm] = rows
    return out


def summarise(per_traj: list[dict[str, list[dict[str, Any]]]]) -> dict[str, dict[str, float]]:
    agg: dict[str, dict[str, float]] = {}
    for arm in per_traj[0] if per_traj else []:
        rows = [r for p in per_traj for r in p[arm]]
        n = len(rows) or 1
        agg[arm] = {
            "turns": len(rows),
            "mean_reprefill_fraction": sum(r["reprefill_fraction"] for r in rows) / n,
            "mean_reprefill_after_shift_bound": sum(r["reprefill_after_shift_bound"] for r in rows) / n,
        }
    return agg


def probe_bep_corpus(root: Path) -> dict[str, Any]:
    """Can the TOC-SP-5 corpus (``data/bep_sandbox/**/traces/*.jsonl``) be replayed?

    Reports the union of per-turn keys, the longest string per key, and the turns that
    carry a prompt tail; ``blocked`` is true when no key can hold tool-output text or a
    whole prompt (the CF-AB-3 blocked record).
    """
    keys: dict[str, int] = {}
    longest: dict[str, int] = {}
    files = turns = tails = bad = 0
    for f in sorted(root.glob("**/traces/*.jsonl")):
        files += 1
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except ValueError:
                bad += 1
                continue
            turns += 1
            tails += 1 if "prompt_tail" in d else 0
            for k, v in d.items():
                keys[k] = keys.get(k, 0) + 1
                if isinstance(v, str):
                    longest[k] = max(longest.get(k, 0), len(v))
    full_prompt_possible = longest.get("prompt_tail", 0) >= 4096
    tool_output_key = [k for k in keys if "output" in k and k != "raw_output" and k in longest]
    return {
        "files": files, "turns": turns, "unparsable_lines": bad, "turns_with_prompt_tail": tails,
        "keys": keys, "longest_string_chars": longest, "tool_output_text_keys": tool_output_key,
        "blocked": not full_prompt_possible and not tool_output_key,
        "reason": "no tool-output text and no full prompt per turn (prompt_tail is a bounded suffix; "
                  "prompt_has_last_output is a boolean)" if not full_prompt_possible and not tool_output_key else "",
    }


def main(argv: list[str]) -> int:
    if argv[:1] == ["--probe-bep"]:
        print(json.dumps(probe_bep_corpus(Path(argv[1])), indent=1, sort_keys=True))
        return 0
    files = sorted(p for a in argv for p in (Path(a).rglob("*.json") if Path(a).is_dir() else [Path(a)]))
    try:
        trajs = [load(f) for f in files]
    except Blocked as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}))
        return 3
    print(json.dumps(summarise([replay(t) for t in trajs]), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
