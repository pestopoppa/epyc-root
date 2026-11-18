#!/usr/bin/env python3
"""Token guards for the handoff-session dispatcher (hs-dispatcher-v3), operator decision 2026-11-06
("agreed" to recommendations 1-5 of docs/reports/coordination/token-efficiency-audit-20261106.md).

Zero-token: pure functions over the registry, the Codex rollouts and budget.json. No model is ever called here.

  G1 resolve_spawn()      explicit model + effort per spawn (row -> handoff -> registry entry -> cheap default),
                          validated against the installed Codex CLI's model catalog; unresolved => SpawnRefused.
  G2 lease_verdict()      per-thread token ceiling + wall-clock lease on a LIVE turn => kill + hard park.
     resume_verdict()     a continue-resume needs progress evidence (last turn had an effect) and stays under
                          max_resumes per 24 h; otherwise hard park (only `handoff_sessions.py unpark` clears it).
     quota_until()        a usage-limit hit with no parseable reset waits for budget.json resets_at (never 30 min).
  G3 (codex_budget_meter.py) writes budget.json; apply_budget_pause() honours its paused_until.
  G4 rotate_verdict()     last-call input > context_rotate_tokens (default 60k) => fresh thread from the checkpoint.
  G5 width_cap()          max_live = min(configured cap [default 2], floor(budget rate allowed / per-session rate)).

Every knob lives in the registry under `token_guards` (see DEFAULTS); the registry's top-level `max_live` is the cap.
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import signal

DEFAULTS = {
    # G1: the cheap default (NOT the ~/.codex/config.toml gpt-6.1-terra/high default the audit measured)
    "default_model": {"codex": "gpt-6-luna", "claude": "sonnet", "opencode": None},
    "default_effort": {"codex": "medium", "claude": "medium", "opencode": None},
    # G2
    "session_token_ceiling": 15_000_000,   # cumulative total_tokens of ONE thread (cached input included)
    "lease_s": 5400,                       # one turn's wall clock (worker_runner's lease)
    "max_resumes": 12,                     # continue-resumes per slug per rolling 24 h (launched spawns only)
    "noop_park_turns": 2,                  # consecutive no-effect turns before a no-progress park (R3)
    "spawn_refused_park": 3,               # consecutive identical SpawnRefused reasons -> spawn-config-invalid park (R1)
    "auto_unpark_max_per_day": 2,          # guard-park auto-unparks per slug per rolling 24 h (R2/R5)
    "unknown_reset_backoff_s": 6 * 3600,   # only when neither the error text nor budget.json gives resets_at
    # G4
    "context_rotate_tokens": 60_000,
    # G5
    "max_live": 2,
    "claude_weekly_tokens": None,          # operator-stated weekly Claude allowance (tokens); None = meter without alarms
    "reserve_fraction": 0.05,              # CHURN-CONT-RESERVE: weekly-budget tranche held back for janitor/filing/teardown
    "per_session_frac_per_h": 0.012,       # fallback weekly-fraction burn per live session (audit W2: ~1.2 %/h)
    "pace_multiplier": 1.0,                # operator scales the budget-paced allowed rate (2026-11-17: 2.5 so that width 2 fits)
    # D9 net-progress guard (2026-11-18): rolling per-slug turn history of real tick flips vs new open boxes
    "netprog_window": 6,                   # (a) last N turns: sum(opened) >= sum(closed) and no result -> park
    "netprog_prep_only": 8,                # (b) last N consecutive turns with result=False -> park
}
EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")
CODEX_SESSIONS = os.path.expanduser("~/.codex/sessions")
CODEX_MODELS_CACHE = os.path.expanduser("~/.codex/models_cache.json")
BUDGET_NAME = "budget.json"


class SpawnRefused(ValueError):
    """A spawn without a resolved, valid model + effort. The dispatcher logs REFUSED-SPAWN and does not launch."""


def cfg(reg: dict) -> dict:
    c = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    for k, v in ((reg or {}).get("token_guards") or {}).items():
        if isinstance(c.get(k), dict) and isinstance(v, dict):
            c[k].update(v)  # per-key deep merge: a registry that sets only codex keeps the other engines' defaults
        else:
            c[k] = v
    if (reg or {}).get("max_live") is not None:
        c["max_live"] = int(reg["max_live"])
    return c


# ---------------------------------------------------------------- G1 model + effort
def codex_catalog(path=CODEX_MODELS_CACHE) -> dict | None:
    """{model slug: [efforts]} from the installed Codex CLI's model cache; None if unreadable."""
    try:
        d = json.load(open(path))
    except (OSError, ValueError):
        return None
    out = {}
    for m in (d.get("models") if isinstance(d, dict) else d) or []:
        if isinstance(m, dict) and m.get("slug"):
            out[m["slug"]] = [x.get("effort") for x in m.get("supported_reasoning_levels") or [] if isinstance(x, dict)]
    return out or None


