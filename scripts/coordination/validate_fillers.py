#!/usr/bin/env python3
"""validate_fillers.py -- the grant-writer validator for the shared compute QUEUE (FILLERS.md).

PROPOSED 2026-10-21 (process change A of
/mnt/raid0/llm/tmp/inference-backlog-audit-20261021/REPORT.md section 4; format fixed by stage-3),
pending workspace-58 agreement to call it from the grant writer.  Read-only, stdlib only.

    validate_fillers.py [--file F] [--row ID] [--for-grant]

    --file F     default /mnt/raid0/llm/tmp/compute-flags/FILLERS.md
    --row ID     check only that row (exact filler-id)
    --for-grant  the row is about to be GRANTED: every violation is a REFUSAL (exit 2).
                 Requires --row.  Without --for-grant every violation is a WARNING (exit 0):
                 other owners' rows may still carry "-" or free-form values today.

Exit codes
    0  nothing refused (warnings may have been printed)
    2  refused: --for-grant and the row violates at least one rule
    3  malformed: unreadable file, no table header, header columns differ from the 18 expected,
       --row not found, --for-grant without --row, or (with --row) the row does not have exactly
       18 cells.  Rows other than the target that are malformed are WARNings in a full scan.

The table (one markdown table, a leading "| <id> |", no "|" inside a cell, 18 cells per row):

    filler-id | owner | launcher + PID | resources | min useful window | max private RAM |
    STOP file | status | class | duration | min window | DS41-class y/n | ready y/n | prior |
    decision | min_effect | substrate | notes

Rules (a cell value of "-" or empty means unfilled and violates the rule for its column)
    col 6         "peak host RAM GiB" (header may still read "max private RAM"): a number in GiB,
                  `48` or `48 GiB` (a leading ~ and decimals are allowed).  Definition (workspace-58,
                  2026-10-22): private/anon peak PLUS file-mapped weight bytes -- mapped weights count
                  even with mmap.  ram_admit.sh compares it with MemAvailable (margin 64 GiB).
                  Prose such as "~48 GB VRAM", a range, or "-" is a violation.
    status        first token in {ARMED, REGISTERED, NOT-ARMED, CANCELLED, COMPLETE}; trailing
                  prose after the token is a violation (keep the cell to the literal token --
                  launchers flip ARMED->COMPLETE with sed)
    class         in {filler, block-correctness, block-timing-pairable, block-timing-quiet}
    DS41-class    exactly y or n
    ready         exactly y or n
    substrate     in {cpu, gpu, either}
    prior         a path (an absolute path, possibly inside backticks or followed by a note), or
                  `none found (<who>, <date>)` (an ISO date must appear inside the parentheses);
                  prior_check.py's own `none (checked <ts>)` is also accepted
    decision      one non-empty line of at least 8 characters
    min_effect    an effect size containing a number (with its unit), exact-identity wording
                  (exact / identical / identity / zero), or `n/a (<reason>)` for rows with no effect
                  to detect (a build, a noise-floor measurement, ...)
    block-timing-quiet additionally (change C): `decision` names a champion / candidate /
                  baseline, AND `notes` or `prior` cites a floor file (a path or filename with
                  "floor" and a .json/.md/.jsonl/.txt extension, e.g. serving-floor.*.json).
CTC-Q-C (booking class is derived, D9 ack 2026-10-22): derive_booking_class() computes
                  quiet / timing-pairable / correctness from decision+prior+notes (see its docstring);
                  a declared class STRICTER than the derived one (quiet > timing-pairable >
                  correctness) is a violation (REFUSE under --for-grant, WARN otherwise).
                  `--print-class ROW` prints the derived class for grant writers (gpu-quiet claim:
                  only block-timing-quiet takes it).
Row ids must be unique (duplicate = violation on the later row).

Queue semantics (operator ruling relayed by workspace-58, 2026-10-22: "Being queued implies BEING
ready").  Terminal rows (COMPLETE, CANCELLED) are exempt from the rules below.
    QUEUED   = ready=y AND status ARMED AND a LIVE launcher.  The launcher PID is encoded as a
               `pid=<N>` token in the existing `launcher + PID` cell (col 3) or, failing that, in
               `notes`; the legacy spelling `PID <N>` in col 3 is also read.  No 19th column.
               Live = /proc/<N> exists AND its cmdline contains the row's filler-id, a grant id
               named in the row (`grants/<id>.grant`, `grant <id>`, `grant=<id>`) or a launcher
               script path (.sh/.py/.bash absolute path in col 3).  Needs a stated min window
               (col 11) and RAM (col 6, checked above).  ready=y with a dead/absent PID is an error.
    BACKLOG  = everything else (ready=n).  status must be BACKLOG, `owner` (col 2) filled, and
               `notes` must carry `blocker=<kind>[: free text]` with kind one of
               {missing launcher, harness fix, build, operator decision}.
    REGISTERED / NOT-ARMED / ... with ready=n is an error: convert the row to BACKLOG.
The liveness probe is injectable: check_row(..., pid_alive=f) / module attribute `pid_alive`
(signature f(pid: int, tokens: list[str]) -> bool).
"""
from __future__ import annotations

