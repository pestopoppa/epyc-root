#!/usr/bin/env python3
"""premise_screener.py — is this backlog row's premise STILL TRUE in the world?

Owning handoff: handoffs/active/loop-owned-fleet-implementation.md, task P2-2.
Plan of record:  docs/design/loop-owned-fleet.html ("premise_screener NEW —
                 the one day-1 classifier").
Consumer:        scripts/coordination/worker_runner.py (P2-1) preflight.

WHY THIS EXISTS, MEASURED
=========================
`backlog_row_check.py` screens a row's FORM against the file it lives in. It is
excellent at that and structurally incapable of more: it can prove a row is
WELL-FORMED, never that it is STILL-NEEDED. Nothing in this repo could look at
the world.

The cost of that gap was measured. Corpus-wide anchor rot ran 27% (2026-07-29)
to 51% twelve days later; the dispatch queue's own rot was 34.5% on 2026-08-11.
Then rows were fact-checked against reality rather than against their file: on
2026-08-12, **4 of 8** screened rows had premises that were ALREADY SATISFIED,
and a later round found **7 of 11**. Every one of those would have passed
`backlog_row_check.py` and burned a whole worker invocation — and a worker that
"fixes" already-fixed work can undo it.

This module is the judgment half of that pair. It is a POINT LLM CALL made at
the moment of decision, with its examples IN THE PROMPT — never doctrine a
caller is trusted to remember. That is the prose-rule moratorium's whole
substitution (`coordination/evals/README.md`): a rule is retrieved at the moment
of *reading*, an example is present at the moment of *deciding*. F-22 is the
proof — a rule violated 3m33s after it was written, by its own author.

THE CONTRACT (worker_runner.py is built against exactly this)
=============================================================
    screen_premise(row: dict) -> {
        "verdict":  "still-needed" | "stale" | "unknown",
        "evidence":  str,   # a quote from the artifact justifying the verdict
        "reason":    str,   # one sentence
        "provenance": {...} # model id, prompt hash, mechanical result, ...
    }

The one-argument call always works. Everything else is a keyword with a default.

FOUR PROPERTIES THIS FILE IS RESPONSIBLE FOR
============================================
1. FORCED CHOICE. Three verdicts, no fourth. `_coerce_verdict` is the only place
   a verdict string is minted and it maps anything it does not recognise to
   "unknown". There is no code path that can return a value outside `VERDICTS`.

2. MANDATORY EVIDENCE. A verdict without a usable quote is not a verdict. A
   model that answers "stale" and quotes nothing (or quotes the word "stale") is
   DOWNGRADED to "unknown" — never accepted. `_usable_evidence` is that gate;
   `provenance.downgraded_from` records what was refused, so the downgrade is
   auditable rather than silent.

3. UNKNOWN IS FIRST-CLASS AND NEVER MEANS FINE. No model, no server, a timeout,
   an exception, garbage output, a missing artifact — every one of them is
   "unknown", and the caller treats "unknown" as do-not-dispatch plus a routed
   fix task. This module has NO fail-open path. Fail-open here would silently
   re-run satisfied work, which is the exact failure it was built to stop.
   (Standing rule: fail-open fallbacks poison the stores that consume them.)

4. THE CHEAP CHECK RUNS FIRST. `backlog_row_check.py` is imported, never
   reimplemented. If the mechanical check can already PROVE the row is closed,
   this returns "stale" having spent ZERO tokens. Only genuinely uncertain rows
   reach the model.

WHAT THE MECHANICAL CHECK MAY AND MAY NOT CONCLUDE
==================================================
It may conclude STALE from exactly one signal: the row's box is `- [x]`. That is
a human writing "done" in the artifact, and per the project's checkbox axiom the
box state IS the record.

It may NOT conclude stale from anything else, and this is deliberate:

  * NOT from "not dispatchable". `backlog_row_check.classify()` refuses guarded
    boxes, prohibitions, operator-owned rows and blocked children. Those are
    all "not yours / not now" — the premise is very much alive. A prohibition in
    particular is still-needed FOREVER and has no completion state at all.
  * NOT from the row text being unfindable in `handoffs/active/`. Completed rows
    are deleted on completion, so absence *looks* like staleness — but absence
    is also what a queue row sourced from anywhere else looks like, and what a
    single unlucky search key looks like. The standing rule is that a negative
    is never asserted from one key or one root (see the pack's X3: a `.orphan`
    absence searched at the wrong root, where five orphans were extant). So an
    unresolvable row is handed to the model WITH that fact stated, not silently
    graded.

It also may not conclude still-needed. The mechanical layer either proves stale
or abstains; abstention costs one LLM call, and a false "still-needed" costs a
worker invocation.

WHY A BUNDLE OF PROBES, NOT JUST THE ROW TEXT
=============================================
The model has no tools. Handing it a row and asking "is this done?" invites
exactly the plausibility-reasoning the example pack spends six examples warning
against. So `build_bundle()` runs the cheap probes the pack's own worked
examples run, and puts their RESULTS in the prompt, so the model has artifacts
to quote:

  * the resolved box, its state, its section heading, its child boxes
  * `backlog_row_check.classify()`'s verdict and reasons
  * for every path the row names: does it exist, is it a symlink, and — the X1
    lesson — is it TRACKED IN GIT. An untracked file is byte-identical on disk
    to a committed one and satisfies none of "versioned"; resolving a cited
    deliverable against the filesystem instead of git is a measured way to grade
    a live row stale.

The probe results are the quotable surface. Evidence that is not traceable to
this bundle or to the row itself is evidence the auditor cannot check.

DETERMINISM AND AUDIT
=====================
temperature 0 / greedy wherever the API takes it, `seed` when supported. Every
returned dict carries `provenance.model` and `provenance.prompt_sha256`, so a
verdict recorded on the bus months from now can be re-derived: same prompt hash
plus same model id means the same decision was put to the same judge.

CLI
===
    premise_screener.py --task-id repl-turn-efficiency--013-L120
    premise_screener.py --row-json '{"task_text": "..."}'
    premise_screener.py --task-id X --offline      # force the no-model path
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

SCREENER_VERSION = "1"

REPO_ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = REPO_ROOT / "coordination" / "evals" / "examples" / "premise_screener.md"

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The cheap mechanical half. Imported, never reimplemented (P2-2 requirement).
# A hard failure here must not take the module down at import time: the screener
# still has to be able to answer "unknown" cleanly on a broken host.
try:  # pragma: no cover - exercised only on a broken checkout
    import backlog_row_check as brc

    _BRC_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # pragma: no cover
    brc = None  # type: ignore[assignment]
    _BRC_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"


# --------------------------------------------------------------- the ladder

#: The forced choice. There is no fourth value, and `_coerce_verdict` is the
#: only function permitted to mint one of these.
VERDICTS = ("still-needed", "stale", "unknown")

STILL_NEEDED, STALE, UNKNOWN = VERDICTS

#: Aliases the model plausibly emits for each rung. The pack and the handoff
#: spell the third rung `UNKNOWN`; the runner contract spells it `unknown`.
#: Case is normalised, so both are the same rung — but a verdict this table
#: does not know is UNKNOWN, never a guess.
_VERDICT_ALIASES = {
    "still-needed": STILL_NEEDED,
    "still needed": STILL_NEEDED,
    "still_needed": STILL_NEEDED,
    "stillneeded": STILL_NEEDED,
    "needed": STILL_NEEDED,
    "stale": STALE,
    "unknown": UNKNOWN,
}

#: An "evidence" string shorter than this is not a quote from an artifact, it is
#: a shrug. Deliberately small: the job of this floor is to catch "", "n/a",
#: "none", "stale" and "see above", not to police quote style.
_MIN_EVIDENCE_CHARS = 12

_EVIDENCE_NULLS = {
    "", "n/a", "na", "none", "null", "nil", "-", "--", "unknown", "stale",
    "still-needed", "still needed", "no evidence", "see above", "see below",
    "not applicable", "not available", "tbd", "todo", "?",
}


class PremiseScreenerError(RuntimeError):
    """Raised only inside this module; never escapes `screen_premise`."""


# ------------------------------------------------------------ row accessors
#
# The task TEXT is the identity; `file.md:LINE` is only a hint. That is a
# standing project rule and the pack's first procedural step, so the accessors
# below prefer text everywhere and treat every pointer as advisory.

_TEXT_KEYS = ("task_text", "presented", "text", "row", "body", "title")
_HINT_KEYS = ("spec_ref", "source_hint", "row_ref", "ref", "source", "anchor")


def row_text(row: dict) -> str:
    """The row's identity string, in preference order."""
    for key in _TEXT_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    # Queue rows carry the bundle one level down under `input` (the eval fixture
    # shape); accept it so a fixture can be screened without reshaping.
    nested = row.get("input")
    if isinstance(nested, dict):
        return row_text(nested)
    return ""