_DECL = re.compile(r"^\s*(?:[-*>]\s*)?\**\s*(?:codex[ _-])?(model|effort|reasoning[ _-]effort)\s*\**\s*[:=]\s*\**\s*`?([A-Za-z0-9._/#-]+)`?",
                   re.I | re.M)


def declared(text: str, head_lines: int = 60) -> dict:
    """`model:` / `effort:` declarations in a handoff's header (first `head_lines` lines)."""
    out = {}
    for k, v in _DECL.findall("\n".join((text or "").splitlines()[:head_lines])):
        k = "model" if k.lower() == "model" else "effort"
        out.setdefault(k, v.strip())
    return out


def resolve_spawn(engine: str, entry: dict, handoff_text: str = "", row_decls=(), conf=None, catalog=None) -> dict:
    """Resolve (model, effort) for one spawn; precedence row > handoff > registry entry > engine default.
    Raises SpawnRefused unless both are resolved and (codex) accepted by the installed CLI's catalog."""
    conf = conf or DEFAULTS
    src = {}
    model = effort = None
    layers = [(f"row:{r.get('id', '?')}", r) for r in row_decls or [] if isinstance(r, dict)]
    layers += [("handoff", declared(handoff_text)), ("registry", {"model": entry.get("model"), "effort": entry.get("effort")}),
               ("default", {"model": (conf.get("default_model") or {}).get(engine), "effort": (conf.get("default_effort") or {}).get(engine)})]
    for name, d in layers:
        if name == "handoff":  # header prose (e.g. "M1-M2 ~half day") is a size estimate, not a setting: ignore, never refuse
            d = dict(d)
            if d.get("effort") and str(d["effort"]).lower() not in EFFORTS:
                src["handoff_ignored_effort"] = str(d.pop("effort"))
            if engine == "codex" and catalog is not None and d.get("model") and str(d["model"]) not in catalog:
                src["handoff_ignored_model"] = str(d.pop("model"))
        if model is None and d.get("model"):
            model, src["model"] = str(d["model"]), name
        if effort is None and d.get("effort"):
            effort, src["effort"] = str(d["effort"]).lower(), name
    if not model or not effort:
        raise SpawnRefused(f"{engine}: model={model!r} effort={effort!r} not both resolved (declare them in the row, the handoff "
                           f"header or the registry entry; no engine default for {engine})")
    if effort not in EFFORTS:
        raise SpawnRefused(f"{engine}: effort {effort!r} is not one of {EFFORTS}")
    if engine == "codex":
        if catalog is None:
            raise SpawnRefused(f"codex: model catalog {CODEX_MODELS_CACHE} unreadable; cannot validate {model}/{effort}")
        if model not in catalog:
            raise SpawnRefused(f"codex: model {model!r} not accepted by the installed CLI (known: {sorted(catalog)})")
        if catalog[model] and effort not in catalog[model]:
            raise SpawnRefused(f"codex: effort {effort!r} not supported by {model} (supported: {catalog[model]})")
    return {"model": model, "effort": effort, "source": src}


def engine_flags(engine: str, model: str, effort: str) -> list:
    """CLI flags that pin model + effort (plan mode included for Codex) so nothing inherits ~/.codex/config.toml."""
    if engine == "codex":
        return ["-m", model, "-c", f'model_reasoning_effort="{effort}"', "-c", f'plan_mode_reasoning_effort="{effort}"']
    if engine == "claude":
        return ["--model", model, "--effort", effort]
    if engine == "opencode":
        return ["-m", model if "#" in model else f"{model}#{effort}"]
    raise SpawnRefused(engine)


