#!/usr/bin/env python3
"""pending_refs.py - "is this path/branch/build still wanted by PENDING work?" (operator keep rule 2026-11-21).

Prepped tasks wait on a host reboot or an autopilot/AutoKernel hold release, so their worktrees, scratch and builds
LOOK stale (idle, merged). referenced_by_pending() is the code-level exclusion shared by worktree_reaper.py and
build_ttl.py. A subject (absolute path, its basename, its branch) is PENDING-REFERENCED when any of these names it:

  1. a row spec / manifest / smoke record: every *.json under <flags>/{ready,parked,held,armed,hold,holds,dryrun}
     (ready/withdrawn/ included; only FILED ready/ and dryrun/ rows are history),
     and the top-level <flags> files whose name suggests a hold (ARMED*, HOLD*, *hold*, *pre-arm*, *prearm*)
  2. a handoff box: any line of handoffs/active/*.md except a ticked `[x]` box without hold words (a line naming the subject counts; lines that
     say waits-on-reboot / operator hold / held / parked / post-reboot are reported with that tag)
  3. a pre-arm/hold file or launcher: scripts under --script-root (default /workspace/scripts + <flags>/bin)
  4. a row id that is not filed yet (ready/<id>.json without filing-done/<id>.FILED): a subject whose basename
     contains that id (or the id contains the basename) is held

Matching is by substring on the absolute path, the basename and the branch name; names shorter than MIN_NAME (6) chars
only match as the full path, so `tf` or `main` never match everything. The index is built once per pass.
"""
from __future__ import annotations

import glob
import os

MIN_NAME = 6
CAP = 4 * 1024 * 1024
DEFAULT_FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
DEFAULT_HANDOFFS = ["/workspace/handoffs/active", "/mnt/raid0/llm/views/epyc-root-main/handoffs/active"]
DEFAULT_SCRIPT_ROOTS = ["/workspace/scripts"]
HOLD_WORDS = ("waits on reboot", "wait on reboot", "operator hold", "held", "parked", "post-reboot", "hold release",
              "stage-b", "autopilot relaunch", "pre-arm", "hil")
SPEC_SUBDIRS = ("ready", "parked", "held", "armed", "hold", "holds", "dryrun")
SCRIPT_EXT = (".sh", ".py")   # launchers only: docs/READMEs name builds as examples


def _read(p):
    try:
        if os.path.getsize(p) > CAP:
            return ""
        with open(p, "rb") as fh:
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return ""


class PendingIndex:
    def __init__(self, flags=DEFAULT_FLAGS, handoff_dirs=None, script_roots=None):
        self.flags = flags
        self.specs = []        # [(file, text)]
        self.boxes = []        # [(file, line, hold_tagged)]
        self.scripts = []      # [(file, text)]
        self.unfiled_ids = set()
        def filed(rid):
            return os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED"))

        for sub in SPEC_SUBDIRS:
            for p in glob.glob(os.path.join(flags, sub, "**", "*.json"), recursive=True):
                rel = os.path.relpath(p, os.path.join(flags, sub)).split(os.sep)
                # a WITHDRAWN spec (ready/withdrawn/) still protects what it names: a withdrawn row can be republished and a
                # build it named was lost once (operator 2026-11-21); only plain FILED history is ignored
                if "withdrawn" not in rel and sub in ("ready", "dryrun"):   # these dirs keep history: only UNFILED rows are pending work
                    rid = rel[0][:-5] if sub == "ready" and len(rel) == 1 else (rel[0] if sub == "dryrun" else os.path.basename(p)[:-5])
                    if filed(rid):
                        continue
                self.specs.append((p, _read(p)))
        for p in glob.glob(os.path.join(flags, "*")):
            n = os.path.basename(p).lower()
            if os.path.isfile(p) and ("hold" in n or "pre-arm" in n or "prearm" in n or n.startswith("armed")):
                self.specs.append((p, _read(p)))
        for p in glob.glob(os.path.join(flags, "ready", "**", "*.json"), recursive=True):
            rid = os.path.basename(p)[:-5]
            if not os.path.exists(os.path.join(flags, "filing-done", rid + ".FILED")):
                self.unfiled_ids.add(rid)
        seen = set()
        for d in (handoff_dirs if handoff_dirs is not None else DEFAULT_HANDOFFS):
            for p in glob.glob(os.path.join(d, "*.md")):
                rp = os.path.realpath(p)
                if rp in seen:
                    continue
                seen.add(rp)
                for ln in _read(p).splitlines():
                    low = ln.lower()
                    held = any(w in low for w in HOLD_WORDS)
                    if "[x]" in low and not held:
                        continue   # a ticked box is history, not pending work (a held/parked/reboot line always counts)
                    self.boxes.append((p, ln, held))
        for root in (script_roots if script_roots is not None else DEFAULT_SCRIPT_ROOTS + [os.path.join(flags, "bin")]):
            for dp, dns, fns in os.walk(root):
                dns[:] = [d for d in dns if d not in (".git", "node_modules", "__pycache__", "tests")]
                for fn in fns:
                    if fn.endswith(SCRIPT_EXT):
                        self.scripts.append((os.path.join(dp, fn), _read(os.path.join(dp, fn))))

    @staticmethod
    def _needles(path, branch, extra):
        ns = [os.path.normpath(path)]
        base = os.path.basename(path.rstrip("/"))
        # a generic basename (`source`, `app`, `tree`) names every other row's checkout too: only a DISTINCTIVE basename
        # (>= 8 chars with a digit, `-` or `_`) matches by name; the full path always does
        if len(base) >= 8 and any(c.isdigit() or c in "-_" for c in base):
            ns.append(base)
        for n in [branch] + list(extra or []):
            if n and len(n) >= MIN_NAME:
                ns.append(n)
        return ns

    def check(self, path, branch=None, extra=None):
        """-> reason string when pending work references the subject, else None."""
        ns = self._needles(path, branch, extra)
        base = os.path.basename(path.rstrip("/"))
        for rid in self.unfiled_ids:
            if len(rid) >= MIN_NAME and rid in base and any(c.isdigit() or c in "-_" for c in base):
                return f"unfiled-row:{rid}"
        for f, t in self.specs:
            for n in ns:
                if n in t:
                    return f"row-spec:{os.path.relpath(f, self.flags) if f.startswith(self.flags) else f} names {n}"
        for f, ln, held in self.boxes:
            for n in ns:
                if n in ln:
                    return f"handoff{'(hold)' if held else ''}:{os.path.basename(f)} names {n}"
        for f, t in self.scripts:
            for n in ns:
                if n in t:
                    return f"script:{f} names {n}"
        return None


def referenced_by_pending(path, branch=None, index=None, extra=None, **kw):
    """Convenience wrapper: reason or None. Pass a prebuilt `index` when checking many subjects."""
    return (index or PendingIndex(**kw)).check(path, branch, extra)