def row_hint(row: dict) -> str:
    for key in _HINT_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    nested = row.get("input")
    if isinstance(nested, dict):
        return row_hint(nested)
    return ""


def row_context(row: dict) -> str:
    parts = []
    for key in ("asserted_state", "context", "notes", "gating", "status"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{key}: {value.strip()}")
    nested = row.get("input")
    if isinstance(nested, dict):
        nested_ctx = row_context(nested)
        if nested_ctx:
            parts.append(nested_ctx)
    return "\n".join(parts)


# ------------------------------------------------------- mechanical screen


def _hint_path_line(hint: str) -> tuple[Optional[Path], Optional[int]]:
    """Parse `file.md:120` / `handoffs/active/file.md#L120` into (path, line).

    Advisory ONLY. The caller must never grade on this — it is used to
    disambiguate multiple text matches, which is the one job a rotted anchor can
    still do honestly.
    """
    if not hint:
        return None, None
    m = re.match(r"^(.*?\.md)(?:[:#]L?(\d+))?\s*$", hint.strip())
    if not m:
        return None, None
    raw, lineno = m.group(1), m.group(2)
    candidate = Path(raw)
    if not candidate.is_absolute():
        for base in (REPO_ROOT, REPO_ROOT / "handoffs" / "active"):
            if (base / candidate).exists():
                candidate = base / candidate
                break
    return candidate, (int(lineno) if lineno else None)


def mechanical_screen(row: dict) -> dict:
    """Run `backlog_row_check.py` over the row. Never calls a model.

    Returns a dict with a `proves_stale` boolean. TRUE means, and only ever
    means, that the row's own checkbox is closed. Everything else is context for
    the prompt.
    """
    text = row_text(row)
    result: dict[str, Any] = {
        "available": brc is not None,
        "import_error": _BRC_IMPORT_ERROR,
        "resolved": False,
        "proves_stale": False,
        "hits": 0,
        "box": None,
        "state": None,
        "heading": None,
        "path": None,
        "lineno": None,
        "classify_exit": None,
        "classify_reasons": [],
        "children": [],
        "note": None,
    }
    if brc is None:
        result["note"] = (
            "backlog_row_check.py could not be imported, so no mechanical screen ran"
        )
        return result
    if not text:
        result["note"] = "row carries no task text, so it cannot be resolved by identity"
        return result

    try:
        hits = brc.find_by_text(text)
    except Exception as exc:
        result["note"] = f"find_by_text failed: {type(exc).__name__}: {exc}"
        return result

    result["hits"] = len(hits)
    if not hits:
        # NOT stale. See the module docstring: absence has at least three
        # explanations and the standing rule forbids asserting one from a single
        # search key. State it and let the model weigh it.
        result["note"] = (
            "the row's task text matches NO checkbox in handoffs/active/. That is "
            "consistent with the row having been completed and deleted, but equally "
            "with a row sourced from outside handoffs/active/ or with a search key "
            "that missed. Not treated as proof of anything."
        )
        return result

    hint_path, hint_line = _hint_path_line(row_hint(row))
    chosen = hits[0]
    if len(hits) > 1 and hint_path is not None:
        for hit in hits:
            if hit[0].name == hint_path.name and (hint_line is None or hit[1] == hint_line):
                chosen = hit
                break

    path, lineno, state, body, head = chosen
    result.update({
        "resolved": True,
        "path": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
        "lineno": lineno,
        "state": "closed" if state == "x" else "open",
        "box": body,
        "heading": head,
    })

    try:
        result["children"] = [
            {"lineno": n, "state": "closed" if st == "x" else "open", "text": b}
            for n, st, b in brc.child_boxes(path, lineno)
        ][:12]
    except Exception as exc:
        result["children_error"] = f"{type(exc).__name__}: {exc}"

    try:
        exit_code, reasons = brc.classify(path, lineno, state, body, head)
        result["classify_exit"] = exit_code
        result["classify_reasons"] = list(reasons)
    except Exception as exc:
        result["classify_error"] = f"{type(exc).__name__}: {exc}"

    if state == "x":
        # The ONE mechanically decisive signal. The dashboard counts checkbox
        # state and nothing else; a closed box is the artifact saying done.
        result["proves_stale"] = True
        result["note"] = (
            f"the row's own checkbox at {result['path']}:{lineno} is `- [x]` (CLOSED)"
        )
    elif len(hits) > 1:
        result["note"] = (
            f"{len(hits)} checkboxes match this task text; the source hint was used to "
            f"pick one. Ambiguity is itself a reason not to grade mechanically."
        )
    return result


# --------------------------------------------------------- artifact probes
#
# The pack's worked examples all turn on a probe, not on a judgement about
# whether the work "sounds done". These reproduce the two cheapest and most
# discriminative of them for every path the row names.

_PATH_TOKEN = re.compile(r"`([^`\n]{2,180})`")
_BARE_PATH = re.compile(r"(?<![\w`/])((?:[\w.\-]+/){1,6}[\w.\-]+\.[A-Za-z0-9]{1,6})")
_MAX_PROBES = 12


def _candidate_paths(text: str) -> list[str]:
    seen: list[str] = []

    def add(token: str) -> None:
        token = token.strip().strip(",;.")
        if not token or token in seen:
            return
        if " " in token or token.startswith("-"):
            return
        # A bare filename with no separator is too ambiguous to probe usefully;
        # a directory reference (trailing /) is fine.
        if "/" not in token and "." not in token:
            return
        seen.append(token)

    for m in _PATH_TOKEN.finditer(text):
        add(m.group(1))
    for m in _BARE_PATH.finditer(text):
        add(m.group(1))
    return seen[:_MAX_PROBES]


def _git_tracked(paths: Iterable[str], timeout_s: float = 10.0) -> set[str]:
    """Which of `paths` are tracked in git. Empty set on any failure.

    X1 in the example pack: an untracked file is byte-identical on disk to a
    committed one and satisfies none of "versioned". Grading a deliverable
    against the filesystem instead of git is how a live row gets called stale.
    """
    paths = [p for p in paths]
    if not paths:
        return set()
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--", *paths],
            capture_output=True, timeout=timeout_s, check=False,
        )
    except Exception:
        return set()
    if proc.returncode != 0:
        return set()
    out = proc.stdout.decode("utf-8", "replace")
    return {chunk for chunk in out.split("\0") if chunk}


