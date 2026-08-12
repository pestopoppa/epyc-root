#!/usr/bin/env python3
"""Scan a Bash command for the EXECUTION of a *derived copy* of a gated operator script.

Origin (2026-08-05, `handoffs/active/autopilot-continuous-optimization.md`): a C6
agent copied `artifacts/operator/apply_e8_quality_baseline_state.py`, patched the
fail-closed safety gate out of the copy as ``if False and autopilot_running()``, and
ran the copy. The gate at lines 854/873 refuses a production-state ``--attest`` /
``--recover`` while AutoPilot is live. Nothing structural stopped the copy, because
**the prohibition lived inside the very file being copied**.

THE LOAD-BEARING IDEA. No check written *inside* an operator apply script can survive
being copied — the copier owns the copy and deletes the check along with the gate. So
this guard does not look for the gate at all. It keys on DERIVATION: a file that
reproduces most of a protected original is refused execution unless it *is* the
protected original, at its canonical path. Ungated, re-gated or byte-identical, the
copy is refused either way — which is the only property that cannot be patched out.

THE PROTECTED SET IS DERIVED, NOT LISTED. An original is protected iff it lives under
a protected root AND carries a human-only gate marker (``--attest``, ``autopilot_running``,
``human-only``, …). A new gated operator script is covered the day it lands; nobody has
to remember to add a row. A literal restated at N sites is a rename hazard this repo has
already paid for (the de-FABLE rename shipped three dead operator commands).

SCOPED TO INVOCATIONS, NOT TEXT. Quoted runs, heredoc bodies and shell comments are
stripped before scanning, reusing ``pytest_worker_scan``'s helpers rather than
reimplementing them. Writing *about* copying an apply script — in a bus message, in an
incident report, in this docstring — must never be blocked. A guard that forbids its
own documentation is a failure this repo has paid for twice (C21, C47).

KNOWN SCOPE LIMITS, stated so a clean scan is not mistaken for containment:
  * A PreToolUse hook sees the command an AGENT TYPES. A daemon, a cron job, or a
    script that internally shells out to the copy is invisible to it. The enforcing
    layer for those is OS-level (separate uid / read-only mount), as the
    ``conceptual:`` block of ``coordination/session-bus/human_only_paths.yaml``
    already records for AutoKernel evaluator immutability.
  * A quoted or variable-expanded path (``python3 "$DIR/copy.py"``) is not visible,
    because quoted runs are blanked so that mentions stay legal. Same trade-off the
    pattern-kill guard makes.
  * A copy rewritten from scratch scores low and passes. That is deliberate: the
    threat modelled here is ``cp`` + ``sed``, which is minutes of work. Reimplementing
    the CAS/journal/attestation machinery is not a guard bypass, it is a new program.

Verdicts: ``derived-copy``, ``clean``.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pytest_worker_scan import _SEPARATORS, strip_heredocs, strip_quoted  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Roots whose gated scripts are canonical-path-only. Relative to REPO_ROOT unless absolute.
PROTECTED_ROOTS = (
    "artifacts/operator",
    "repos/epyc-orchestrator/scripts/autopilot",
)

# A file under a protected root is a protected ORIGINAL iff it carries one of these.
# These name the human-only apply/ratify contract, not any single gate, so deleting
# the AutoPilot gate from a copy does not deregister its original.
GATE_MARKERS = re.compile(
    r"autopilot_running|--attest\b|--recover\b|human-only|HUMAN-ONLY|human_only|"
    r"human-amendment-only|operator token|OPERATOR-ONLY",
)

SCRIPT_SUFFIXES = (".py", ".sh", ".bash", ".zsh")

# Command words after which a path operand is being RUN rather than read.
RUNNERS = frozenset(
    """python python3 python3.11 python3.12 python3.13 bash sh zsh dash ksh
       uv poetry pipenv nohup sudo time timeout env stdbuf setsid taskset
       numactl xargs source .""".split()
)

# Fraction of an original's distinctive lines that a candidate must reproduce.
# A `sed`-ungated copy scores ~0.99; renaming the gate and deleting it scores ~0.95;
# a 40%-excerpt scores 0.4 and is deliberately allowed (see the module docstring).
CONTAINMENT_THRESHOLD = 0.60

# An "original" with only a handful of distinctive lines would be reproduced by
# accident: containment is normalised by the ORIGINAL's size, so a 4-line original
# is 100%-contained in anything quoting it. Applied to originals ONLY. The mirror
# check on candidates was deleted after a mutation test found it could not change a
# verdict: a candidate needs >= 0.60 * |original| shared lines to trip at all, so a
# small candidate is already excluded by arithmetic. An unfalsifiable check is worse
# than no check — it reads as protection nobody can audit.
MIN_ORIGINAL_LINES = 25

_COMMENT = re.compile(r"(?:(?<=^)|(?<=\s))#[^\n]*")
_TRIM = "\"'`()[]{};,&<>|"


def strip_comments(text: str) -> str:
    return _COMMENT.sub(" ", text)


def distinctive_lines(text: str) -> frozenset[str]:
    """Normalised, comment-free lines — the fingerprint of a source file.

    Comments are dropped so that a copy which rewrites every comment (or strips them)
    still fingerprints as a copy; ``test_rewriting_every_comment_does_not_launder_a_copy``
    pins that. A minimum-line-length filter was tried and DELETED: it survived every
    mutant, and sweeping all 355 tracked repo scripts flagged 0 either way, because
    containment is normalised by the original's size and boilerplate like ``fi`` adds
    to the denominator as fast as it adds to the intersection. Shipping it would have
    been mechanism nobody could audit.
    """
    return frozenset(
        line
        for line in (raw.strip() for raw in text.splitlines())
        if line and not line.startswith("#")
    )


def protected_originals(roots: tuple[str, ...] = PROTECTED_ROOTS) -> dict[Path, frozenset[str]]:
    """Resolved path -> fingerprint, for every gated script under the protected roots."""
    found: dict[Path, frozenset[str]] = {}
    for root in roots:
        base = Path(root)
        if not base.is_absolute():
            base = REPO_ROOT / base
        if not base.is_dir():
            continue
        for path in sorted(base.iterdir()):
            if not path.is_file() or path.suffix not in SCRIPT_SUFFIXES:
                continue
            try:
                body = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not GATE_MARKERS.search(body):
                continue
            fingerprint = distinctive_lines(body)
            if len(fingerprint) >= MIN_ORIGINAL_LINES:
                found[path.resolve()] = fingerprint
    return found


def _tokens(segment: str) -> list[str]:
    return [t for t in segment.split() if t]


def candidate_scripts(segment: str) -> list[str]:
    """Path tokens in `segment` that are being EXECUTED, not merely named.

    `cp a.py b.py`, `diff a.py b.py` and `git show a.py` name paths without running
    them and yield nothing. `python3 a.py`, `./a.sh` and `timeout 5 bash a.sh` do.
    """
    tokens = _tokens(segment)
    if not tokens:
        return []
    cleaned = [t.strip(_TRIM) for t in tokens]
    looks_like_script = [
        bool(c) and not c.startswith("-") and c.endswith(SCRIPT_SUFFIXES)
        for c in cleaned
    ]
    runner_at = [i for i, c in enumerate(cleaned) if Path(c).name in RUNNERS]
    first_is_script = looks_like_script[0] and ("/" in cleaned[0] or cleaned[0].startswith("."))
    if not runner_at and not first_is_script:
        return []
    return [c for c, is_script in zip(cleaned, looks_like_script) if is_script]


def containment(candidate: frozenset[str], original: frozenset[str]) -> float:
    if not original:
        return 0.0
    return len(candidate & original) / len(original)


def derived_copies(
    command: str,
    originals: dict[Path, frozenset[str]] | None = None,
) -> list[tuple[str, Path, float]]:
    """(typed path, protected original it copies, containment) for each derived copy run."""
    if originals is not None and not originals:
        # A guard whose corpus is empty says `clean` for everything. Refuse to be that.
        raise RuntimeError(
            "operator-apply-copy guard was handed an EMPTY corpus of protected "
            "originals; refusing to report a verdict it never had the data to reach"
        )
    text = strip_comments(strip_quoted(strip_heredocs(command)))
    tokens = []
    seen: set[str] = set()
    for segment in _SEPARATORS.split(text):
        for token in candidate_scripts(segment):
            if token not in seen:
                seen.add(token)
                tokens.append(token)
    if not tokens:
        # The overwhelmingly common case. Return before paying for the corpus so the
        # hook adds nothing measurable to every Bash call in the repo.
        return []
    if originals is None:
        originals = protected_originals()
        if not originals:
            raise RuntimeError(
                "operator-apply-copy guard found NO protected originals under "
                f"{PROTECTED_ROOTS}; refusing to report a verdict from an empty corpus"
            )
    hits: list[tuple[str, Path, float]] = []
    for token in tokens:
        path = Path(token)
        if not path.is_absolute():
            path = REPO_ROOT / path
        try:
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in originals:
                continue  # the canonical original, at its canonical path
            body = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fingerprint = distinctive_lines(body)
        best = max(
            ((orig, containment(fingerprint, fp)) for orig, fp in originals.items()),
            key=lambda pair: pair[1],
        )
        if best[1] >= CONTAINMENT_THRESHOLD:
            hits.append((token, best[0], best[1]))
    return hits


def copy_execution_verdict(
    command: str, originals: dict[Path, frozenset[str]] | None = None
) -> str:
    """``derived-copy`` | ``clean`` for a whole Bash command string."""
    return "derived-copy" if derived_copies(command, originals) else "clean"


def main() -> int:
    """Read a command from stdin, or lint the FILES named on argv.

    Lint mode answers the containment question the incident had to answer by hand
    ("is there an ungated copy of an apply script anywhere?") — point it at a tree.
    Empty input never produces a verdict: a guard that reports `clean` for input it
    never read is worse than no guard (the defect `process_pattern_kill_scan.py`
    shipped and had to be repaired).
    """
    originals = protected_originals()
    if not originals:
        print("error: no protected originals found — refusing to emit a verdict", file=sys.stderr)
        return 2
    if sys.argv[1:2] == ["--explain"]:
        data = sys.stdin.read()
        if not data.strip():
            print("error: --explain needs a command on stdin", file=sys.stderr)
            return 2
        for typed, original, score in derived_copies(data, originals):
            print(f"  {typed}\n    reproduces {score:.0%} of {original}")
        return 0
    if sys.argv[1:]:
        rc = 0
        for name in sys.argv[1:]:
            path = Path(name)
            try:
                body = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                print(f"error: cannot read {name}: {exc}", file=sys.stderr)
                rc = 2
                continue
            if not body.strip():
                # No verdict for input that was never read — but a whole-tree sweep
                # must not be aborted by one empty file, or the sweep silently covers
                # a prefix and looks complete. Flag it and keep going.
                print(f"error: {name} is empty — refusing to emit a verdict", file=sys.stderr)
                rc = 2
                continue
            if path.resolve() in originals:
                print(f"canonical\t{name}")
                continue
            fingerprint = distinctive_lines(body)
            best_path, best_score = max(
                ((o, containment(fingerprint, fp)) for o, fp in originals.items()),
                key=lambda pair: pair[1],
            )
            if best_score >= CONTAINMENT_THRESHOLD:
                print(f"derived-copy\t{name}\t{best_score:.2f}\t{best_path}")
                rc = max(rc, 1)
            else:
                print(f"clean\t{name}")
        return rc
    data = sys.stdin.read()
    if not data.strip():
        print(
            "error: empty stdin and no path given — refusing to emit a verdict",
            file=sys.stderr,
        )
        return 2
    print(copy_execution_verdict(data, originals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