import argparse
import os
import re
import sys

DEFAULT_FILE = "/mnt/raid0/llm/tmp/compute-flags/FILLERS.md"
COLUMNS = ["filler-id", "owner", "launcher + pid", "resources", "min useful window",
           "max private ram", "stop file", "status", "class", "duration", "min window",
           "ds41-class y/n", "ready y/n", "prior", "decision", "min_effect", "substrate", "notes"]
HEADER_ALIASES = {"peak host ram gib": "max private ram", "peak host ram (gib)": "max private ram"}
RAM_RE = re.compile(r"^~?\s*\d+(?:\.\d+)?\s*(?:gib)?$", re.I)
STATUSES = {"ARMED", "REGISTERED", "NOT-ARMED", "CANCELLED", "COMPLETE", "BACKLOG"}
TERMINAL = {"COMPLETE", "CANCELLED"}
BLOCKER_KINDS = ("missing launcher", "harness fix", "build", "operator decision")
BLOCKER_RE = re.compile(r"blocker\s*[=:]\s*(" + "|".join(BLOCKER_KINDS) + r")\b", re.I)
PID_RE = re.compile(r"\bpid=(\d+)\b", re.I)
LEGACY_PID_RE = re.compile(r"\bPID\s+(\d+)\b")
GRANT_RE = re.compile(r"grants/([\w.-]+?)\.grant|\bgrant[ =]`?([\w][\w.-]*)", re.I)
LAUNCHER_PATH_RE = re.compile(r"(?<![\w.])/[\w.@+=/-]+\.(?:sh|py|bash)\b")
CLASSES = {"filler", "block-correctness", "block-timing-pairable", "block-timing-quiet"}
SUBSTRATES = {"cpu", "gpu", "either"}

PATH_RE = re.compile(r"(?<![\w.])/[\w.@+=-]+(?:/[\w.@+=-]+)+")
NONE_RE = re.compile(r"^none(?: found)? \(.*\d{4}-\d{2}-\d{2}.*\)", re.I)
BASELINE_RE = re.compile(r"champion|candidate|baseline", re.I)
FLOOR_RE = re.compile(r"[\w/.@+=-]*floor[\w/.@+=-]*\.(?:json|md|jsonl|txt)\b", re.I)
# CTC-Q-C (D9 ack 2026-10-22): booking class is DERIVED from the decision, not defaulted.
KEEP_GATE_RE = re.compile(r"keep gate|\bKEEP\b|keep[ /]+(?:or|vs)|\bHOLD\b|fold (?:or|vs)", re.I)
REGISTRY_FLOOR_RE = re.compile(r"registry[\w\s/-]{0,20}floor|floor[\w\s/-]{0,20}registry", re.I)
TIMING_RE = re.compile(r"indicative|timing|tok/s|\bt/s\b|\bpp\d*\b|\btg\b|latency|"
                       r"throughput|wall[- ]?clock|ms/|\bhost gap\b", re.I)
# A disclaimed mention ("no throughput claim", "not a timing run", "without timing", "non-timing") is not a
# timing signal; nor is "indicative correctness" (indicative is a timing token only as "indicative timing/speed").
_TIMING_TOK = TIMING_RE.pattern.replace("indicative|", "")
# Only articles may sit between the negator and the token, and a token followed by regression/loss/drop is a timing
# GATE ("no throughput regression", "no tg loss"), not a disclaimer: under-classifying a timing run is the worse error.
NEGATED_TIMING_RE = re.compile(r"(?:\b(?:no|not|without|never)\b|\bnon-?)[\s-]+(?:(?:a|an|the|any)\s+)?(?:" + _TIMING_TOK
                               + r")(?![\w/-]*[\s-]+(?:regression|loss|drop|degradation|delta|change))", re.I)