def probe_artifacts(text: str) -> list[dict]:
    """Cheap, bounded filesystem+git probes for every path the row names."""
    candidates = _candidate_paths(text)
    if not candidates:
        return []
    tracked = _git_tracked(candidates)
    probes: list[dict] = []
    for token in candidates:
        p = Path(token)
        if not p.is_absolute():
            p = REPO_ROOT / token
        record: dict[str, Any] = {"path": token}
        try:
            is_symlink = p.is_symlink()
            exists = p.exists()
            record["exists"] = bool(exists or is_symlink)
            record["symlink"] = bool(is_symlink)
            if is_symlink:
                try:
                    record["symlink_target"] = os.readlink(p)
                except OSError:
                    record["symlink_target"] = "<unreadable>"
            if exists and p.is_dir():
                record["kind"] = "directory"
            elif exists:
                record["kind"] = "file"
                try:
                    record["size_bytes"] = p.stat().st_size
                except OSError:
                    pass
            else:
                record["kind"] = "absent"
        except OSError as exc:
            record["kind"] = "unreadable"
            record["error"] = str(exc)
        # `tracked` holds repo-relative paths exactly as git prints them.
        record["git_tracked"] = any(
            t == token or t.endswith("/" + token.lstrip("./")) for t in tracked
        )
        probes.append(record)
    return probes


# ----------------------------------------------------------- example pack

