"""Task synthesizer — composes verifiable Agent-World tasks (NIB2-44 AW-1).

A ``SynthesizedTask`` bundles:

  environment_id       link back to the discovery provenance
  tool_set             the MCP tools the agent may use
  prompt               the task statement
  difficulty_band      easy | medium | hard (tool-call count + chain depth)
  verifier             a VerifierSpec — scored by the built scorer
  ground_truth_hint    optional hint string (used by the solvability gate)
  metadata             free-form (distractors, expected tool-call count, …)

The synthesizer is LLM-backed: the caller injects an ``llm`` callable
that accepts a system+user pair and returns a JSON string with the task
fields. A seed-based deterministic ``FakeLLM`` is provided for tests so
the rest of the species can be validated without real inference.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

from scripts.autopilot.species.env_synth.boundary_contract import (
    HypothesisBoundaryContract,
)
from scripts.autopilot.species.env_synth.mcp_tool_registry import MCPToolEntry
from scripts.autopilot.species.env_synth.verifier_builder import (
    VerifierBuilder,
    VerifierSpec,
    VerifierType,
)
from src.structured_output.repair import (
    AsyncCompleteFn,
    RepairResult,
    fish_json,
    parse_with_repair_async,
)

log = logging.getLogger("autopilot.env_synth.task_synthesizer")

# TD-21.26: the synthesized-task shape `_build_task` already requires
# downstream -- `prompt` is the only hard requirement (an empty prompt is
# rejected outright); `verifier`/`ground_truth_hint`/`metadata` are read
# defensively (`payload.get(...) or {}`/`""`) and, for the boundary-task
# path, the caller's OWN trusted verifier/hint override whatever the model
# proposes there anyway. Derived from `_parse`'s own field reads below, not
# invented -- nested `verifier` field validity is `_build_verifier`'s job,
# not the fish/repair schema's.
_TASK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "prompt": {"type": "string"},
        "verifier": {"type": "object"},
        "ground_truth_hint": {"type": "string"},
        "metadata": {"type": "object"},
    },
    "required": ["prompt"],
}

_TASK_REPAIR_INSTRUCTION = (
    "Convert the reply, given as the user message, into ONE JSON object "
    "with exactly these keys: prompt (the task statement), verifier (an "
    "object with a type field plus whichever of reference/pattern/"
    "allowlist/case_sensitive/min_tokens that type needs), "
    "ground_truth_hint (a string), and metadata (an object). Copy the "
    "reply's own wording and values faithfully -- never invent a task, "
    "verifier, or hint that is not already present in the reply. Respond "
    "with the JSON object only, no commentary and no markdown fence."
)


def _llm_as_complete(llm: "LLMCall") -> AsyncCompleteFn:
    """TD-21.26: adapt the species' injected ``llm(system, user) -> str``
    callable into the shared repair module's ``AsyncCompleteFn`` shape
    (``complete(messages, schema) -> str``).

    ``LLMCall`` has no schema/``response_format`` parameter at all -- unlike
    ``http_chat_completer``, this transport cannot ask the server to
    constrain decoding, so the schema is carried entirely in the system
    message text (``_TASK_REPAIR_INSTRUCTION`` / the ETD equivalent) and
    enforced only client-side by ``parse_with_repair_async``'s validator.
    That is strictly better than the pre-TD-21.26 behaviour (a bare
    ``json.loads`` with a from-zero regeneration on any miss), not a
    regression: an off-schema repair reply is still a typed ``"failed"``,
    never smuggled through as valid.
    """

    async def complete(messages: Any, _schema: Any) -> str:
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        return await llm(system, user)

    return complete


class DifficultyBand(str, Enum):
    EASY = "easy"  # 1-2 tool calls, linear chain
    MEDIUM = "medium"  # 3-5 tool calls, some branching
    HARD = "hard"  # 6+ tool calls, branching + distractors


_BAND_TOOL_CALLS = {
    DifficultyBand.EASY: (1, 2),
    DifficultyBand.MEDIUM: (3, 5),
    DifficultyBand.HARD: (6, 10),
}


@dataclass
class SynthesizedTask:
    environment_id: str
    tool_set: list[str]  # tool_ids from the registry
    prompt: str
    difficulty_band: DifficultyBand
    verifier: VerifierSpec
    ground_truth_hint: str = ""
    expected_tool_calls: tuple[int, int] = (1, 2)
    metadata: dict[str, Any] = field(default_factory=dict)
    boundary_contract: Optional[HypothesisBoundaryContract] = None


LLMCall = Callable[[str, str], Awaitable[str]]


@dataclass
class TaskSynthesizer:
    """Compose tasks for a given (environment, tool_subset) with a
    requested difficulty band. Caller injects ``llm`` — a FakeLLM is
    provided below for offline scaffolding / tests.
    """

    llm: LLMCall
    max_retries: int = 2

    async def synthesize(
        self,
        environment_id: str,
        tools: list[MCPToolEntry],
        band: DifficultyBand,
        *,
        seed: Optional[int] = None,
    ) -> Optional[SynthesizedTask]:
        """Produce one verifiable task, or ``None`` if synthesis fails."""
        if not tools:
            log.warning("task_synthesizer: empty tool set for env %s", environment_id)
            return None

        system = (
            "You are a synthetic-task generator for an Agent-World environment. "
            "Given a list of tools and a difficulty band, produce ONE verifiable "
            "task. Respond with a single JSON object containing keys: "
            "prompt, verifier (type in {regex, exact_match, f1}; reference; "
            "pattern; allowlist), ground_truth_hint, metadata. "
            "Reject vague or unverifiable tasks — the verifier MUST be cheap and "
            "deterministic."
        )

        tool_section = "\n".join(f"- {t.tool_id}: {t.name} — {t.description[:120]}" for t in tools)
        user = (
            f"Environment: {environment_id}\n"
            f"Difficulty band: {band.value}\n"
            f"Tool call count target: {_BAND_TOOL_CALLS[band]}\n"
            f"Tools available:\n{tool_section}\n\n"
            "Generate the JSON task."
        )

        complete = _llm_as_complete(self.llm)
        for attempt in range(self.max_retries + 1):
            try:
                raw = await self.llm(system, user)
                # TD-21.26: fish (tolerant) then, on a miss, ONE repair turn
                # against the SAME injected model before falling back to a
                # from-zero regeneration -- the retry-from-zero cost DS41
                # measured on every non-JSON reply.
                task = await self._parse_with_repair(
                    raw,
                    complete=complete,
                    environment_id=environment_id,
                    tool_set=[t.tool_id for t in tools],
                    band=band,
                    seed=seed,
                )
                if task is not None:
                    return task
            except Exception as e:
                log.warning(
                    "synthesize attempt %d/%d failed: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    e,
                )
        return None

    async def synthesize_boundary(
        self,
        environment_id: str,
        tools: list[MCPToolEntry],
        band: DifficultyBand,
        *,
        boundary: HypothesisBoundaryContract,
        verifier: VerifierSpec,
        ground_truth_hint: str,
        seed: Optional[int] = None,
    ) -> Optional[SynthesizedTask]:
        """Compose one AW-10 task while keeping labels/verifiers out of planner prose.

        The controller supplies the immutable boundary and verifier. The LLM may
        phrase a prompt, but any verifier it returns is ignored.
        """
        if not tools:
            return None
        VerifierBuilder.build(verifier)
        if not isinstance(ground_truth_hint, str) or not ground_truth_hint.strip():
            raise ValueError("ground_truth_hint: controller-supplied label is required")
        system = (
            "Phrase ONE task at the supplied hypothesis disagreement boundary. "
            "Return JSON keys prompt, ground_truth_hint, and metadata only. The "
            "controller already owns the label and verifier; do not invent either."
        )
        tool_section = "\n".join(
            f"- {tool.tool_id}: {tool.name} — {tool.description[:120]}" for tool in tools
        )
        user = (
            f"Environment: {environment_id}\n"
            f"Difficulty band: {band.value}\n"
            f"Boundary contract: {json.dumps(boundary.to_dict(), sort_keys=True)}\n"
            f"Tools available:\n{tool_section}\n\nGenerate the JSON task."
        )
        complete = _llm_as_complete(self.llm)
        for attempt in range(self.max_retries + 1):
            try:
                raw = await self.llm(system, user)
                task = await self._parse_with_repair(
                    raw,
                    complete=complete,
                    environment_id=environment_id,
                    tool_set=[tool.tool_id for tool in tools],
                    band=band,
                    seed=seed,
                    trusted_verifier=verifier,
                    trusted_ground_truth_hint=ground_truth_hint,
                    boundary=boundary,
                )
                if task is not None:
                    return task
            except Exception as exc:  # noqa: BLE001 -- injected LLM boundary
                log.warning(
                    "boundary synthesize attempt %d/%d failed: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )
        return None

    # ── parsing ────────────────────────────────────────────────────

    async def _parse_with_repair(
        self,
        raw: str,
        *,
        complete: AsyncCompleteFn,
        environment_id: str,
        tool_set: list[str],
        band: DifficultyBand,
        seed: Optional[int],
        trusted_verifier: Optional[VerifierSpec] = None,
        trusted_ground_truth_hint: Optional[str] = None,
        boundary: Optional[HypothesisBoundaryContract] = None,
    ) -> Optional[SynthesizedTask]:
        """TD-21.26: fish first (byte-identical happy path, 0 repair calls);
        on a miss, ONE repair turn against the caller's own injected ``llm``
        before the outer loop resorts to a from-zero regeneration."""
        kwargs = dict(
            environment_id=environment_id,
            tool_set=tool_set,
            band=band,
            seed=seed,
            trusted_verifier=trusted_verifier,
            trusted_ground_truth_hint=trusted_ground_truth_hint,
            boundary=boundary,
        )
        task = self._parse(raw, **kwargs)
        if task is not None:
            return task

        result: RepairResult = await parse_with_repair_async(
            raw,
            schema=_TASK_SCHEMA,
            complete=complete,
            instruction=_TASK_REPAIR_INSTRUCTION,
            site="env_synth.task_synthesizer",
            kind="object",
            # TD-21.34: the instruction already says "never invent a task,
            # verifier, or hint that is not already present" -- prompt/
            # reference/pattern/allowlist/min_tokens/ground_truth_hint are all
            # facts that must come from the reply. `verifier.type` is exempt:
            # it is a 3-way classification (VerifierType: regex/exact_match/
            # f1) the model maps its own verifier design onto, which the
            # reply's prose essentially never spells verbatim.
            require_evidence=True,
            evidence_exempt={"verifier.type"},
        )
        if result.status not in ("parsed", "repaired"):
            log.warning(
                "task synthesizer: repair turn did not recover a valid task (%s): %s",
                result.status, result.reason,
            )
            return None
        return self._build_task(result.value, **kwargs)

    def _parse(
        self,
        raw: str,
        *,
        environment_id: str,
        tool_set: list[str],
        band: DifficultyBand,
        seed: Optional[int],
        trusted_verifier: Optional[VerifierSpec] = None,
        trusted_ground_truth_hint: Optional[str] = None,
        boundary: Optional[HypothesisBoundaryContract] = None,
    ) -> Optional[SynthesizedTask]:
        """TD-21.26: deterministic fish (fence-aware + string-aware balanced-
        bracket fallback, kind="object" so only a dict counts) in place of the
        old bare ``json.loads`` -- a fenced or trailing-prose reply now parses
        without needing a repair turn or a from-zero regeneration at all."""
        payload = fish_json(raw, kind="object")
        if payload is None:
            log.warning("task synthesizer: non-JSON LLM output")
            return None
        return self._build_task(
            payload,
            environment_id=environment_id,
            tool_set=tool_set,
            band=band,
            seed=seed,
            trusted_verifier=trusted_verifier,
            trusted_ground_truth_hint=trusted_ground_truth_hint,
            boundary=boundary,
        )

    def _build_task(
        self,
        payload: dict[str, Any],
        *,
        environment_id: str,
        tool_set: list[str],
        band: DifficultyBand,
        seed: Optional[int],
        trusted_verifier: Optional[VerifierSpec] = None,
        trusted_ground_truth_hint: Optional[str] = None,
        boundary: Optional[HypothesisBoundaryContract] = None,
    ) -> Optional[SynthesizedTask]:
        """Build a ``SynthesizedTask`` from an already-parsed payload dict --
        shared by the fish path (``_parse``) and the TD-21.26 repair path
        (``_parse_with_repair``) so verifier-building/validation is identical
        either way."""
        prompt = (payload.get("prompt") or "").strip()
        if not prompt:
            return None

        verifier = trusted_verifier or self._build_verifier(payload.get("verifier") or {})
        if verifier is None:
            return None

        return SynthesizedTask(
            environment_id=environment_id,
            tool_set=tool_set,
            prompt=prompt,
            difficulty_band=band,
            verifier=verifier,
            ground_truth_hint=(
                trusted_ground_truth_hint
                if trusted_ground_truth_hint is not None
                else (payload.get("ground_truth_hint") or "").strip()
            ),
            expected_tool_calls=_BAND_TOOL_CALLS[band],
            metadata={
                "seed": seed,
                "raw_metadata": payload.get("metadata") or {},
            },
            boundary_contract=boundary,
        )

    @staticmethod
    def _build_verifier(data: dict[str, Any]) -> Optional[VerifierSpec]:
        type_str = (data.get("type") or "").lower()
        try:
            vtype = VerifierType(type_str)
        except ValueError:
            log.warning("unknown verifier type %s", type_str)
            return None
        spec = VerifierSpec(
            type=vtype,
            reference=data.get("reference", ""),
            pattern=data.get("pattern", ""),
            allowlist=list(data.get("allowlist", []) or []),
            case_sensitive=bool(data.get("case_sensitive", False)),
            min_tokens=int(data.get("min_tokens", 1)),
        )
        try:
            VerifierBuilder.build(spec)  # raises on degenerate spec
        except ValueError as e:
            log.warning("verifier validation failed: %s", e)
            return None
        return spec


# ── fake LLM for offline scaffolding + tests ────────────────────────


def make_fake_llm(
    verifier_type: VerifierType = VerifierType.EXACT_MATCH,
    reference: str = "42",
    pattern: str = "",
    rng: Optional[random.Random] = None,
) -> LLMCall:
    """Deterministic fake LLM that returns a valid JSON task payload.

    Useful for tests + smoke runs without live inference.
    """
    rng = rng or random.Random(0)

    async def _llm(system: str, user: str) -> str:
        topic = f"topic_{rng.randint(0, 9999)}"
        payload: dict[str, Any] = {
            "prompt": f"Using the provided tools, compute the expected answer for {topic}.",
            "verifier": {
                "type": verifier_type.value,
                "reference": reference,
                "pattern": pattern or r"^\d+$",
                "allowlist": [],
                "case_sensitive": False,
                "min_tokens": 1,
            },
            "ground_truth_hint": reference,
            "metadata": {"topic": topic},
        }
        return json.dumps(payload)

    return _llm