INDICATIVE_CORRECTNESS_RE = re.compile(r"indicative[\s-]+(?:correctness|check|only)", re.I)


def has_timing_signal(text: str) -> bool:
    """TIMING_RE over text with negated/disclaimed timing mentions and 'indicative correctness' removed."""
    return bool(TIMING_RE.search(INDICATIVE_CORRECTNESS_RE.sub(" ", NEGATED_TIMING_RE.sub(" ", text))))


# A row that MEASURES a floor (A/A, noise unit/floor, floor calibration/pairs) for a build is a baseline
# measurement: it cannot cite a floor file because it produces one.  Needs a build reference too.
FLOOR_MEASURE_RE = re.compile(r"noise[- ](?:unit|floor)|\ba/?a[- ]floor|floor[- ](?:calibration|pairs?)|"
                              r"serving-floor calibration|measures? (?:the )?(?:\w+ ){0,2}floor", re.I)
BUILD_REF_RE = re.compile(r"champion|candidate|baseline|\brecipe\b|\bbuild\b|\b[0-9a-f]{7,12}\b", re.I)
CLASS_RANK = {"block-correctness": 0, "block-timing-pairable": 1, "block-timing-quiet": 2}
EFFECT_NUM_RE = re.compile(r"\d")
EFFECT_QUAL_RE = re.compile(r"\b(exact(?:ly)?|identical|identity|zero)\b", re.I)
EFFECT_BUILD_RE = re.compile(r"^n/a \([^)\s][^)]*\)", re.I)


class Malformed(Exception):
    pass


def split_row(line: str) -> list[str]:
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|")):
        raise Malformed(f"not a table row: {line[:60]!r}")
    return [c.strip() for c in s[1:-1].split("|")]


def parse_table(text: str) -> tuple[dict[str, int], list[tuple[int, list[str]]], list[str]]:
    """Return (column index by lowercase name, [(line_no, cells)], notes) for the filler table.

    The table runs to the next heading ('#').  A blank line inside it is tolerated (the rows
    below are still checked) but reported, because markdown renders them as a separate block."""
    lines = text.splitlines()
    hdr = None
    for i, ln in enumerate(lines):
        if ln.startswith("|") and ln.split("|")[1].strip().lower() == "filler-id":
            hdr = i
            break
    if hdr is None:
        raise Malformed("no table header starting with '| filler-id |'")
    names = [HEADER_ALIASES.get(c.lower(), c.lower()) for c in split_row(lines[hdr])]
    if names != COLUMNS:
        raise Malformed("header columns differ from the 18 expected: got "
                        f"{len(names)} ({' | '.join(names)})")
    rows = []
    notes: list[str] = []
    blank_at = 0
    for j in range(hdr + 1, len(lines)):
        ln = lines[j]
        if ln.startswith("#"):
            break
        if not ln.startswith("|"):
            if not ln.strip() and not blank_at:
                blank_at = j + 1
            continue
        if blank_at:
            notes.append(f"line {blank_at}: blank line inside the table; rows below it render "
                         "as a separate block in markdown (still validated)")
            blank_at = 0
        cells = split_row(ln)
        if cells and set(cells[0]) <= set("-: "):
            continue  # the |---|---| separator
        rows.append((j + 1, cells))
    return {n: k for k, n in enumerate(names)}, rows, notes


def unfilled(v: str) -> bool:
    return v.strip() in ("", "-")