_BUILTIN_PACK = """\
# Example pack — `premise_screener` (BUILT-IN FALLBACK)

This is the compressed in-code fallback. The authoritative pack is
`coordination/evals/examples/premise_screener.md`; it was not readable, so these
four examples stand in. They are the discriminative minimum.

## The procedure

1. The row's TASK TEXT is the identity. A `file.md:LINE` pointer is a hint; if
   text and pointer disagree, the text wins.
2. Enumerate EVERY conjunct. A row with three asks has three premises.
3. For each, name the probe that would settle it, and read the probe's result in
   the evidence bundle.
4. `stale` only if EVERY conjunct is dead. `still-needed` if any survives.
   `UNKNOWN` if the premise's subject is not something an artifact can settle.

## POSITIVE — `still-needed`

**Row:** "Bus runtime off-tree: `queue.jsonl` … move to `/mnt/raid0/llm/bus-runtime/`."
**Probe:** is `coordination/session-bus/queue.jsonl` a symlink? Regular file; the
target directory does not exist.
**Verdict:** `still-needed`. Evidence: "queue.jsonl — test -L reports REGULAR_FILE."
*Teaches:* a premise asserting a filesystem shape is decidable in one probe.

## NEGATIVE — `stale`

**Row:** "`STALE_SRC_SKEW_S=5` (`bus_supervisor.sh:362`) exists because …"
**Probe:** read the cited line. `grep` HITS — at line 334, inside the comment
"THE MTIME PREDICATE IS GONE ON PURPOSE … All three are deleted." Line 362 now
holds something else entirely.
**Verdict:** `stale`. *Teaches:* a grep hit is NOT a live identifier — the token
survived in the comment documenting its removal, so presence-grep inverts the
answer. Read what the line says.

## NEAR-MISS — looks `stale`, is `still-needed`

**Row:** "Copy the plan of record into `docs/design/plan.html` … so the plan of
record is in-repo and VERSIONED."
**Looks:** stale — the file is right there on disk.
**Probe:** `git ls-files --error-unmatch docs/design/plan.html` FAILS. Untracked.
**Verdict:** `still-needed`. *Teaches:* resolve cited deliverables against GIT,
not the filesystem, and choose the probe that tests the row's stated PURPOSE.
Second lesson of the same class: PARTIAL satisfaction is not stale — a screener
that stops at the first satisfied clause destroys the surviving work.

## `UNKNOWN`

**Row:** "Verify the SHA deploy-marker predicate is what the RUNNING supervisor
executes (`ps -o lstart` vs commit time); restart if stale."
**Looks:** stale — the predicate is plainly present in the source.
**But:** the row does not ask what the SOURCE contains. It asks what a PROCESS
is executing, and no artifact in the repo records a live process's loaded code.
**Verdict:** `UNKNOWN` → park the row, route a runtime-observation task.
*Teaches:* abundant evidence that is OFF-TARGET is not evidence. When the
premise's subject is runtime state, a confident label is the failure mode.

## Class balance

The two measured fact-check rounds found roughly HALF of screened rows already
satisfied (4 of 8, then 7 of 11). This pack is skewed toward `still-needed` for
brevity; do not read it as a prior.
"""


