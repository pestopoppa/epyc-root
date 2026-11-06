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
    "max_resumes": 12,                     # continue-resumes per slug per rolling 24 h
    "unknown_reset_backoff_s": 6 * 3600,   # only when neither the error text nor budget.json gives resets_at
    # G4
    "context_rotate_tokens": 60_000,
    # G5
    "max_live": 2,
    "per_session_frac_per_h": 0.012,       # fallback weekly-fraction burn per live session (audit W2: ~1.2 %/h)
}
EFFORTS = ("low", "medium", "high", "xhigh", "max", "ultra")
CODEX_SESSIONS = os.path.expanduser("~/.codex/sessions")
CODEX_MODELS_CACHE = os.path.expanduser("~/.codex/models_cache.json")
BUDGET_NAME = "budget.json"


class SpawnRefused(ValueError):
    """A spawn without a resolved, valid model + effort. The dispatcher logs REFUSED-SPAWN and does not launch."""


def cfg(reg: dict) -> dict:
    c = dict(DEFAULTS)
    c.update((reg or {}).get("token_guards") or {})
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
    e["parked"] = {"reason": reason, "at": now_iso}


def is_parked(e: dict) -> bool:
    return bool(e.get("parked"))


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
    if is_parked(e):
        return False, f"parked: {e['parked'].get('reason')}"
    if int(e.get("noop_turns") or 0) >= 1:
        return False, f"no progress evidence: last {e.get('noop_turns')} turn(s) landed no tick, row or filing"
    recent = [t for t in e.get("resume_ts") or [] if now - t < 86400]
    if len(recent) >= int(conf["max_resumes"]):
        return False, f"max_resumes: {len(recent)} continue-resumes in 24 h >= {conf['max_resumes']}"
    return True, "progress evidence present"


def note_resume(e: dict, now: float) -> None:
    e["resume_ts"] = [t for t in e.get("resume_ts") or [] if now - t < 86400] + [now]


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
    hours = max((float(budget["resets_at"]) - now) / 3600.0, 0.25)
    allowed = max(0.0, 1.0 - float(budget["weekly_fraction"])) / hours
    burn = float(budget.get("burn_frac_per_h") or 0)
    per = burn / live if live and burn > 0 else float(conf["per_session_frac_per_h"])
    derived = int(math.floor(allowed / per + 1e-9)) if per > 0 else cap
    return min(cap, derived), f"min(cap {cap}, derived {derived} = {allowed:.4f}/h allowed / {per:.4f}/h per session)"
