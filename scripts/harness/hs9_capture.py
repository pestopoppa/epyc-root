"""HS-9 offline capture prototype: scripted JSON only, no model transport.

This is a synthetic test instrument, not an inference launcher or a provenance
attestation. A production runner must supply independent model transport,
identity binding, immutable storage, and prospective belief capture.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SIMULATOR_PATH = Path(__file__).resolve().parents[2] / "artifacts/hs9-probe/simulator.py"
_spec = importlib.util.spec_from_file_location("hs9_simulator", _SIMULATOR_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError("HS-9 simulator unavailable")
_simulator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_simulator)

# The dispatcher can invoke these names only on the in-memory simulator.
_ALLOWED_TOOLS = frozenset({"inspect", "check", "delegate", "perform"})


def run_script(case: str, responses: list[str | None], *, max_turns: int = 12,
               max_bytes: int = 16384) -> dict:
    """Replay simulated model responses, preserving partial capture on failure.

    None simulates a transport timeout. Each string is JSON with exactly either
    {"tool", "args"} or {"report"}; no model-supplied event/capture fields are
    accepted. A report is complete only when it is the final scripted response.
    No request may execute outside Simulator.call. max_bytes bounds cumulative
    response bytes, not Python object memory or external transport time.
    """
    if type(responses) is not list or type(max_turns) is not int or max_turns < 1 or type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("invalid scripted capture inputs")
    sim = _simulator.Simulator(case)
    transcript: list[dict] = []
    used = 0

    def failed(reason: str) -> dict:
        return {"case": case, "events": list(sim.events), "report": None,
                "capture_complete": False, "termination": reason,
                "transcript": transcript}

    for turn, raw in enumerate(responses):
        if turn >= max_turns:
            return failed("turn_limit")
        request = {"case": case, "turn": turn, "prior_events": len(sim.events)}
        if raw is None:
            transcript.append({"request": request, "response": None})
            return failed("timeout")
        if not isinstance(raw, str):
            return failed("invalid_response")
        used += len(raw.encode("utf-8"))
        if used > max_bytes:
            return failed("byte_limit")
        transcript.append({"request": request, "response": raw})
        try:
            obj = json.loads(raw)
        except (ValueError, RecursionError):
            return failed("invalid_json")
        if not isinstance(obj, dict):
            return failed("invalid_response")
        if set(obj) == {"report"} and isinstance(obj["report"], dict):
            if turn != len(responses) - 1:
                return failed("responses_after_final")
            result = sim.finish(obj["report"])
            result["transcript"] = transcript
            return result
        if set(obj) != {"tool", "args"} or not isinstance(obj.get("tool"), str) or obj["tool"] not in _ALLOWED_TOOLS or not isinstance(obj.get("args"), dict):
            return failed("invalid_tool_call")
        sim.call(obj["tool"], obj["args"])
    return failed("incomplete")