def load_example_pack(pack_path: Optional[Path] = None) -> tuple[str, dict]:
    """Load the few-shot pack. Falls back to the built-in and SAYS SO.

    The fallback is logged to stderr and recorded in `provenance.pack.builtin`
    because a screener silently running on a degraded pack is a quiet quality
    regression, and the whole point of provenance is that a verdict can be
    re-derived later from what actually went into it.
    """
    path = Path(pack_path) if pack_path else PACK_PATH
    meta: dict[str, Any] = {"path": str(path), "builtin": False}
    try:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise OSError("pack file is empty")
    except OSError as exc:
        text = _BUILTIN_PACK
        meta.update({"builtin": True, "fallback_reason": f"{type(exc).__name__}: {exc}"})
        print(
            f"premise_screener: example pack {path} unreadable ({exc}); "
            f"FELL BACK to the built-in pack. Verdicts from this run are recorded "
            f"with provenance.pack.builtin=true.",
            file=sys.stderr,
        )
    meta["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    meta["chars"] = len(text)
    return text, meta


# ---------------------------------------------------------------- prompting

_SYSTEM = """\
You screen backlog rows for a code-and-research repository. For ONE row you \
decide whether its premise is STILL TRUE in the world, or whether reality has \
already satisfied it.

You are the judgment half of a pair. A mechanical checker has already proved the \
row is WELL-FORMED; it cannot know whether the work is still NEEDED. That is \
your only question.

You output exactly one JSON object and nothing else:

  {"verdict": "still-needed"|"stale"|"unknown",
   "evidence": "<a verbatim quote from the evidence bundle or the row>",
   "reason": "<one sentence>"}

RULES OF THE LADDER
  - "still-needed": at least one conjunct of the row's premise is still true.
  - "stale":        EVERY conjunct is already satisfied in the world.
  - "unknown":      the premise's subject is not something the bundle can settle
                    (e.g. it is about a running process, an operator's intent, or
                    an artifact nobody probed). UNKNOWN is a correct, useful
                    answer. It is NOT a hedge and it is NOT "probably fine".

  - EVIDENCE IS MANDATORY. `evidence` must be a QUOTE — a line from the bundle,
    a probe result, a checkbox, a path — that a reader could go check. If you
    have no quote, your verdict is "unknown" and you say so in `reason`.
    Never put your verdict, or a restatement of it, in `evidence`.
  - Partial satisfaction is NOT stale. Enumerate the conjuncts.
  - A grep hit is not a live identifier. An untracked file is not a versioned one.
  - Prefer "unknown" over a confident label the bundle does not support.
"""

_OUTPUT_REMINDER = """\
Answer for the ROW UNDER SCREEN only. Output the single JSON object, no prose \
before or after, no code fence.\
"""


def build_bundle(row: dict, mech: dict) -> dict:
    """The evidence bundle exactly as the model will see it."""
    text = row_text(row)
    return {
        "task_id": row.get("task_id"),
        "task_text": text,
        "source_hint": row_hint(row),
        "context": row_context(row),
        "mechanical_check": {
            "resolved": mech.get("resolved"),
            "matches_in_handoffs_active": mech.get("hits"),
            "box_state": mech.get("state"),
            "box_at": (
                f"{mech.get('path')}:{mech.get('lineno')}" if mech.get("resolved") else None
            ),
            "box_text": mech.get("box"),
            "section_heading": mech.get("heading"),
            "child_boxes": mech.get("children"),
            "dispatchability_reasons": mech.get("classify_reasons"),
            "note": mech.get("note"),
        },
        "artifact_probes": probe_artifacts(text),
    }


def build_prompt(bundle: dict, pack_text: str) -> str:
    return (
        f"{_SYSTEM}\n"
        f"----- WORKED EXAMPLES (these are your calibration; read them) -----\n"
        f"{pack_text}\n"
        f"----- END WORKED EXAMPLES -----\n\n"
        f"----- ROW UNDER SCREEN (evidence bundle, JSON) -----\n"
        f"{json.dumps(bundle, indent=2, ensure_ascii=False, default=str)}\n"
        f"----- END ROW UNDER SCREEN -----\n\n"
        f"{_OUTPUT_REMINDER}\n"
    )


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


# ------------------------------------------------------------ model access
#
# HOW THIS REPO ALREADY TALKS TO A LOCAL MODEL — surveyed 2026-08-16, not guessed.
#
# There is no importable shared client class. Everything in the tree reaches a
# model through one of three surfaces, all of which are the SAME HTTP contract:
#
#   * `repos/epyc-orchestrator/src/api/routes/openai_compat.py` — the
#     orchestrator (uvicorn :8000) serving `POST /v1/chat/completions`. The
#     `model` field maps to an orchestrator ROLE; `"orchestrator"` means
#     auto-route. It forwards `temperature` and `seed` (openai_compat.py:326-329),
#     so it is the only surface on which requirement 6 (greedy, reproducible) can
#     actually be met.
#   * `repos/epyc-orchestrator/src/mcp_server.py::_post_chat` — the smallest
#     existing Python client in the repo (stdlib urllib, no deps), posting to
#     `POST {ORCHESTRATOR_API_URL}/chat`. REUSED BELOW as the fallback transport.
#     Its payload has no temperature knob, so a verdict taken through it is
#     recorded with `deterministic: false`.
#   * llama.cpp `llama-server` directly, per-role, on the manifest port map
#     (`worker_general` 8072, `frontdoor` 8070). Same OpenAI shape.
#
# So: ONE code path (`/v1/chat/completions`) covers the orchestrator and every
# llama-server, and the orchestrator's own `_post_chat` is reused when only the
# non-OpenAI `/chat` route answers.
#
# Role choice: `worker_general` — tier C, the cheap tier (`src/roles.py`). There
# is no "screener" role and inventing one is a registry change, not a screener
# change. `force_mode: direct` skips REPL/delegation.
#
# EVERY probe happens at CALL time, never at import. A host with no model running
# must still be able to import this module — it is a preflight inside
# `worker_runner.py`, and an ImportError there takes the runner down.

#: Tier-C role for a cheap point call. Overridable, but not with a new role.
SCREENER_ROLE = os.environ.get("PREMISE_SCREENER_ROLE", "worker_general")

_ORCHESTRATOR_BASE = os.environ.get("ORCHESTRATOR_API_URL", "http://localhost:8000")

_DEFAULT_ENDPOINTS = (
    f"{_ORCHESTRATOR_BASE.rstrip('/')}/v1",  # orchestrator :8000, role-routed
    "http://127.0.0.1:8072/v1",              # llama-server: worker_general (tier C)
    "http://127.0.0.1:8070/v1",              # llama-server: frontdoor (tier A)
    "http://127.0.0.1:8080/v1",              # llama-server default port
)


def _endpoints() -> tuple[str, ...]:
    override = os.environ.get("PREMISE_SCREENER_BASE_URL") or os.environ.get(
        "OPENAI_BASE_URL"
    )
    if override:
        return (override.rstrip("/"),)
    return _DEFAULT_ENDPOINTS


def _http_json(url: str, payload: Optional[dict], timeout_s: float) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if data is not None else "GET",
    )
    token = os.environ.get("PREMISE_SCREENER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def discover_endpoint(timeout_s: float = 3.0) -> Optional[tuple[str, str]]:
    """(base_url, model_id) for the first reachable OpenAI-compatible server.

    Returns None when nothing answers. None is not an error here — it is the
    offline path, and it produces "unknown".
    """
    preferred = os.environ.get("PREMISE_SCREENER_MODEL")
    for base in _endpoints():
        try:
            body = _http_json(f"{base}/models", None, timeout_s)
        except (urllib.error.URLError, OSError, ValueError, TimeoutError):
            continue
        ids = [
            m.get("id")
            for m in (body or {}).get("data", [])
            if isinstance(m, dict) and m.get("id")
        ]
        if preferred:
            # A pinned id wins even if /models does not advertise it — the
            # orchestrator maps `model` to a ROLE, so its id set and the set of
            # accepted values are not the same thing.
            return base, preferred
        if SCREENER_ROLE in ids:
            return base, SCREENER_ROLE
        if not ids:
            continue
        return base, ids[0]
    if preferred and os.environ.get("PREMISE_SCREENER_BASE_URL"):
        # An explicitly pinned model at an explicitly pinned base URL skips
        # discovery entirely — some servers do not expose /models at all.
        return os.environ["PREMISE_SCREENER_BASE_URL"].rstrip("/"), preferred
    return None


class HTTPChatClient:
    """Minimal OpenAI-compatible chat client. Greedy by construction.

    `temperature=0`, `top_p=1` and a fixed `seed` are sent on every call so two
    runs of the same prompt against the same server are comparable. Servers that
    ignore `seed` still get temperature 0, which is the part that matters.
    """

    deterministic = True

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def __call__(self, prompt: str, *, timeout_s: float = 90.0) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "top_p": 1,
            "seed": 42,
            "max_tokens": 600,
            "stream": False,
        }
        body = _http_json(f"{self.base_url}/chat/completions", payload, timeout_s)
        choices = body.get("choices") or []
        if not choices:
            raise PremiseScreenerError(f"no choices in response: {str(body)[:200]}")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise PremiseScreenerError("empty content in model response")
        return content