# ---------------------------------------------------------------- rollout usage
def rollout_usage(session_id, root=CODEX_SESSIONS) -> dict | None:
    """{last_input, total_tokens, rate_limits} from the LAST token_count event of a Codex thread's rollout."""
    if not session_id:
        return None
    files = glob.glob(os.path.join(root, "*", "*", "*", f"rollout-*-{session_id}.jsonl"))
    if not files:
        return None
    out = None
    try:
        with open(max(files, key=os.path.getmtime), "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 400_000))
            for ln in f.read().decode(errors="replace").splitlines():
                if '"token_count"' not in ln:
                    continue
                try:
                    p = json.loads(ln).get("payload") or {}
                except ValueError:
                    continue
                info = p.get("info") or {}
                out = {"last_input": int((info.get("last_token_usage") or {}).get("input_tokens") or 0),
                       "total_tokens": int((info.get("total_token_usage") or {}).get("total_tokens") or 0),
                       "rate_limits": p.get("rate_limits")}
    except OSError:
        return None
    return out


# ---------------------------------------------------------------- G2 budget, lease, resumes, quota
def park(e: dict, reason: str, now_iso: str) -> None:
    e["parked"] = {"reason": reason, "at": now_iso, "wrapup": e.get("last_wrapup")}


def is_parked(e: dict) -> bool:
    """An operator gate is a park that only a ratification lifts (it also holds events queued)."""
    return bool(e.get("parked")) or is_gated(e)


# ---------------------------------------------------------------- operator gate (2026-11-18)
# Operator-only work (e.g. kernel promotion v11): a session carrying operator_gate {"reason", "since"} is never spawned,
# resumed, auto-unparked or auto-started; only `handoff_sessions.py unpark` with a valid ratification file lifts it.
RATIFY_SUBDIR = "operator-ratify"
RATIFY_KEYS = ("slug", "by", "at", "reason")


def is_gated(e: dict) -> bool:
    return isinstance(e, dict) and bool(e.get("operator_gate"))


def ratify_dir(flags: str) -> str:
    return os.path.join(flags, RATIFY_SUBDIR)


def ratification(flags: str, slug: str) -> tuple[bool, str]:
    """(ok, why) for <flags>/operator-ratify/<slug>.json: a JSON object with slug/by/at/reason, slug matching."""
    p = os.path.join(ratify_dir(flags), f"{slug}.json")
    try:
        with open(p) as f:
            d = json.load(f)
    except FileNotFoundError:
        return False, f"no ratification file {p}"
    except (OSError, ValueError) as ex:
        return False, f"unreadable ratification file {p}: {ex}"
    if not isinstance(d, dict):
        return False, f"ratification file {p} is not a JSON object"
    missing = [k for k in RATIFY_KEYS if not str(d.get(k) or "").strip()]
    if missing:
        return False, f"ratification file {p} lacks {', '.join(missing)}"
    if d["slug"] != slug:
        return False, f"ratification file {p} names slug {d['slug']!r}, not {slug!r}"
    return True, f"ratified by {d['by']} at {d['at']}: {d['reason']}"


def unpark(e: dict) -> None:
    e.pop("parked", None)
    e["resume_ts"], e["noop_turns"] = [], 0


def lease_verdict(e: dict, usage: dict | None, now: float, last_resume_ts: float, conf=None) -> str | None:
    """Reason to kill + park a LIVE turn, or None."""
    conf = conf or DEFAULTS
    if usage and usage.get("total_tokens", 0) > int(conf["session_token_ceiling"]):
        return f"thread token ceiling: {usage['total_tokens']} > {conf['session_token_ceiling']}"
    if last_resume_ts and now - last_resume_ts > int(conf["lease_s"]):
        return f"lease expired: turn running {int(now - last_resume_ts)} s > {conf['lease_s']} s"
    return None


def resume_verdict(e: dict, now: float, conf=None) -> tuple[bool, str]:
    """May a continue-driven resume happen? (ok, why). Not ok => the caller hard-parks with `why`."""
    conf = conf or DEFAULTS
    if is_gated(e):
        return False, f"operator-gate: {e['operator_gate'].get('reason')}"
    if is_parked(e):
        return False, f"parked: {e['parked'].get('reason')}"
    if int(e.get("noop_turns") or 0) >= int(conf.get("noop_park_turns", DEFAULTS["noop_park_turns"])):
        return False, f"no progress evidence: last {e.get('noop_turns')} turn(s) landed no tick, row or filing"
    recent = [t for t in e.get("resume_ts") or [] if now - t < 86400]
    if len(recent) >= int(conf["max_resumes"]):
        return False, f"max_resumes: {len(recent)} continue-resumes in 24 h >= {conf['max_resumes']}"
    return True, "progress evidence present"


def note_resume(e: dict, now: float) -> None:
    """Count one continue-resume. Call only after the spawn actually launched (R1: refusals are not resumes)."""
    e["resume_ts"] = [t for t in e.get("resume_ts") or [] if now - t < 86400] + [now]


AUTO_UNPARK_REASONS = ("no progress evidence", "max_resumes", "thread token ceiling", "no-net-progress")

NETPROG_PREFIX = "no-net-progress"
_TICK_RX = re.compile(r"^[-+]\s*[-*] \[[xX]\]")
_OPEN_RX = re.compile(r"^[-+]\s*[-*] \[ \]")


_BELIEF_RX = re.compile(r"\[belief:\s*([^\]]*)\]")
# a verdict word, or a NUMBER in the measurement sense (unit, ratio, comparison, fraction) - bare digits in ids, dates,
# shas, model names ("Qwen3-0.6B", "v10", "2026-11-18") are not results
_VERDICT_RX = re.compile(r"\b(PASS(ED)?|FAIL(ED)?|KEEP|NO-GO|GO|verdict)\b|%|×|"
                         r"\d(\.\d+)?\s*(x\b|tok/s|t/s|ms\b|s\b|GiB|GB|MiB|MB|pp\b)|[<>=≥≤±]\s*-?\d|\b\d+\s*/\s*\d+\b")
_PREP_RX = re.compile(r"\b(prepar\w*|ready|custody|publish\w*|pin\w*|wire\w*|implement\w*)\b", re.I)
_NOISE_RX = re.compile(r"✅\s*\d{4}-\d{2}-\d{2}|\b\d{4}-\d{2}-\d{2}\b|\b[0-9a-f]{7,40}\b|\*\*[A-Z][A-Za-z0-9-]*")


def belief_result(line: str) -> bool:
    """D9: a `[belief:` tick is a RESULT only when the ticked line states a verdict or a number; `[belief: cc]` on a
    prepare/ready/custody/publish/wire line is ceremony, never a result."""
    m = _BELIEF_RX.search(line)
    if not m:
        return False
    if m.group(1).strip() == "cc" and _PREP_RX.search(line):
        return False
    return bool(_VERDICT_RX.search(_NOISE_RX.sub(" ", _BELIEF_RX.sub(" ", line))))


def wrapup_progress(diff_text: str) -> dict:
    """D9 net progress of ONE wrap-up commit's handoff diff (`git show --format= <sha> -- handoffs/`).
    closed = real open->ticked flips: added tick lines beyond the ticked lines the commit removed (an edited or moved
    tick shows as -[x]/+[x] and nets to zero). opened = net new `- [ ]` lines: added open boxes beyond the removed open
    boxes that a flip does not explain. belief = an added tick line carries a RESULT-grade `[belief:` (belief_result)."""
    add_x = rem_x = add_o = rem_o = 0
    belief = False
    for l in diff_text.splitlines():
        if l.startswith(("+++", "---")):
            continue
        if _TICK_RX.match(l):
            if l[0] == "+":
                add_x += 1
                belief = belief or belief_result(l)
            else:
                rem_x += 1
        elif _OPEN_RX.match(l):
            if l[0] == "+":
                add_o += 1
            else:
                rem_o += 1
    closed = max(0, add_x - rem_x)
    opened = max(0, add_o - max(0, rem_o - closed))
    return {"closed": closed, "opened": opened, "belief": belief}


def netprog_verdict(hist: list, conf=None) -> str | None:
    """D9: park reason `no-net-progress: <numbers>` or None, from the per-slug turn history (oldest first; each item
    has closed / opened / result)."""
    conf = conf or DEFAULTS
    w = int(conf.get("netprog_window", DEFAULTS["netprog_window"]))
    p = int(conf.get("netprog_prep_only", DEFAULTS["netprog_prep_only"]))
    if w > 0 and len(hist) >= w:
        last = hist[-w:]
        so, sc = sum(int(t.get("opened") or 0) for t in last), sum(int(t.get("closed") or 0) for t in last)
        if so >= sc and not any(t.get("result") for t in last):
            return f"{NETPROG_PREFIX}: last {w} turns opened {so} >= closed {sc}, 0 results"
    if p > 0 and len(hist) >= p:
        last = hist[-p:]
        if not any(t.get("result") for t in last):  # ticks of prep boxes are the ceremony: closes do not rescue it
            return (f"{NETPROG_PREFIX}: last {p} turns 0 results (closed {sum(int(t.get('closed') or 0) for t in last)}, "
                    f"opened {sum(int(t.get('opened') or 0) for t in last)})")
    return None


def auto_unpark_eligible(e: dict, now: float, conf=None) -> bool:
    """R2/R5 guardrails: a GUARD park whose wait can end, never an operator or spawn-config-invalid park, and under
    auto_unpark_max_per_day in a rolling 24 h."""
    conf = conf or DEFAULTS
    if is_gated(e):
        return False
    reason = str((e.get("parked") or {}).get("reason") or "")
    if not reason or "operator" in reason or reason.startswith("spawn-config-invalid"):
        return False
    if not reason.startswith(AUTO_UNPARK_REASONS):
        return False
    recent = [t for t in e.get("auto_unparks") or [] if now - t < 86400]
    return len(recent) < int(conf.get("auto_unpark_max_per_day", DEFAULTS["auto_unpark_max_per_day"]))


def auto_unpark(e: dict, now: float) -> None:
    """Unpark and charge the per-slug 24 h limit; a token-ceiling park restarts on a FRESH thread."""
    ceiling = str(e["parked"].get("reason") or "").startswith("thread token ceiling")
    unpark(e)
    e["auto_unparks"] = [t for t in e.get("auto_unparks") or [] if now - t < 86400] + [now]
    if ceiling:
        e["fresh_next"] = True


def kill_pid(pid: int) -> bool:
    """SIGTERM a PID the dispatcher itself spawned; SIGKILL if it survives the next check. True if signalled."""
    try:
        if int(pid) in (os.getpid(), os.getppid()) or int(pid) <= 1:
            return False  # never ourselves, our parent or init
        os.kill(int(pid), signal.SIGTERM)
        return True
    except (OSError, ValueError, TypeError):
        return False


def quota_until(now: float, budget: dict | None, conf=None) -> tuple[float, str]:
    """When a usage limit hit has no parseable reset: budget.json resets_at, else one long backoff (never 30 min)."""
    conf = conf or DEFAULTS
    r = float((budget or {}).get("resets_at") or 0)
    if r > now:
        return r, "budget.json resets_at"
    return now + int(conf["unknown_reset_backoff_s"]), "unknown-reset backoff"


# ---------------------------------------------------------------- G3 budget.json consumer
def load_budget(flags: str) -> dict | None:
    try:
        return json.load(open(os.path.join(flags, BUDGET_NAME)))
    except (OSError, ValueError):
        return None


def budget_paused_until(budget: dict | None, now: float) -> float:
    t = float((budget or {}).get("paused_until") or 0)
    return t if t > now else 0.0


# ---------------------------------------------------------------- G4 rotation
def rotate_verdict(last_input: int | None, conf=None) -> bool:
    conf = conf or DEFAULTS
    return (last_input or 0) > int(conf["context_rotate_tokens"])


def checkpoint_from(report: dict | None, e: dict) -> dict:
    r = report or {}
    return {"handoff": e.get("handoff"), "state": r.get("state"), "next": r.get("next"), "next_step": r.get("next_step"),
            "box": r.get("box"), "blocked_by": r.get("blocked_by"), "wrapped_sha": r.get("wrapped_sha") or e.get("last_wrapup"),
            "rotated_from": e.get("session_id"), "complete": bool(r)}


def checkpoint_block(cp: dict | None) -> str:
    if not cp:
        return ""
    return ("## Checkpoint from your previous thread (context rotation; that transcript is NOT available)\n"
            + json.dumps({k: v for k, v in cp.items() if v not in (None, [], "")}, indent=1) + "\n"
            "Re-read only the handoff boxes this names; start at `next_step`.\n")


# ---------------------------------------------------------------- G5 width cap
def width_cap(conf: dict, budget: dict | None, now: float, live: int = 0) -> tuple[int, str]:
    """(max_live, why) = min(configured cap, floor(allowed fraction/h / per-session fraction/h))."""
    cap = int(conf.get("max_live", DEFAULTS["max_live"]))
    if not budget or budget.get("weekly_fraction") is None or not budget.get("resets_at"):
        return cap, f"configured cap {cap} (budget unknown)"
    if budget_paused_until(budget, now):
        return 0, f"budget exhausted; paused until {budget.get('paused_until')}"
    rem = remaining_fraction(budget)
    if rem is not None and rem <= float(conf.get("reserve_fraction", DEFAULTS["reserve_fraction"])):
        return 0, f"reserve reached: remaining {rem:.4f} <= reserve {conf.get('reserve_fraction', DEFAULTS['reserve_fraction'])}"
    hours = max((float(budget["resets_at"]) - now) / 3600.0, 0.25)
    mult = float(conf.get("pace_multiplier", 1.0))
    allowed = max(0.0, 1.0 - float(budget["weekly_fraction"])) / hours * mult
    burn = float(budget.get("burn_frac_per_h") or 0)
    per = burn / live if live and burn > 0 else float(conf["per_session_frac_per_h"])
    derived = int(math.floor(allowed / per + 1e-9)) if per > 0 else cap
    m = f" (x{mult:g} pace)" if mult != 1.0 else ""
    return min(cap, derived), f"min(cap {cap}, derived {derived} = {allowed:.4f}/h allowed{m} / {per:.4f}/h per session)"


# ---------------------------------------------------------------- reserve tranche (CHURN-CONT-RESERVE)
# Work kinds that stay admitted once the reserve is reached: they CLOSE work (janitor/filing/teardown) and are
# charged outside row accounting. Everything else (the default "work") is new-work admission.
RESERVE_ELIGIBLE_KINDS = ("janitor", "filing", "teardown")


def remaining_fraction(budget: dict | None) -> float | None:
    """Remaining weekly fraction = 1 - the highest known used fraction (codex weekly_fraction, claude_weekly_fraction);
    None when the meter carries neither."""
    used = [float(budget[k]) for k in ("weekly_fraction", "claude_weekly_fraction") if budget and budget.get(k) is not None]
    return round(max(0.0, 1.0 - max(used)), 9) if used else None


def admit(conf: dict, budget: dict | None, kind: str = "work") -> tuple[bool, str]:
    """May new work of `kind` be admitted (session/row dispatch)? Refused once remaining weekly budget <= reserve_fraction.
    Reserve-eligible kinds are always admitted; a missing/unreadable meter fails CLOSED for "work", open for those."""
    if kind in RESERVE_ELIGIBLE_KINDS:
        return True, f"{kind}: reserve-eligible"
    rem = remaining_fraction(budget)
    if rem is None:
        return False, "meter missing or unreadable: fail closed for new work"
    reserve = float(conf.get("reserve_fraction", DEFAULTS["reserve_fraction"]))
    if rem <= reserve:
        return False, f"reserve reached: remaining {rem:.4f} <= reserve {reserve} (only {'/'.join(RESERVE_ELIGIBLE_KINDS)} admitted)"
    return True, f"remaining {rem:.4f} > reserve {reserve}"


# ---------------------------------------------------------------- restart gate (TOKEN-DISPATCHER-RESTART-GATE)
DOCTRINE_FILE = "agents/shared/OPERATING_CONSTRAINTS.md"
DOCTRINE_LINES = (
    "- Every spawn carries model + effort + token budget, or it is a defect.",
    "- Each wrap-up reports budget fraction per outcome.",
    "- **Fan-out width is a CEILING of 3-5 subagents, never a floor.**",
)


def restart_failures(reg: dict, budget: dict | None, now: float, root: str, catalog=None) -> list[str]:
    """Reasons the dispatcher must NOT be restarted; empty list = gate open."""
    out = []
    try:
        lines = set(open(os.path.join(root, DOCTRINE_FILE)).read().split("\n"))
    except OSError as ex:
        lines = set()
        out.append(f"doctrine: cannot read {DOCTRINE_FILE}: {ex}")
    for ln in DOCTRINE_LINES:
        if lines and ln not in lines:
            out.append(f"doctrine: line not ratified in {DOCTRINE_FILE}: {ln!r} (operator runs artifacts/operator/ratify_token_doctrine_20261106.sh)")
    if budget is None:
        out.append("budget: budget.json missing or unreadable (run codex_budget_meter.py once)")
    else:
        if budget.get("weekly_fraction") is not None and float(budget["weekly_fraction"]) >= 1.0 and budget_paused_until(budget, now) == 0.0 \
                and not budget.get("paused_until"):
            out.append(f"budget: weekly_fraction {budget['weekly_fraction']} >= 1 with no paused_until")
        if budget_paused_until(budget, now):
            out.append(f"budget: exhausted, paused_until {budget.get('paused_until')} is in the future")
    if float((reg or {}).get("paused_until") or 0) > now:
        out.append(f"registry: paused_until {(reg or {}).get('paused_until')} is in the future")
    conf = cfg(reg)
    if int(conf["max_live"]) > 2:
        out.append(f"max_live: {conf['max_live']} > 2")
    for eng, model in (conf.get("default_model") or {}).items():
        if not model:
            continue
        try:
            resolve_spawn(eng, {}, "", (), conf, catalog)
        except SpawnRefused as ex:
            out.append(f"defaults: {ex}")
    return out
