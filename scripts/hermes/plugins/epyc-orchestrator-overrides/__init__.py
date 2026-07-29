"""Hermes plugin: deterministic EPYC orchestrator request overrides."""

from __future__ import annotations

from typing import Any

_SESSION_OVERRIDES: dict[str, dict[str, Any]] = {}

_ROLE_MAP = {
    "architect": "architect_general",
    "biggest": "architect_general",
    "frontdoor": "frontdoor",
    "worker": "worker_general",
}

_ESCALATION_MAP = {
    "off": "A",
    "a": "A",
    "b1": "B1",
    "b2": "B2",
    "full": None,
    "auto": None,
}


def _session_key(context: dict[str, Any] | None = None, **kwargs: Any) -> str:
    data = dict(context or {})
    data.update({k: v for k, v in kwargs.items() if v is not None})

    session_id = data.get("session_id")
    if session_id:
        return str(session_id)

    agent = data.get("agent")
    if agent is not None:
        agent_session = getattr(agent, "session_id", None)
        if agent_session:
            return str(agent_session)

    event = data.get("event")
    if event is not None:
        event_session = getattr(event, "session_id", None)
        if event_session:
            return str(event_session)

    return "default"


def _overrides_for(session: str) -> dict[str, Any]:
    return _SESSION_OVERRIDES.setdefault(session, {})


def _clear_role_overrides(overrides: dict[str, Any]) -> None:
    overrides.pop("x_orchestrator_role", None)
    overrides.pop("x_force_model", None)


def _format_overrides(overrides: dict[str, Any]) -> str:
    if not overrides:
        return "auto"
    parts = [f"{key}={value!r}" for key, value in sorted(overrides.items())]
    return ", ".join(parts)


def _handle_use(args: str, context: dict[str, Any] | None = None) -> str:
    choice = (args or "").strip().lower()
    if not choice:
        return "Usage: /use architect|biggest|frontdoor|worker|auto"

    session = _session_key(context)
    overrides = _overrides_for(session)

    if choice == "auto":
        _clear_role_overrides(overrides)
        return f"EPYC role override cleared for session {session}."

    role = _ROLE_MAP.get(choice)
    if role is None:
        return "Usage: /use architect|biggest|frontdoor|worker|auto"

    _clear_role_overrides(overrides)
    overrides["x_orchestrator_role"] = role
    return f"EPYC role override set: x_orchestrator_role={role!r}."


def _handle_escalation(args: str, context: dict[str, Any] | None = None) -> str:
    choice = (args or "").strip().lower()
    if not choice:
        return "Usage: /escalation off|B1|B2|full"

    session = _session_key(context)
    overrides = _overrides_for(session)

    if choice not in _ESCALATION_MAP:
        return "Usage: /escalation off|B1|B2|full"

    value = _ESCALATION_MAP[choice]
    if value is None:
        overrides.pop("x_max_escalation", None)
        return f"EPYC escalation override cleared for session {session}."

    overrides["x_max_escalation"] = value
    return f"EPYC escalation cap set: x_max_escalation={value!r}."


def _handle_nocode(args: str, context: dict[str, Any] | None = None) -> str:
    choice = (args or "").strip().lower()
    session = _session_key(context)
    overrides = _overrides_for(session)

    if choice in {"", "on", "true"}:
        overrides["x_disable_repl"] = True
        return "EPYC REPL execution disabled for this session."

    if choice in {"off", "false", "auto"}:
        overrides.pop("x_disable_repl", None)
        return f"EPYC REPL override cleared for session {session}."

    return "Usage: /nocode [off]"


def _handle_epyc_status(args: str, context: dict[str, Any] | None = None) -> str:
    session = _session_key(context)
    return f"EPYC overrides for session {session}: {_format_overrides(_overrides_for(session))}"


def _inject_overrides(**kwargs: Any) -> None:
    session = _session_key(kwargs)
    overrides = _SESSION_OVERRIDES.get(session) or _SESSION_OVERRIDES.get("default")
    if not overrides:
        return

    api_kwargs = kwargs.get("api_kwargs")
    if not isinstance(api_kwargs, dict):
        return

    extra_body = api_kwargs.setdefault("extra_body", {})
    if isinstance(extra_body, dict):
        extra_body.update(overrides)


def register(ctx) -> None:
    ctx.register_command(
        name="use",
        handler=_handle_use,
        description="Force an EPYC orchestrator role for this Hermes session",
        args_hint="architect|biggest|frontdoor|worker|auto",
    )
    ctx.register_command(
        name="escalation",
        handler=_handle_escalation,
        description="Cap or clear EPYC orchestrator escalation for this Hermes session",
        args_hint="off|B1|B2|full",
    )
    ctx.register_command(
        name="nocode",
        handler=_handle_nocode,
        description="Disable or restore EPYC orchestrator REPL execution",
        args_hint="[off]",
    )
    ctx.register_command(
        name="epyc-overrides",
        handler=_handle_epyc_status,
        description="Show active EPYC orchestrator overrides for this Hermes session",
        args_hint="",
        aliases=("epyc-routing",),
    )
    ctx.register_hook("pre_llm_call", _inject_overrides)