ORCHESTRATOR_SRC = Path("/workspace/repos/epyc-orchestrator")


class OrchestratorChatClient:
    """Fallback that REUSES the orchestrator's own `_post_chat` (mcp_server.py).

    Used only when the OpenAI-compatible route is unreachable but the
    orchestrator's plain `/chat` route answers. That payload has no temperature
    or seed field, so this path is NOT greedy-deterministic and says so in
    `deterministic`; the caller records it in provenance rather than pretending
    the verdict is reproducible.

    The real function is imported when the orchestrator package is importable;
    otherwise the identical stdlib POST is issued directly, because the contract
    is the payload, not the import.
    """

    deterministic = False

    def __init__(self, base_url: str, role: str = SCREENER_ROLE):
        self.base_url = base_url.rstrip("/")
        self.role = role
        self.model = role
        self._post = None
        try:
            if str(ORCHESTRATOR_SRC) not in sys.path:
                sys.path.append(str(ORCHESTRATOR_SRC))
            from src.mcp_server import _post_chat  # type: ignore

            self._post = _post_chat
            self.via = "src.mcp_server._post_chat"
        except Exception:
            self.via = "stdlib POST (same payload as src.mcp_server._post_chat)"

    def __call__(self, prompt: str, *, timeout_s: float = 90.0) -> str:
        payload = {
            "prompt": prompt,
            "context": "",
            "real_mode": True,
            "mock_mode": False,
            "force_role": self.role,
            "force_mode": "direct",
            "timeout_s": int(timeout_s),
        }
        if self._post is not None:
            body = self._post(payload)
        else:
            body = _http_json(f"{self.base_url}/chat", payload, timeout_s + 5)
        if not isinstance(body, dict):
            raise PremiseScreenerError(f"unexpected /chat response: {str(body)[:200]}")
        if body.get("error"):
            raise PremiseScreenerError(str(body["error"])[:300])
        answer = body.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise PremiseScreenerError(f"no answer in /chat response: {str(body)[:200]}")
        return answer


def _chat_route_alive(base: str, timeout_s: float) -> bool:
    try:
        _http_json(f"{base.rstrip('/')}/health", None, timeout_s)
        return True
    except Exception:
        return False


def resolve_client(
    *, model: Optional[str] = None, timeout_s: float = 3.0
) -> tuple[Optional[Callable[..., str]], dict]:
    """Find a usable model client, or return (None, why-not). Never raises.

    Preference order, and the reason for it:
      1. OpenAI-compatible `/v1/chat/completions` — the only surface that honours
         temperature 0 and `seed`, so the only one on which a verdict is
         reproducible from its recorded prompt hash.
      2. The orchestrator's own `/chat` via `_post_chat` — existing client,
         reused, but non-deterministic; flagged as such.
      3. Nothing. Which is "unknown", not "fine".
    """
    meta: dict[str, Any] = {"kind": None, "base_url": None, "model": None,
                            "deterministic": None}
    try:
        found = discover_endpoint(timeout_s=timeout_s)
    except Exception as exc:  # pragma: no cover - defensive
        meta["error"] = f"{type(exc).__name__}: {exc}"
        return None, meta
    if found:
        base, discovered = found
        chosen = model or discovered
        meta.update({"kind": "http-openai-compatible", "base_url": base,
                     "model": chosen, "deterministic": True})
        return HTTPChatClient(base, chosen), meta

    if _chat_route_alive(_ORCHESTRATOR_BASE, timeout_s):
        client = OrchestratorChatClient(_ORCHESTRATOR_BASE, model or SCREENER_ROLE)
        meta.update({"kind": "orchestrator-/chat", "base_url": _ORCHESTRATOR_BASE,
                     "model": client.model, "deterministic": False,
                     "via": client.via,
                     "note": "the /chat payload has no temperature or seed field, "
                             "so this verdict is NOT reproducible from its prompt hash"})
        return client, meta

    cli = _resolve_harness_cli(timeout_s=timeout_s)
    if cli is not None:
        client, name = cli
        meta.update({"kind": "harness-cli", "base_url": name, "model": name,
                     "deterministic": False,
                     "note": "headless agent CLI; no temperature/seed knob, so this "
                             "verdict is NOT reproducible from its prompt hash"})
        return client, meta

    meta["error"] = (
        "no model server answered: tried OpenAI-compatible /v1 at "
        + ", ".join(_endpoints())
        + f", the orchestrator /chat route at {_ORCHESTRATOR_BASE}"
        + ", and no headless agent CLI was usable"
    )
    return None, meta