def proc_pid_alive(pid: int, tokens: list[str]) -> bool:
    """True iff /proc/<pid> exists and its cmdline contains at least one of `tokens`."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmd = f.read().replace(b"\0", b" ").decode("utf-8", "replace")
    except OSError:
        return False
    return any(t and t in cmd for t in tokens)


pid_alive = proc_pid_alive  # monkeypatchable; check_row(pid_alive=...) overrides per call


def launcher_pid(cells: list[str], col: dict[str, int]) -> int | None:
    for cell, rx in ((cells[col["launcher + pid"]], PID_RE), (cells[col["notes"]], PID_RE),
                     (cells[col["launcher + pid"]], LEGACY_PID_RE)):
        m = rx.search(cell)
        if m:
            return int(m.group(1))
    return None


def queue_semantics(cells: list[str], col: dict[str, int], probe) -> list[str]:
    """QUEUED-implies-ready / everything-else-BACKLOG rules (a)-(d)."""
    g = lambda name: cells[col[name]]  # noqa: E731
    status = g("status").split()[0] if g("status").split() else ""
    if status in TERMINAL:
        return []
    out: list[str] = []
    ready = g("ready y/n")
    if ready == "y":
        if status != "ARMED":
            out.append(f"ready=y but status {status!r}: a queued row is ARMED with a live launcher; "
                       "otherwise set ready=n and status BACKLOG")
        if unfilled(g("min window")):
            out.append("ready=y needs a stated min window (col 11)")
        pid = launcher_pid(cells, col)
        if pid is None:
            out.append("ready=y but no launcher PID: put `pid=<N>` in the launcher + PID cell "
                       "(the launcher must be alive and polling its grant), else make it BACKLOG")
        else:
            lc = g("launcher + pid")
            tokens = [g("filler-id")] + LAUNCHER_PATH_RE.findall(lc)
            tokens += [a or b for a, b in GRANT_RE.findall(lc + " " + g("notes"))]
            if not probe(pid, tokens):
                out.append(f"ready=y but launcher pid={pid} is dead (no /proc/{pid}, or its cmdline "
                           "names neither the row id, a grant id nor the launcher path): "
                           "convert the row to BACKLOG")
    elif ready == "n":
        if status == "REGISTERED":
            out.append("status REGISTERED with ready=n is an error: convert it to BACKLOG "
                       "(blocker=<missing launcher|harness fix|build|operator decision> + owner)")
        elif status != "BACKLOG":
            out.append(f"non-ready row has status {status!r}: must be BACKLOG")
    if status == "BACKLOG" or ready == "n":
        if unfilled(g("owner")):
            out.append("BACKLOG row needs an owner (col 2)")
        if not BLOCKER_RE.search(g("notes")):
            out.append("BACKLOG row needs `blocker=<missing launcher|harness fix|build|"
                       "operator decision>[: text]` in notes")
    if status == "BACKLOG" and ready == "y":
        out.append("status BACKLOG with ready=y is contradictory")
    return out


def declared_class(cells: list[str], col: dict[str, int]) -> str:
    """First token of the class cell (tolerates trailing prose such as 'block-timing-quiet (why)')."""
    t = cells[col["class"]].split()
    return t[0] if t else ""


def scratch_retention_violations(notes: str) -> list[str]:
    """Require an explicit, narrow per-file custody plan for scratch writers.

    Empty raw declarations cannot demonstrate that launchers do not write temp,
    server, or cache files, so fail closed instead of inspecting mutable scripts.
    """
    fields = {}
    for part in notes.split(';'):
        if '=' in part:
            k, v = part.strip().split('=', 1)
            if k.strip() in {'scratch_root', 'keep_globs', 'raw_globs'}:
                if k.strip() in fields:
                    return [f'duplicate {k.strip()} in notes']
                fields[k.strip()] = v.strip()
    if 'scratch_root' not in fields:
        return []
    root = fields['scratch_root'].rstrip('/')
    if not root.startswith('/') or root in ('', '/') or os.path.normpath(root) != root:
        return ['scratch_root must be a normalized absolute path']
    raw = [x.strip() for x in fields.get('raw_globs', '').split(',') if x.strip() and x.strip() not in ('-', 'none', '[]')]
    keep = [x.strip() for x in fields.get('keep_globs', '').split(',') if x.strip() and x.strip() not in ('-', 'none', '[]')]
    out = []
    if not raw:
        out.append('scratch_root requires nonempty raw_globs; declare cache/server/tmp outputs explicitly')
    for pattern in keep:
        if '..' in pattern.split('/') or (pattern.startswith('/') and not pattern.startswith(root + '/') and pattern != root):
            out.append('keep_globs must stay inside scratch_root')
            continue
        rel = pattern[len(root) + 1:] if pattern.startswith(root + '/') else pattern
        if pattern == root or rel in ('.', '*', '**', '**/*') or rel.endswith('/**'):
            out.append('keep_globs must name evidence files, not the scratch root or a whole directory')
    return out


def strict_scratch_retention(notes: str) -> bool:
    """Explicit opt-in for newly migrated rows; old rows warn until migrated."""
    return bool(re.search(r'(?:^|;)\s*retention_v2\s*=\s*1\s*(?:;|$)', notes))


def measures_build_floor(cells: list[str], col: dict[str, int]) -> bool:
    """The existing floor-measurement exception, shared by derivation and admission."""
    dec = cells[col["decision"]]
    return bool(FLOOR_MEASURE_RE.search(dec + " " + cells[col["min_effect"]])
                and BUILD_REF_RE.search(dec))


def derive_booking_class(cells: list[str], col: dict[str, int]) -> str:
    """CTC-Q-C: derive the booking class of a row from its decision / prior / notes (and min_effect unit).

    QUIET             (also: decision/min_effect says the row MEASURES a floor for a build)
                      decision names a champion/candidate/baseline or a keep gate, AND a floor file
                      (serving-floor.*.json style, via FLOOR_RE) or a registry floor is cited in
                      decision, notes or prior.
    TIMING-PAIRABLE   not quiet, but the decision / min_effect / notes is indicative or timing-valued.
    CORRECTNESS       everything else.
    'filler' rows are not blocks: returned unchanged.  Correctness never takes a quiet window by default."""
    g = lambda name: cells[col[name]]  # noqa: E731
    if declared_class(cells, col) == "filler":
        return "filler"
    dec, notes, prior = g("decision"), g("notes"), g("prior")
    names_baseline = bool(BASELINE_RE.search(dec) or KEEP_GATE_RE.search(dec))
    cites_floor = any(FLOOR_RE.search(t) or REGISTRY_FLOOR_RE.search(t) for t in (dec, notes, prior))
    if names_baseline and cites_floor:
        return "block-timing-quiet"
    if measures_build_floor(cells, col):
        return "block-timing-quiet"
    if has_timing_signal(" ".join((dec, g("min_effect"), notes))):
        return "block-timing-pairable"
    return "block-correctness"


def check_row(cells: list[str], col: dict[str, int], seen: set[str], pid_alive=None) -> list[str]:
    """Violations of one 18-cell row (empty list = clean)."""
    probe = pid_alive or globals()["pid_alive"]
    g = lambda name: cells[col[name]]  # noqa: E731
    out: list[str] = []
    rid = g("filler-id")
    if unfilled(rid) or " " in rid:
        out.append(f"filler-id {rid!r} is empty or contains spaces")
    if rid in seen:
        out.append("duplicate filler-id")

    status = g("status")
    tok = status.split()[0] if status.split() else ""
    if tok not in STATUSES:
        out.append(f"status {status!r}: first token must be one of {sorted(STATUSES)}")
    elif status != tok:
        out.append(f"status {status!r}: carries text after the token {tok!r} (put it in notes)")
    if tok in TERMINAL:
        return out  # terminal rows: id, uniqueness and status token only
    if strict_scratch_retention(g('notes')):
        out += scratch_retention_violations(g('notes'))
    ram = g("max private ram")
    if not RAM_RE.match(ram):
        out.append(f"peak host RAM (col 6) {ram[:40]!r}: must be a number in GiB, e.g. '48' or "
                   "'48 GiB' (private/anon peak + file-mapped weight bytes)")
    if g("class") not in CLASSES:
        out.append(f"class {g('class')!r} not in {sorted(CLASSES)}")
    for name in ("ds41-class y/n", "ready y/n"):
        if g(name) not in ("y", "n"):
            out.append(f"{name} {g(name)!r} must be exactly y or n")
    if g("substrate") not in SUBSTRATES:
        out.append(f"substrate {g('substrate')!r} not in {sorted(SUBSTRATES)}")

    prior = g("prior")
    if unfilled(prior):
        out.append("prior unfilled ('-'): path to the checked prior result, or "
                   "'none found (<who>, <date>)'")
    elif not (PATH_RE.search(prior) or NONE_RE.match(prior)):
        out.append(f"prior {prior[:60]!r}: neither a path nor 'none found (<who>, <date>)'")

    dec = g("decision")
    if unfilled(dec) or len(dec) < 8:
        out.append("decision unfilled or too short (one line naming the decision it informs)")

    eff = g("min_effect")
    if unfilled(eff):
        out.append("min_effect unfilled ('-'): effect size with a unit, or 'n/a (<reason>)'")
    elif not (EFFECT_BUILD_RE.match(eff) or EFFECT_NUM_RE.search(eff) or EFFECT_QUAL_RE.search(eff)):
        out.append(f"min_effect {eff[:60]!r}: no number/unit, exact-identity wording or 'n/a (<reason>)'")

    if g("class") == "block-timing-quiet" and not measures_build_floor(cells, col):
        if not BASELINE_RE.search(dec):
            out.append("block-timing-quiet: decision must name a champion/candidate baseline")
        if not (FLOOR_RE.search(g("notes")) or FLOOR_RE.search(prior)):
            out.append("block-timing-quiet: notes or prior must cite a floor file "
                       "(e.g. serving-floor.*.json)")
    dcl, ecl = declared_class(cells, col), derive_booking_class(cells, col)
    if dcl in CLASS_RANK and CLASS_RANK[dcl] > CLASS_RANK[ecl]:
        out.append(f"declared class {dcl} is stricter than derived {ecl} (CTC-Q-C): quiet needs a "
                   "decision naming a champion/candidate baseline or keep gate AND a cited floor "
                   "file; timing-pairable needs an indicative/timing decision; correctness jobs "
                   "must not take quiet windows by default")
    out += queue_semantics(cells, col, probe)
    return out


def run(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="validate the FILLERS.md queue table")
    ap.add_argument("--file", default=DEFAULT_FILE)
    ap.add_argument("--row")
    ap.add_argument("--for-grant", action="store_true")
    ap.add_argument("--print-class", metavar="ROW",
                    help="print the DERIVED booking class of ROW (one token on stdout) and exit 0; "
                         "grant writers set --gpu-quiet from it (3 if the row is unknown/malformed)")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 3 if e.code else 0
    if a.for_grant and not a.row:
        print("MALFORMED: --for-grant requires --row <filler-id>", file=sys.stderr)
        return 3
    try:
        with open(a.file, encoding="utf-8") as f:
            text = f.read()
        col, rows, tnotes = parse_table(text)
    except (OSError, UnicodeDecodeError, Malformed) as exc:
        print(f"MALFORMED: {a.file}: {exc}", file=sys.stderr)
        return 3

    if a.print_class:
        for _, cells in rows:
            if cells and cells[0] == a.print_class:
                if len(cells) != len(COLUMNS):
                    print(f"MALFORMED: row {a.print_class!r}: {len(cells)} cells", file=sys.stderr)
                    return 3
                print(derive_booking_class(cells, col))
                return 0
        print(f"MALFORMED: row {a.print_class!r} not found in {a.file}", file=sys.stderr)
        return 3

    seen: set[str] = set()
    for n in tnotes:
        print(f"WARN {n}")
    refused = warned = checked = 0
    found = False
    for line_no, cells in rows:
        rid = cells[0] if cells else ""
        target = a.row is None or rid == a.row
        if len(cells) != len(COLUMNS):
            if a.row is not None and rid == a.row:
                print(f"MALFORMED: line {line_no} row {rid!r}: {len(cells)} cells, expected "
                      f"{len(COLUMNS)} (a '|' inside a cell?)", file=sys.stderr)
                return 3
            if a.row is None:
                print(f"WARN line {line_no} {rid}: malformed row, {len(cells)} cells, expected "
                      f"{len(COLUMNS)} (a '|' inside a cell?)")
                warned += 1
            continue
        probs = check_row(cells, col, seen)
        seen.add(rid)
        if not target:
            continue
        found = found or rid == a.row
        checked += 1
        if cells[col['status']] not in TERMINAL and not strict_scratch_retention(cells[col['notes']]):
            for p in scratch_retention_violations(cells[col['notes']]):
                print(f"WARN line {line_no} {rid}: legacy scratch retention: {p}")
                warned += 1
        for p in probs:
            if a.for_grant:
                print(f"REFUSE line {line_no} {rid}: {p}")
                refused += 1
            else:
                print(f"WARN line {line_no} {rid}: {p}")
                warned += 1
    if a.row is not None and not found:
        print(f"MALFORMED: row {a.row!r} not found in {a.file}", file=sys.stderr)
        return 3
    verdict = "REFUSED" if refused else "OK"
    print(f"{verdict}: {checked} row(s) checked, {refused} refusal(s), {warned} warning(s)")
    return 2 if refused else 0


if __name__ == "__main__":
    sys.exit(run())