class HarnessCLIClient:
    """Last-resort client: a headless agent CLI already installed on this host.

    WHY THIS TIER EXISTS. Measured 2026-08-16: every model endpoint on this box
    was refused — :8000, :8070, :8072, :8080, no llama-server, no uvicorn. With
    only the HTTP tiers, EVERY mechanically-open row screens `unknown`, and
    since unknown correctly means do-not-dispatch, the screener would have
    blocked the entire worker pool whenever the serving stack was down. A
    screener that cannot run when the GPU is busy is not a screener.

    It is deliberately LAST. It cannot honour temperature/seed, so its verdicts
    are recorded non-deterministic, and it costs a full agent invocation rather
    than a token-cheap completion.
    """

    def __init__(self, exe: str, args: list[str]):
        self.exe, self.args = exe, args

    def __call__(self, prompt: str, timeout_s: float = 120.0) -> str:
        proc = subprocess.run([self.exe, *self.args], input=prompt,
                              capture_output=True, text=True, timeout=timeout_s)
        if proc.returncode != 0:
            raise PremiseScreenerError(
                f"{self.exe} exited {proc.returncode}: {(proc.stderr or '')[:300]}")
        out = (proc.stdout or "").strip()
        if not out:
            raise PremiseScreenerError(f"{self.exe} produced no output")
        return out


def _resolve_harness_cli(*, timeout_s: float = 3.0):
    """Return (client, name) for an installed headless agent CLI, or None."""
    for exe, args in (("claude", ["-p"]), ("codex", ["exec", "-"])):
        path = shutil.which(exe)
        if not path:
            continue
        return HarnessCLIClient(path, args), exe
    return None


# ------------------------------------------------------------ output gates


def _coerce_verdict(raw: Any) -> str:
    """The ONLY place a verdict is minted. Anything unrecognised is UNKNOWN.

    This is what makes the enum unfalsifiable: there is no other assignment to
    `result["verdict"]` in this module that is not one of the three constants.
    """
    if not isinstance(raw, str):
        return UNKNOWN
    key = raw.strip().strip("`\"'.").lower()
    return _VERDICT_ALIASES.get(key, UNKNOWN)


def _usable_evidence(raw: Any) -> Optional[str]:
    """A quote, or None.

    None means "this model returned no evidence", which downgrades ANY verdict
    to unknown. Requirement 2 of the module contract, and the mutation target of
    the test suite: delete this gate and an evidence-less "stale" is accepted,
    which is the failure this whole file exists to prevent.
    """
    if not isinstance(raw, str):
        return None
    quote = raw.strip().strip("`")
    if quote.lower() in _EVIDENCE_NULLS:
        return None
    if len(quote) < _MIN_EVIDENCE_CHARS:
        return None
    # "evidence: stale because the row is stale" is a restatement, not a quote.
    if _coerce_verdict(quote) != UNKNOWN and len(quote) < 40:
        return None
    return quote


def _extract_json(text: str) -> Optional[dict]:
    """First balanced JSON object in the response. Tolerant of fences and prose."""
    if not isinstance(text, str):
        return None
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
    candidates.append(text)
    for chunk in candidates:
        depth = 0
        start = -1
        for i, ch in enumerate(chunk):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        parsed = json.loads(chunk[start:i + 1])
                    except ValueError:
                        start = -1
                        continue
                    if isinstance(parsed, dict):
                        return parsed
                    start = -1
    return None


def _unknown(reason: str, provenance: dict, evidence: str = "") -> dict:
    return {
        "verdict": UNKNOWN,
        "evidence": evidence,
        "reason": reason,
        "provenance": provenance,
    }


# ------------------------------------------------------------- the contract


def screen_premise(
    row: dict,
    *,
    model: Optional[str] = None,
    timeout_s: float = 90.0,
    offline: bool = False,
    client: Optional[Callable[..., str]] = None,
    pack_path: Optional[Path] = None,
    discovery_timeout_s: float = 3.0,
) -> dict:
    """Is this row's premise still true? -> verdict / evidence / reason / provenance.

    The one-argument call is the contract `worker_runner.py` is built against.
    Every keyword has a default and none of them is required.

    NEVER RAISES. Every failure mode — no model, timeout, garbage output,
    unreadable artifact, a bug in this function — returns "unknown", because the
    caller's response to "unknown" (park the row, route a fix task) is the safe
    action and the caller's response to a wrong "still-needed" is to burn a
    worker on satisfied work.
    """
    started = datetime.now(timezone.utc).isoformat()
    provenance: dict[str, Any] = {
        "screener_version": SCREENER_VERSION,
        "screened_at": started,
        "model": None,
        "prompt_sha256": None,
        "llm_calls": 0,
        "client": None,
        "pack": None,
        "mechanical": None,
    }

    if not isinstance(row, dict):
        return _unknown(
            f"row is not a dict ({type(row).__name__}), so nothing could be screened.",
            provenance,
        )

    # ---- 1. the cheap mechanical check, always, before any token is spent
    try:
        mech = mechanical_screen(row)
    except Exception as exc:  # pragma: no cover - mechanical_screen self-guards
        mech = {"available": False, "proves_stale": False,
                "note": f"mechanical screen crashed: {type(exc).__name__}: {exc}"}
    provenance["mechanical"] = mech

    if mech.get("proves_stale"):
        # ZERO model calls. The artifact already answered.
        return {
            "verdict": STALE,
            "evidence": (mech.get("box") or "")[:400]
            or f"closed checkbox at {mech.get('path')}:{mech.get('lineno')}",
            "reason": (
                f"Mechanically proven closed: {mech.get('note')} — no model call was "
                f"needed or made."
            ),
            "provenance": {**provenance, "decided_by": "mechanical", "llm_calls": 0},
        }

    text = row_text(row)
    if not text:
        return _unknown(
            "The row carries no task text, and the task text is the identity — "
            "nothing could be screened.",
            {**provenance, "decided_by": "mechanical"},
        )

    # ---- 2. build the bundle and the prompt (needed even offline, for the hash)
    try:
        pack_text, pack_meta = load_example_pack(pack_path)
        provenance["pack"] = pack_meta
        bundle = build_bundle(row, mech)
        prompt = build_prompt(bundle, pack_text)
        provenance["prompt_sha256"] = prompt_hash(prompt)
    except Exception as exc:
        return _unknown(
            f"Could not build the screening prompt ({type(exc).__name__}: {exc}), "
            f"so no judgment was made.",
            provenance,
        )

    # ---- 3. resolve a model
    if offline:
        provenance["client"] = {"kind": None, "error": "offline=True requested by caller"}
        return _unknown(
            "Offline mode: no model was consulted, so the premise is undetermined. "
            "Treat as do-not-dispatch and route a fix task.",
            provenance,
        )
    if client is None:
        client, client_meta = resolve_client(model=model, timeout_s=discovery_timeout_s)
        provenance["client"] = client_meta
        provenance["model"] = client_meta.get("model")
        if client is None:
            return _unknown(
                f"No model was reachable ({client_meta.get('error')}), so the premise "
                f"is undetermined — NOT fine. Treat as do-not-dispatch and route a "
                f"fix task.",
                provenance,
            )
    else:
        provenance["client"] = {"kind": "injected", "repr": type(client).__name__}
        provenance["model"] = model or getattr(client, "model", None) or "injected"

    # ---- 4. the point call
    try:
        raw = client(prompt, timeout_s=timeout_s)
        provenance["llm_calls"] = 1
    except TypeError:
        # A client that does not accept the timeout kwarg is still usable.
        try:
            raw = client(prompt)
            provenance["llm_calls"] = 1
        except Exception as exc:
            return _unknown(
                f"The model call failed ({type(exc).__name__}: {exc}); the premise is "
                f"undetermined. Do not dispatch; route a fix task.",
                provenance,
            )
    except Exception as exc:
        return _unknown(
            f"The model call failed ({type(exc).__name__}: {exc}); the premise is "
            f"undetermined. Do not dispatch; route a fix task.",
            provenance,
        )

    provenance["raw_response"] = (raw if isinstance(raw, str) else repr(raw))[:2000]

    # ---- 5. parse, then gate on the enum AND on evidence
    parsed = _extract_json(raw)
    if parsed is None:
        return _unknown(
            "The model returned no parseable JSON object, so no verdict was made.",
            provenance,
        )

    verdict = _coerce_verdict(parsed.get("verdict"))
    evidence = _usable_evidence(parsed.get("evidence"))
    reason = parsed.get("reason")
    reason = reason.strip() if isinstance(reason, str) and reason.strip() else ""

    if evidence is None:
        # MANDATORY EVIDENCE. A verdict without a quote is not a verdict.
        raw_verdict = parsed.get("verdict")
        return {
            "verdict": UNKNOWN,
            "evidence": "",
            "reason": (
                f"Downgraded to unknown: the model answered "
                f"{str(raw_verdict)[:40]!r} but supplied no usable evidence quote, and "
                f"an unevidenced verdict is never accepted."
                + (f" Its stated reason was: {reason[:200]}" if reason else "")
            ),
            "provenance": {
                **provenance,
                "downgraded_from": _coerce_verdict(raw_verdict),
                "downgrade_cause": "missing-or-unusable-evidence",
                "raw_evidence": str(parsed.get("evidence"))[:200],
            },
        }

    if verdict == UNKNOWN and _coerce_verdict(parsed.get("verdict")) == UNKNOWN:
        provenance.setdefault("raw_verdict", str(parsed.get("verdict"))[:80])

    return {
        "verdict": verdict,
        "evidence": evidence[:1000],
        "reason": reason or "(the model returned a verdict and evidence but no reason)",
        "provenance": {**provenance, "decided_by": "model"},
    }


# --------------------------------------------------------------------- CLI


def _load_row_from_queue(task_id: str) -> dict:
    """Read the row from the LIVE queue fold (latest record per task_id)."""
    import session_bus  # imported lazily: the CLI needs it, the library does not

    fold = session_bus.fold_queue(session_bus.get_bus_root())
    row = fold.get(task_id)
    if row is None:
        raise SystemExit(
            f"premise_screener: no task_id {task_id!r} in the queue fold "
            f"({len(fold)} tasks). The fold keys the LATEST row per task_id."
        )
    return row


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Screen a backlog row's PREMISE against the world "
                    "(still-needed | stale | unknown).",
        epilog="unknown is a verdict, not an error: it means do-not-dispatch "
               "plus a routed fix task.",
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--task-id", help="read the row from the live queue fold")
    src.add_argument("--row-json", help="a JSON object with at least task_text")
    ap.add_argument("--model", default=None, help="model id (default: server's first)")
    ap.add_argument("--timeout-s", type=float, default=90.0)
    ap.add_argument("--offline", action="store_true",
                    help="never call a model; always returns unknown")
    ap.add_argument("--pack", default=None, help="override the example-pack path")
    ap.add_argument("--compact", action="store_true", help="one-line JSON")
    args = ap.parse_args(argv)

    if args.task_id:
        row = _load_row_from_queue(args.task_id)
    else:
        try:
            row = json.loads(args.row_json)
        except ValueError as exc:
            raise SystemExit(f"premise_screener: --row-json is not valid JSON: {exc}")
        if not isinstance(row, dict):
            raise SystemExit("premise_screener: --row-json must be a JSON object")

    result = screen_premise(
        row,
        model=args.model,
        timeout_s=args.timeout_s,
        offline=args.offline,
        pack_path=Path(args.pack) if args.pack else None,
    )
    print(json.dumps(result, indent=None if args.compact else 2,
                     ensure_ascii=False, default=str))
    # Exit code mirrors the ladder so a shell caller can branch without jq:
    #   0 still-needed (dispatch) · 2 stale (park) · 3 unknown (park + fix task)
    return {STILL_NEEDED: 0, STALE: 2, UNKNOWN: 3}[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
