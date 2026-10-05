"""Compile model-capability descriptors from orchestrator registries."""

from __future__ import annotations

import argparse
import copy
import hashlib
import re
import subprocess
import sys
from datetime import datetime, date, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_LEAN_REGISTRY = _REPO_ROOT / "orchestration/model_registry.yaml"
DEFAULT_RESEARCH_REGISTRY = Path(
    "/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml"
)
DEFAULT_DESCRIPTOR_OUTPUT = _REPO_ROOT / "orchestration/model_descriptors.yaml"


class DescriptorCompileError(ValueError):
    """Descriptor compilation found missing load-bearing evidence."""

    def __init__(self, missing_by_model: dict[str, list[str]]) -> None:
        self.missing_by_model = missing_by_model
        lines = ["Descriptor compilation refused incomplete model descriptors:"]
        for model_id, gaps in sorted(missing_by_model.items()):
            for gap in gaps:
                lines.append(f"  - {model_id}: {gap}")
        super().__init__("\n".join(lines))


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} did not parse to a mapping")
    return loaded


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML file that must parse to a mapping."""
    return _load_yaml(path)


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_commit(path: Path) -> str | None:
    for parent in (path if path.is_dir() else path.parent).resolve().parents:
        if (parent / ".git").exists():
            try:
                return subprocess.check_output(
                    ["git", "-C", str(parent), "rev-parse", "--short", "HEAD"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            except (OSError, subprocess.CalledProcessError):
                return None
    return None


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _coerce_scalar(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        match = re.search(r"(\d+(?:\.\d+)?)", stripped)
        if match:
            return float(match.group(1))
    return None


def _as_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            parsed = int(stripped)
            return parsed if parsed > 0 else None
    return None


def _score_fraction(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("pct", "percent", "percentage", "raw"):
            if key in value:
                score = _score_fraction(value.get(key))
                if score is not None:
                    return score
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number / 100.0 if number > 1.0 else number
    if isinstance(value, str):
        frac = re.search(r"(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)", value)
        if frac and float(frac.group(2)):
            return round(float(frac.group(1)) / float(frac.group(2)), 4)
        pct = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
        if pct:
            return round(float(pct.group(1)) / 100.0, 4)
    return None


def _canonical_slug(value: str) -> str:
    value = value.rsplit("/", 1)[-1]
    value = re.sub(r"\.gguf$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"-0+\d+-of-0+\d+$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"[^A-Za-z0-9._]+", "-", value).strip("-").lower()
    value = re.sub(r"-+", "-", value)
    return value


def _canonical_model_id(name: str, quant: str | None) -> str:
    base = name.rsplit("/", 1)[-1]
    base = re.sub(r"\.gguf$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"-0+\d+-of-0+\d+$", "", base, flags=re.IGNORECASE)
    if quant:
        base = re.sub(rf"[-_]?{re.escape(quant)}$", "", base, flags=re.IGNORECASE)
    slug = _canonical_slug(base)
    slug = re.sub(r"-(instruct|it|assistant)$", "", slug)
    slug = re.sub(r"^gemma-(\d)", r"gemma\1", slug)
    if quant:
        slug = f"{slug}-{_canonical_slug(quant)}"
    return slug


def _first_model_dict(*configs: dict[str, Any] | None) -> dict[str, Any]:
    for cfg in configs:
        if not isinstance(cfg, dict):
            continue
        model = cfg.get("model")
        if isinstance(model, dict):
            return model
    return {}


def _first_model_name(*configs: dict[str, Any] | None) -> str | None:
    model = _first_model_dict(*configs)
    if model.get("name"):
        return str(model["name"])
    for cfg in configs:
        if not isinstance(cfg, dict):
            continue
        for key in ("model", "model_path"):
            value = cfg.get(key)
            if isinstance(value, str):
                return value.rsplit("/", 1)[-1]
    return None


def _quant_from(name: str | None, model: dict[str, Any]) -> str | None:
    if model.get("quant"):
        return str(model["quant"])
    if not name:
        return None
    match = re.search(
        r"(Q\d_K_[A-Z0-9]+|Q\d_K_[A-Z]+|Q\d_K_M|Q\d_K_S|Q\d_0|Q\d(?:_[0-9])?|f16|fp16)",
        name,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else None


def _params_from(name: str | None, model: dict[str, Any]) -> float | None:
    size = model.get("params_b")
    if size is not None:
        return _as_float(size)
    if not name:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)B", name, flags=re.IGNORECASE)
    return float(match.group(1)) if match else None


def _active_from(name: str | None, arch: str | None, params_b: float | None) -> float | None:
    if name:
        match = re.search(r"A(\d+(?:\.\d+)?)B", name, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    if arch and "dense" in arch.lower():
        return params_b
    return None


def _family_from(model_id: str, params_b: float | None) -> str:
    if params_b is None:
        return model_id
    marker = f"{params_b:g}b"
    parts = model_id.split("-")
    family: list[str] = []
    for part in parts:
        if part == marker:
            break
        family.append(part)
    return "-".join(family) if family else model_id


def _server_for_role(
    role: str,
    server_mode: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None, str | None]:
    direct = server_mode.get(role)
    if isinstance(direct, dict):
        return role, direct, None

    for server_role, cfg in server_mode.items():
        if not isinstance(cfg, dict):
            continue
        if cfg.get("model_role") == role:
            return str(server_role), cfg, None
        shared = cfg.get("shared_with")
        if isinstance(shared, list) and role in shared:
            return str(server_role), cfg, "shared_with"
    return None, None, None


def _model_id_from_configs(*configs: dict[str, Any] | None) -> str | None:
    model_name = _first_model_name(*configs)
    if not model_name:
        return None
    model = _first_model_dict(*configs)
    return _canonical_model_id(model_name, _quant_from(model_name, model))


def _expanded_active_roles(
    active_roles: set[str] | None,
    registry: dict[str, Any],
) -> set[str]:
    roles = set(active_roles or set())
    server_mode = registry.get("server_mode") or {}
    top_roles = registry.get("roles") or {}
    if not roles:
        roles.update(
            key
            for key, value in server_mode.items()
            if isinstance(value, dict) and value.get("model")
        )
    for cfg in server_mode.values():
        if not isinstance(cfg, dict):
            continue
        model_role = cfg.get("model_role")
        if model_role and model_role in top_roles:
            roles.add(str(model_role))
        shared = cfg.get("shared_with")
        if isinstance(shared, list):
            roles.update(str(item) for item in shared)
    return roles


def _registry_date(*configs: dict[str, Any] | None) -> Any:
    for cfg in configs:
        if not isinstance(cfg, dict):
            continue
        value = cfg.get("benchmark_date")
        if value is not None:
            return _coerce_scalar(value)
        performance = cfg.get("performance")
        if isinstance(performance, dict) and performance.get("benchmark_date") is not None:
            return _coerce_scalar(performance["benchmark_date"])
    return None


# Domain words that, when they appear in a registry benchmark_score string,
# mean the number describes ONE domain rather than the whole canonical suite.
# Keyed by the suite_vector name the score belongs under instead of "overall".
_BENCHMARK_DOMAIN_WORDS: tuple[tuple[str, str], ...] = (
    ("long_context", "long_context"),
    ("long-context", "long_context"),
    ("vision", "vision_language"),
    ("mmmu", "vision_language"),
    ("swe-bench", "swe_verified"),
    ("swe_verified", "swe_verified"),
    ("tool_compliance", "tool_compliance"),
)


def _benchmark_domain_qualifier(raw: Any) -> str | None:
    """Return the suite key a benchmark_score is scoped to, or None if whole-suite.

    A benchmark_score is free text ("25/27 (93%) on canonical long_context
    suite"). When it names its own scope, that scope — not "overall" — is where
    the number belongs.
    """
    if not isinstance(raw, str):
        return None
    lowered = raw.lower()
    for word, suite_key in _BENCHMARK_DOMAIN_WORDS:
        if word in lowered:
            return suite_key
    return None


_PUBLIC_BENCHMARKS_PATH = (
    Path(__file__).resolve().parents[2] / "orchestration" / "public_benchmarks.yaml"
)


@lru_cache(maxsize=1)
def _public_benchmarks() -> dict[str, Any]:
    """Load vendor-reported / leaderboard results. Missing file is NOT fatal.

    Absence yields an empty mapping so descriptors still compile, but the
    per-model record then carries no `public` block at all rather than an
    empty-looking one — a consumer can distinguish "no public data" from
    "public data says zero".
    """
    try:
        data = yaml.safe_load(_PUBLIC_BENCHMARKS_PATH.read_text()) or {}
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"{_PUBLIC_BENCHMARKS_PATH} exists but did not parse: {exc!r}. "
            "Refusing to compile descriptors against a half-read benchmark file."
        ) from exc
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def _rankable_benchmarks() -> frozenset[str]:
    """Benchmarks at least TWO fleet models report — the only ones that can rank.

    MEASURED from the data, not declared. A benchmark only one model reports
    says nothing about that model's standing: Qwen3-Next-80B's RULER-1M 0.918
    looks like a commanding long-context number and is comparable to precisely
    nothing, because every other model reports a different long-context suite.
    Using it to rank would be the mixed-instrument defect wearing an axis name.
    """
    counts: dict[str, int] = {}
    for record in (_public_benchmarks().get("models") or {}).values():
        if not isinstance(record, dict):
            continue
        for field in ("benchmarks", "local_benchmarks"):
            for key in record.get(field) or {}:
                counts[key] = counts.get(key, 0) + 1
    return frozenset(k for k, n in counts.items() if n >= 2)


def _merged_benchmarks(record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Pool vendor and locally-measured benchmarks, keeping provenance PER KEY.

    Provenance cannot be a per-model flag once both kinds coexist: the same
    model carries vendor-reported bf16 figures AND numbers we measured on this
    stack at Q8_0/Q4_K_M with thinking off. Recording provenance per benchmark
    is what lets a reader see that `mmlu_pro` is a vendor claim while
    `tool_compliance_local` is ours, instead of one label covering both.

    Local wins a key collision: a number measured on the deployed configuration
    describes this stack better than the upstream claim about a different one.
    """
    merged: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for key, value in (record.get("benchmarks") or {}).items():
        merged[key] = value
        provenance[key] = str(record.get("provenance") or "vendor_reported")
    for key, value in (record.get("local_benchmarks") or {}).items():
        merged[key] = value
        provenance[key] = "measured_local"
    return merged, provenance


def resolve_role_quality(
    capabilities: list[str],
    benchmarks: dict[str, Any],
    overall: float | None,
) -> dict[str, Any]:
    """Pick the quality figure a ROLE should be judged on.

    Walks the role's declared capabilities in order, takes the first axis that
    is both relevant and RANKABLE, and returns the best benchmark on it. Falls
    back to the universal aggregate — recording why — when no preferred axis
    can rank. Returns basis text in every branch so a consumer never sees a
    bare float whose provenance it cannot state.
    """
    data = _public_benchmarks()
    axis_of = data.get("axes") or {}
    cap_axes = data.get("capability_axes") or {}
    rankable = _rankable_benchmarks()

    preferred: list[str] = []
    for capability in capabilities:
        for axis in cap_axes.get(capability) or []:
            if axis not in preferred:
                preferred.append(axis)

    unrankable_seen: list[str] = []
    for axis in preferred:
        on_axis = {k: v for k, v in benchmarks.items() if axis_of.get(k) == axis}
        if not on_axis:
            continue
        usable = {k: v for k, v in on_axis.items() if k in rankable}
        cross_model_rankable = bool(usable)
        if not usable:
            # USE the value anyway, flagged. Vendors publish different
            # long-context suites (RULER-1M / LongBench-v2 / AA-LCR / MRCR-v2,
            # one model each), so `long_context` can never rank the fleet — but
            # RULER 0.918 is still the best available evidence that
            # ingest_long_context is good at the job it exists for. Withholding
            # it would leave the role scored on `reasoning`, which is worse
            # evidence about its actual function.
            #
            # `rankable: false` is what keeps this honest: the value answers
            # "is this role fit for its purpose", and `comparable_value` below
            # answers "how does it rank against other models". Conflating those
            # two questions in one float is the original defect.
            unrankable_seen.append(f"{axis}({'/'.join(sorted(on_axis))})")
            usable = on_axis
        key = sorted(usable)[0]
        value = usable[key]
        if not isinstance(value, (int, float)):
            continue
        # Carry the skipped-axis note even on SUCCESS. ingest_long_context
        # prefers `long_context` and lands on `reasoning`; without this the
        # basis reads "role-relevant axis reasoning" and silently conceals that
        # the axis the role actually exists for could not rank the fleet.
        note = ""
        if not cross_model_rankable:
            note = (
                " — NOT cross-model comparable (no two fleet models share a "
                "benchmark on this axis); use comparable_value to rank"
            )
        elif unrankable_seen:
            note = (
                "; skipped higher-priority " + ", ".join(unrankable_seen)
                + " for the same reason"
            )
        return {
            "value": round(float(value), 4),
            "axis": axis,
            "benchmark": key,
            # Fitness for THIS role's job.
            "rankable": cross_model_rankable,
            # Always cross-model comparable: the universal-benchmark aggregate.
            # A consumer ranking models reads this; a consumer asking "is this
            # role good at its job" reads `value`. These are different
            # questions and a single float cannot answer both.
            "comparable_value": overall,
            "skipped_axes": list(unrankable_seen),
            "basis": f"role-relevant axis {axis} via {key}{note}",
        }

    note = ""
    if unrankable_seen:
        note = (
            "; preferred " + ", ".join(unrankable_seen)
            + " present but NOT rankable (fewer than two fleet models share a "
            "benchmark on that axis)"
        )
    if overall is None:
        return {
            "value": None,
            "axis": None,
            "benchmark": None,
            "rankable": False,
            "basis": "no rankable role axis and no universal aggregate" + note,
        }
    return {
        "value": overall,
        "axis": None,
        "benchmark": None,
        "rankable": True,
        "basis": "universal aggregate (no rankable role-specific axis)" + note,
    }


def _public_quality(model_id: str | None) -> dict[str, Any] | None:
    """The public-benchmark record for one model, keyed by BENCHMARK not axis.

    Deliberately returns benchmark-keyed values plus the conditions they were
    produced under. Two values are comparable iff they share a benchmark key;
    `axes` is carried alongside purely so a role can select the benchmarks
    relevant to it, never so that values can be pooled across an axis.
    """
    if not model_id:
        return None
    data = _public_benchmarks()
    record = (data.get("models") or {}).get(model_id)
    if not isinstance(record, dict):
        return None
    merged, per_key_provenance = _merged_benchmarks(record)
    out = {
        "benchmarks": merged,
        "benchmark_provenance": per_key_provenance,
        "provenance": record.get("provenance"),
        "reported_precision": record.get("reported_precision"),
        "served_precision": record.get("served_precision"),
        "reported_mode": record.get("reported_mode"),
        "source_url": record.get("source_url"),
        "absent_from_card": list(record.get("absent_from_card") or []),
        "retrieved": data.get("retrieved"),
        "axes": dict(data.get("axes") or {}),
        "universal_keys": list(data.get("universal_keys") or []),
    }
    if record.get("local_corroboration"):
        out["local_corroboration"] = copy.deepcopy(record["local_corroboration"])
    return out


def _quality(
    role_cfg: dict[str, Any],
    server_cfg: dict[str, Any] | None,
    model_id: str | None = None,
) -> dict[str, Any]:
    suite_vector: dict[str, float] = {}
    performance = role_cfg.get("performance") if isinstance(role_cfg, dict) else None
    if isinstance(performance, dict):
        for key, value in performance.items():
            score = None
            if key.endswith("_pct") or key in {"quality_score", "vl_score", "long_context_quality"}:
                score = _score_fraction(value)
            elif key.endswith("_suite") or key == "long_context":
                score = _score_fraction(value)
            if score is not None:
                suite_key = key
                if key in {"quality_pct", "quality_score"}:
                    suite_key = "overall"
                elif key == "vl_score":
                    suite_key = "vision_language"
                elif key == "long_context_quality":
                    suite_key = "long_context"
                elif key.endswith("_suite"):
                    suite_key = key.removesuffix("_suite")
                elif key.endswith("_pct"):
                    suite_key = key.removesuffix("_pct")

                suite_vector[suite_key] = score
                # DELIBERATELY no promotion to "overall" here.
                #
                # This used to read:
                #     if key in {"long_context_quality", "vl_score"} and ...:
                #         suite_vector["overall"] = score
                # which manufactured a whole-model quality figure out of a
                # SINGLE-DOMAIN score. It is how Qwen3-Next-80B carried
                # overall=0.9259 from a 27-question long-context suite and
                # Qwen3-VL-30B carried overall=0.636 from MMMU — a vision
                # benchmark — into `priors.quality_overall`, the scalar the
                # router reads. A domain score is evidence ABOUT a domain; it
                # is not an aggregate, and nothing downstream could tell the
                # difference once it was named "overall".
                #
                # Qwen3.6-27B already demonstrated the correct behaviour by
                # accident: it carries swe_verified with no overall, so it
                # compiles to quality_overall=null. Null is the honest value
                # when no whole-suite measurement exists.

    # performance.general_suite_quality: converged, locally measured general-knowledge
    # suites (e.g. mmlu_pro, gpqa) recorded deliberately OUTSIDE quality_score, whose
    # meaning on some roles is a role-purpose suite (architect_critic: the critic
    # suite). They compile as per-AXIS evidence and NEVER as `overall`, so they
    # cannot masquerade as the role-purpose figure. An entry counts only when its
    # truncation is explicitly zero: a capped score is not the model's score
    # (promotion_gates.yaml gates.quality.truncation_audit).
    if isinstance(performance, dict):
        general = performance.get("general_suite_quality")
        if isinstance(general, dict):
            for key, entry in general.items():
                if not (isinstance(key, str) and key.startswith("suite_")):
                    continue
                if not isinstance(entry, dict) or entry.get("truncated") != 0:
                    continue
                accuracy = entry.get("accuracy")
                if isinstance(accuracy, (int, float)) and not isinstance(accuracy, bool):
                    suite_key = key.removeprefix("suite_")
                    if suite_key != "overall":
                        suite_vector.setdefault(suite_key, float(accuracy))

    overall_basis: str | None = None
    if "overall" in suite_vector:
        overall_basis = "registry performance quality_pct/quality_score"

    if isinstance(server_cfg, dict):
        raw_benchmark = server_cfg.get("benchmark_score")
        benchmark_score = _score_fraction(raw_benchmark)
        if benchmark_score is not None and "overall" not in suite_vector:
            # Only a WHOLE-SUITE benchmark may become `overall`. A registry
            # benchmark_score that names its own narrow scope — e.g.
            # "25/27 (93%) on canonical long_context suite" — is domain
            # evidence wearing a general-sounding field name.
            qualifier = _benchmark_domain_qualifier(raw_benchmark)
            if qualifier is None:
                suite_vector["overall"] = benchmark_score
                overall_basis = "registry benchmark_score (whole suite)"
            else:
                suite_vector.setdefault(qualifier, benchmark_score)

    measured: list[dict[str, Any]] = []
    if isinstance(server_cfg, dict) and server_cfg.get("benchmark_score"):
        measured.append(
            {
                "date": _registry_date(server_cfg, role_cfg),
                "protocol": "registry benchmark_score",
                "value": str(server_cfg["benchmark_score"]),
            }
        )
    elif isinstance(performance, dict) and performance:
        measured.append(
            {
                "date": _registry_date(role_cfg),
                "protocol": "registry performance block",
                "value": {k: _coerce_scalar(v) for k, v in performance.items()},
            }
        )

    record: dict[str, Any] = {
        "suite_vector": suite_vector,
        # WHERE `overall` came from, or None when there is no overall. Without
        # this, a consumer comparing two models' quality_overall cannot tell it
        # is comparing a Claude-judged 79-question suite against a 7-suite
        # percentage against a vision benchmark.
        "overall_basis": overall_basis,
        "source": "orchestration/model_registry.yaml",
        "eval_protocol": "MEASUREMENT.md#canonical-quality",
        "measured": measured,
    }
    # Vendor-reported / leaderboard results, benchmark-keyed. Kept in a SEPARATE
    # block from suite_vector on purpose: suite_vector holds figures measured on
    # this stack, `public` holds third-party claims about the bf16 upstream
    # model. Merging them would reintroduce exactly the mixed-provenance defect
    # the overall_basis field exists to expose.
    public = _public_quality(model_id)
    if public is not None:
        record["public"] = public
        # A LEGITIMATE `overall` — the mean over a FIXED benchmark set that
        # every model in the fleet reports (`universal_keys`). This is the only
        # construction that makes the scalar comparable across models: same
        # benchmarks, same vendor conditions, no coverage holes. It is the
        # opposite of the promotion this function used to do, where "overall"
        # meant whichever single number happened to exist.
        #
        # It OUTRANKS a local whole-suite figure on purpose. Our own canonical
        # judge suite is 74% saturated and was only ever run on two of six
        # models, so it cannot rank the fleet; these three benchmarks can.
        # The local numbers are preserved verbatim under suite_vector and are
        # what a same-instrument comparison should use.
        universal = public.get("universal_keys") or []
        benchmarks = public.get("benchmarks") or {}
        values = [benchmarks[k] for k in universal if isinstance(benchmarks.get(k), (int, float))]
        if universal and len(values) == len(universal):
            suite_vector["overall"] = round(sum(values) / len(values), 4)
            record["overall_basis"] = (
                "public benchmarks: mean(" + ", ".join(universal) + ") — "
                f"{public.get('provenance')}, {public.get('reported_precision')}, "
                f"mode={public.get('reported_mode')}"
            )
        elif values:
            # Partial coverage: refuse to average a different subset than the
            # other models use. An aggregate over a model-specific subset is
            # not comparable to one over the full set, and silently averaging
            # whatever exists is how incomparable scalars get built.
            record["overall_basis"] = (
                f"no overall: only {len(values)}/{len(universal)} universal "
                "benchmarks reported; averaging a partial subset would not be "
                "comparable to models with full coverage"
            )

        # THE ROLE-FACING FIGURE. Consumers that score a role (routing, reward)
        # read this rather than picking an axis themselves, so the choice of
        # axis — and the honesty about whether it can rank — is made once, here.
        capabilities = []
        if isinstance(role_cfg, dict):
            capabilities = [
                str(c) for c in (role_cfg.get("candidate_roles") or []) if isinstance(c, str)
            ]
        record["for_role"] = resolve_role_quality(
            capabilities, benchmarks, suite_vector.get("overall")
        )
    return record


def _speed(role_cfg: dict[str, Any], server_cfg: dict[str, Any] | None) -> dict[str, Any]:
    performance = role_cfg.get("performance") if isinstance(role_cfg, dict) else None
    throughput = _as_float(server_cfg.get("throughput")) if isinstance(server_cfg, dict) else None
    optimized = None
    baseline = None
    if isinstance(performance, dict):
        optimized = _as_float(performance.get("optimized_tps"))
        baseline = _as_float(performance.get("baseline_tps"))

    numa_instances = server_cfg.get("numa_instances") if isinstance(server_cfg, dict) else None
    solo_96t_tps = throughput if numa_instances in (None, 1) else baseline
    quarter_48t_tps = throughput if numa_instances == 4 else None

    measured: list[dict[str, Any]] = []
    if throughput is not None:
        measured.append(
            {
                "date": _registry_date(server_cfg, role_cfg),
                "protocol": "server_mode throughput",
                "value_tps": throughput,
            }
        )
    elif optimized is not None or baseline is not None:
        measured.append(
            {
                "date": _registry_date(role_cfg),
                "protocol": "registry performance block",
                "baseline_tps": baseline,
                "optimized_tps": optimized,
            }
        )

    return {
        "solo_96t_tps": solo_96t_tps,
        "quarter_48t_tps": quarter_48t_tps,
        "prefill_tps": None,
        "optimized_tps": optimized,
        "source": "orchestration/model_registry.yaml",
        "measured": measured,
    }


def _acceleration(
    role_cfg: dict[str, Any],
    server_cfg: dict[str, Any] | None,
    enrichment_records: list[dict[str, Any]],
) -> dict[str, Any]:
    accel: dict[str, Any] = {}
    for source in (role_cfg, server_cfg or {}):
        candidate = source.get("acceleration") if isinstance(source, dict) else None
        if isinstance(candidate, dict):
            accel.update(candidate)

    raw_type = accel.get("spec_type") or accel.get("type") or "none"
    spec_type = str(raw_type)
    if spec_type == "speculative_decoding":
        spec_type = "draft"

    draft_compat: list[str] = []
    for key in ("draft_role", "draft_model"):
        value = accel.get(key)
        if value:
            draft_compat.append(_canonical_slug(str(value)))

    enable_thinking = None
    thinking_control = None
    for source in _enrichment_sources(role_cfg, server_cfg, enrichment_records):
        for candidate in (source.get("model") if isinstance(source, dict) else None, source):
            if not isinstance(candidate, dict):
                continue
            raw_control = candidate.get("thinking_control")
            if isinstance(raw_control, str):
                thinking_control = {"mode": raw_control}
                break
            if isinstance(raw_control, dict) and raw_control.get("mode"):
                thinking_control = {
                    str(key): _coerce_scalar(value) for key, value in raw_control.items()
                }
                break
        if thinking_control:
            break

    for source in _enrichment_sources(role_cfg, server_cfg, enrichment_records):
        chat_kwargs = source.get("chat_template_kwargs") if isinstance(source, dict) else None
        if isinstance(chat_kwargs, dict) and "enable_thinking" in chat_kwargs:
            enable_thinking = bool(chat_kwargs["enable_thinking"])
            thinking_control = {
                "mode": "toggle_on" if enable_thinking else "toggle_off",
                "source": "chat_template_kwargs.enable_thinking",
            }
            break
        model = source.get("model") if isinstance(source, dict) else None
        if isinstance(model, dict) and model.get("disable_thinking") is True:
            enable_thinking = False
            thinking_control = {
                "mode": "toggle_off",
                "source": "model.disable_thinking",
            }
            break
        if source.get("disable_thinking") is True:
            enable_thinking = False
            thinking_control = {
                "mode": "toggle_off",
                "source": "disable_thinking",
            }
            break
        if source.get("reasoning") == "off":
            enable_thinking = False
            thinking_control = {
                "mode": "reasoning_off",
                "source": "reasoning",
            }
            break

    kv = server_cfg.get("kv_quant") if isinstance(server_cfg, dict) else None
    if not isinstance(kv, dict):
        kv = {"k": None, "v": None}

    out = {
        "spec_type": spec_type,
        "draft_compat": sorted(set(draft_compat)),
        "enable_thinking": enable_thinking,
        "thinking_control": thinking_control,
        "kv": kv,
    }
    for key in ("draft_max", "draft_p_min", "k", "p_split", "lookup", "corpus_retrieval"):
        if key in accel:
            out[key] = accel[key]
    return out


def _serving(
    role_cfg: dict[str, Any], server_role: str | None, server_cfg: dict[str, Any] | None
) -> dict[str, Any]:
    runtime = server_cfg.get("runtime_requirements") if isinstance(server_cfg, dict) else None
    binary_dir = runtime.get("binary_dir") if isinstance(runtime, dict) else None
    if binary_dir and "ik_llama.cpp" in str(binary_dir):
        binary = "ik-pr1744"
    elif isinstance(server_cfg, dict) and server_cfg.get("backend"):
        binary = str(server_cfg["backend"])
    else:
        binary = "llama.cpp"

    ports: list[int] = []
    if isinstance(server_cfg, dict):
        port = server_cfg.get("port")
        if isinstance(port, int):
            ports.append(port)
        numa_ports = server_cfg.get("numa_ports")
        if isinstance(numa_ports, list):
            ports.extend(int(item) for item in numa_ports if isinstance(item, int))
    else:
        role_port = role_cfg.get("port") if isinstance(role_cfg, dict) else None
        if isinstance(role_port, int):
            ports.append(role_port)
        role_server = role_cfg.get("server") if isinstance(role_cfg, dict) else None
        endpoint = role_server.get("endpoint") if isinstance(role_server, dict) else None
        if isinstance(endpoint, str):
            match = re.search(r":(\d+)(?:/|$)", endpoint)
            if match:
                ports.append(int(match.group(1)))

    numa_instances = server_cfg.get("numa_instances") if isinstance(server_cfg, dict) else None
    if not server_cfg:
        numa_policy = "role_endpoint_binding" if ports else "unresolved_no_server_binding"
    elif numa_instances == 4:
        # Retired 2026-07-30. Retained so historical descriptors stay readable.
        numa_policy = "4x48t_quarter_instances"
    elif numa_instances == 2:
        # 2026-07-30 HALF FLEET. Without this branch every half role fell through
        # to "server_default" — the topology label the whole derived layer
        # carries — so retiring quarters silently unlabelled the entire fleet.
        numa_policy = "2x48t_half_instances"
    elif numa_instances == 1:
        numa_policy = "single_96t"
    else:
        numa_policy = "server_default"

    memory = role_cfg.get("memory") if isinstance(role_cfg, dict) else None
    model = role_cfg.get("model") if isinstance(role_cfg.get("model"), dict) else {}
    requirements = {
        "mmproj_path": str(model["mmproj_path"])
    } if model.get("mmproj_path") else {}
    return {
        "binary": binary,
        "binary_dir": str(binary_dir) if binary_dir else None,
        "numa_policy": numa_policy,
        "mlock": bool(memory.get("pinned")) if isinstance(memory, dict) else False,
        "ports": sorted(set(ports)),
        "server_role": server_role,
        "requirements": requirements,
    }


def _enrichment_sources(
    role_cfg: dict[str, Any],
    server_cfg: dict[str, Any] | None,
    enrichment_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = [role_cfg]
    if isinstance(server_cfg, dict):
        sources.append(server_cfg)
    for record in enrichment_records:
        for key in ("model", "config"):
            source = record.get(key)
            if isinstance(source, dict):
                sources.append(source)
    return sources


def _first_context_value(
    role_cfg: dict[str, Any],
    server_cfg: dict[str, Any] | None,
    enrichment_records: list[dict[str, Any]],
) -> Any:
    for source in _enrichment_sources(role_cfg, server_cfg, enrichment_records):
        model = source.get("model") if isinstance(source, dict) else None
        for candidate in (model, source):
            if not isinstance(candidate, dict):
                continue
            for key in (
                "ctx_max",
                "context_length",
                "max_context",
                "context_size",
                "n_ctx",
                "ctx_size",
            ):
                value = candidate.get(key)
                if value is not None:
                    return value
    return None


# Model-native (architectural / GGUF-header) context keys. These describe the
# maximum context the model was trained/built for, distinct from the possibly
# smaller effective/configured ctx_max that ``_first_context_value`` resolves.
# GGUF exposes this as ``<arch>.context_length``; registries often mirror it as
# ``n_ctx_train`` / ``max_position_embeddings`` / ``native_context_length``.
_NATIVE_CONTEXT_KEYS = (
    "ctx_model_max",
    "native_context_length",
    "n_ctx_train",
    "max_position_embeddings",
    "context_length",
    "train_context_length",
    "context_length_train",
    "gguf_context_length",
)


def _first_model_native_context_value(
    role_cfg: dict[str, Any],
    server_cfg: dict[str, Any] | None,
    enrichment_records: list[dict[str, Any]],
) -> int | None:
    """Resolve the model-native max context from GGUF-header/registry evidence.

    Returns a positive integer token count, or ``None`` when no model-native
    context evidence is present (a structured gap consumers can fail-closed on).
    """
    for source in _enrichment_sources(role_cfg, server_cfg, enrichment_records):
        model = source.get("model") if isinstance(source, dict) else None
        for candidate in (model, source):
            if not isinstance(candidate, dict):
                continue
            for key in _NATIVE_CONTEXT_KEYS:
                parsed = _as_positive_int(candidate.get(key))
                if parsed is not None:
                    return parsed
    return None


def _model_architecture_metadata(model: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for source_key, target_key in (
        ("n_layers", "n_layers"),
        ("n_layer", "n_layers"),
        ("num_hidden_layers", "n_layers"),
        ("block_count", "n_layers"),
        ("attention_layers", "attention_layers"),
        ("n_attention_layers", "attention_layers"),
    ):
        parsed = _as_positive_int(model.get(source_key))
        if parsed is not None:
            metadata.setdefault(target_key, parsed)
    if metadata:
        metadata["source"] = "registry.model"
    return metadata


def _descriptor_modalities(model: dict[str, Any], role_cfg: dict[str, Any]) -> list[str]:
    modalities = {"text"}
    model_names = " ".join(
        str(model.get(key) or "") for key in ("name", "path", "huggingface_id")
    ).lower()
    if model.get("mmproj_path"):
        modalities.add("vision")
    if "coder" in model_names:
        modalities.add("code")
    if "math" in model_names:
        modalities.add("math")
    if "qwen3-next" in model_names or "long-context" in model_names:
        modalities.add("long_context")
    candidate_roles = role_cfg.get("candidate_roles") if isinstance(role_cfg, dict) else None
    if isinstance(candidate_roles, list) and any("vision" in str(role) for role in candidate_roles):
        modalities.add("vision")
    return sorted(modalities)


def _record_model_names(cfg: dict[str, Any]) -> list[str]:
    names: list[str] = []
    model = cfg.get("model") if isinstance(cfg, dict) else None
    if isinstance(model, dict):
        for key in ("name", "path", "huggingface_id"):
            value = model.get(key)
            if value:
                names.append(str(value))
    elif isinstance(model, str):
        names.append(model)
    for key in ("model_path",):
        value = cfg.get(key)
        if value:
            names.append(str(value))
    return names


def _descriptor_lookup_keys(name: str | None, quant: str | None) -> set[str]:
    if not name:
        return set()
    keys = {_canonical_slug(name), _canonical_model_id(name, None)}
    inferred_quant = _quant_from(name, {"quant": quant} if quant else {})
    if inferred_quant:
        keys.add(_canonical_model_id(name, inferred_quant))
    return keys


def _build_enrichment_index(registry: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(registry, dict):
        return {}
    index: dict[str, list[dict[str, Any]]] = {}
    for section_name in ("roles", "server_mode"):
        section = registry.get(section_name)
        if not isinstance(section, dict):
            continue
        for key, cfg in section.items():
            if not isinstance(cfg, dict):
                continue
            model = cfg.get("model") if isinstance(cfg.get("model"), dict) else {}
            quant = str(model.get("quant")) if isinstance(model, dict) and model.get("quant") else None
            record = {
                "section": section_name,
                "key": str(key),
                "config": cfg,
                "model": model,
            }
            for name in _record_model_names(cfg):
                for lookup_key in _descriptor_lookup_keys(name, quant):
                    index.setdefault(lookup_key, []).append(record)
    return index


def _merge_descriptor(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    for key in ("roles", "server_roles", "runtime_aliases"):
        values = incoming["role_bindings"].get(key) or []
        existing = target["role_bindings"].setdefault(key, [])
        target["role_bindings"][key] = sorted(set(existing) | set(values))
    alias_overrides = incoming["role_bindings"].get("alias_overrides") or []
    if alias_overrides:
        existing_overrides = target["role_bindings"].setdefault("alias_overrides", [])
        merged = {
            (
                str(override.get("role")),
                str(override.get("served_by")),
                str(override.get("ignored_model_id")),
            ): override
            for override in existing_overrides + alias_overrides
            if isinstance(override, dict)
        }
        target["role_bindings"]["alias_overrides"] = [
            merged[key] for key in sorted(merged)
        ]
    target["role_bindings"]["shared_mmap"] = target["role_bindings"].get("shared_mmap") or incoming[
        "role_bindings"
    ].get("shared_mmap")
    target["quality"]["suite_vector"].update(incoming["quality"]["suite_vector"])
    target["quality"]["measured"].extend(incoming["quality"]["measured"])
    if not target["speed"]["measured"]:
        target["speed"] = incoming["speed"]
    target_architecture = target.get("architecture")
    incoming_architecture = incoming.get("architecture")
    if not isinstance(target_architecture, dict) and isinstance(incoming_architecture, dict):
        target["architecture"] = dict(incoming_architecture)
    elif isinstance(target_architecture, dict) and isinstance(incoming_architecture, dict):
        target_architecture.update(
            {
                key: value
                for key, value in incoming_architecture.items()
                if value is not None and key not in target_architecture
            }
        )
    for key in ("ports",):
        target["serving"][key] = sorted(
            set(target["serving"].get(key) or []) | set(incoming["serving"].get(key) or [])
        )
    target["known_gaps"] = sorted(set(target["known_gaps"]) | set(incoming["known_gaps"]))


def _descriptor_gaps(descriptor: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if not descriptor["quality"]["suite_vector"]:
        gaps.append("Missing quality suite_vector evidence")
    if not descriptor["speed"]["measured"]:
        gaps.append("Missing speed measurement evidence")
    if not descriptor["serving"]["ports"]:
        gaps.append("Missing serving port binding")
    if descriptor["serving"]["numa_policy"] == "unresolved_no_server_binding":
        gaps.append("Missing server_mode binding")
    if descriptor["acceleration"]["enable_thinking"] is None:
        thinking_control = descriptor["acceleration"].get("thinking_control")
        if not isinstance(thinking_control, dict) or not thinking_control.get("mode"):
            gaps.append("Missing enable_thinking compatibility evidence")
    if descriptor["ctx_max"] is None:
        gaps.append("Missing structured ctx_max")
    return gaps


def _descriptor_for_role(
    role: str,
    role_cfg: dict[str, Any],
    server_role: str | None,
    server_cfg: dict[str, Any] | None,
    binding_kind: str | None,
    enrichment_index: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    model = _first_model_dict(role_cfg, server_cfg)
    model_name = _first_model_name(role_cfg, server_cfg)
    if not model_name:
        return None

    quant = _quant_from(model_name, model)
    model_id = _canonical_model_id(model_name, quant)
    enrichment_records: list[dict[str, Any]] = []
    for key in _descriptor_lookup_keys(model_name, quant):
        enrichment_records.extend(enrichment_index.get(key, []))
    arch = str(model.get("architecture") or "unknown")
    params_b = _params_from(model_name, model)
    active_b = _active_from(model_name, arch, params_b)

    mem_gb = model.get("size_gb")
    if mem_gb is None and isinstance(server_cfg, dict):
        mem_gb = server_cfg.get("memory_gb")

    server_model_name = _first_model_name(server_cfg) if server_cfg else None
    # 2026-08-01: pass the server's OWN model dict, not `{}`.
    #
    # `_quant_from` prefers an explicit `quant:` field and only falls back to
    # parsing the name. The role side above is resolved as
    # `_quant_from(model_name, model)` — name PLUS declared field — while this
    # side was resolved from the name alone. For any model whose name does not
    # embed its quant (Qwen3-VL-30B-A3B-Instruct, declared `quant: Q4_K_M`) the
    # two ids could never agree, and the Role-server conflict below fired on a
    # mismatch the comparison had manufactured by discarding information it held.
    # Symmetric inputs; a genuine quant disagreement still raises.
    server_model_dict = _first_model_dict(server_cfg) if server_cfg else {}
    server_model_id = (
        _canonical_model_id(server_model_name, _quant_from(server_model_name, server_model_dict))
        if server_model_name
        else None
    )

    known_gaps: list[str] = []
    runtime_aliases: list[str] = []
    if binding_kind == "shared_with" and server_role:
        runtime_aliases.append(server_role)
        if server_model_id and server_model_id != model_id:
            known_gaps.append(
                "Role-server conflict: role model metadata does not match the shared runtime server model"
            )

    architecture = _model_architecture_metadata(model)
    descriptor = {
        "model_id": model_id,
        "display_name": str(model.get("name") or model_name),
        "family": _family_from(model_id, params_b),
        "arch": arch,
        "params_b": params_b,
        "active_b": active_b,
        "quant": quant,
        "mem_gb": _as_float(mem_gb),
        "ctx_max": _first_context_value(role_cfg, server_cfg, enrichment_records),
        "ctx_model_max": _first_model_native_context_value(
            role_cfg, server_cfg, enrichment_records
        ),
        "modalities": _descriptor_modalities(model, role_cfg),
        "role_bindings": {
            "roles": [role],
            "server_roles": [server_role] if server_role else [],
            "runtime_aliases": runtime_aliases,
            "shared_mmap": bool(server_cfg),
        },
        "quality": _quality(role_cfg, server_cfg, model_id),
        "speed": _speed(role_cfg, server_cfg),
        "acceleration": _acceleration(role_cfg, server_cfg, enrichment_records),
        "serving": _serving(role_cfg, server_role, server_cfg),
        "known_gaps": known_gaps,
    }
    if architecture:
        descriptor["architecture"] = architecture
    descriptor["known_gaps"].extend(_descriptor_gaps(descriptor))
    return descriptor


def portable_source_path(path: Path) -> str:
    """Spell a pinned source path so the pin means the same thing in every checkout.

    A file inside THIS checkout is recorded repo-relative
    (``orchestration/model_registry.yaml``); anything outside it (the research
    master registry, a test's tmp tree) stays absolute.

    WHY: the generated artifacts used to record ``str(path)`` — the absolute path
    of whichever checkout compiled them. Every git worktree shares one set of
    committed artifacts, so a worktree then (a) saw its descriptors as STALE for
    nothing but the path spelling of ``source_registries.lean.path`` and (b) had
    its guard hash-check the PRIMARY clone's files, not its own — so the gate's
    verdict in a worktree depended on another session's uncommitted edits in a
    different working tree (measured 2026-09-24: two ``source_artifacts`` hash
    mismatches in a fresh worktree, both caused by uncommitted edits in the
    shared clone). The sha256 is the identity; the path only says WHICH file of
    the checkout under test to hash. Resolve with
    :func:`resolve_portable_source_path`.
    """
    try:
        return path.resolve().relative_to(_REPO_ROOT.resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


def resolve_portable_source_path(raw: str, repo_root: Path = _REPO_ROOT) -> Path:
    """Inverse of :func:`portable_source_path`: relative means relative to ``repo_root``.

    ``repo_root`` defaults to the checkout whose code is running — the same root
    :func:`portable_source_path` relativised against — so a gate run in a
    worktree verifies that worktree's files.
    """
    path = Path(raw)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def _source_metadata(path: Path) -> dict[str, Any]:
    return {
        "path": portable_source_path(path),
        "repo_commit": _repo_commit(path),
        "sha256": _sha256(path),
    }


def compile_model_descriptors(
    lean_registry_path: Path = DEFAULT_LEAN_REGISTRY,
    research_registry_path: Path | None = DEFAULT_RESEARCH_REGISTRY,
    *,
    active_roles: set[str] | None = None,
    allow_incomplete: bool = False,
) -> dict[str, Any]:
    """Compile one descriptor per canonical model identity.

    The current W2 compiler is intentionally conservative: it derives model identity,
    role bindings, serving, acceleration, and registry-carried quality/speed evidence
    from the lean registry. It records research registry provenance in the metadata so
    W2 follow-up work can promote richer benchmark artifacts without rewriting source
    registries in place.
    """
    registry = _load_yaml(lean_registry_path)
    research_registry: dict[str, Any] | None = None
    if research_registry_path is not None and research_registry_path.exists():
        research_registry = _load_yaml(research_registry_path)
    enrichment_index = _build_enrichment_index(research_registry)

    roles = registry.get("roles") or {}
    server_mode = registry.get("server_mode") or {}
    if not isinstance(roles, dict) or not isinstance(server_mode, dict):
        raise ValueError("registry must contain mapping-valued roles and server_mode sections")

    descriptors: dict[str, dict[str, Any]] = {}
    for role in sorted(_expanded_active_roles(active_roles, registry)):
        role_cfg = roles.get(role)
        server_role, server_cfg, binding_kind = _server_for_role(role, server_mode)
        alias_override: dict[str, str] | None = None
        if binding_kind == "shared_with" and isinstance(server_cfg, dict):
            role_model_id = _model_id_from_configs(role_cfg if isinstance(role_cfg, dict) else None)
            server_model_id = _model_id_from_configs(server_cfg)
            model_role = server_cfg.get("model_role")
            primary_role_cfg = roles.get(model_role) if model_role else None
            if role_model_id and server_model_id and role_model_id != server_model_id:
                if isinstance(primary_role_cfg, dict):
                    role_cfg = primary_role_cfg
                else:
                    role_cfg = {}
                primary = str(model_role) if model_role else str(server_role)
                alias_override = {
                    "role": role,
                    "served_by": primary,
                    "ignored_model_id": role_model_id,
                    "reason": "server_mode.shared_with runtime takes precedence",
                }
        if not isinstance(role_cfg, dict) and isinstance(server_cfg, dict):
            model_role = server_cfg.get("model_role")
            role_cfg = roles.get(model_role) if model_role else {}
        if not isinstance(role_cfg, dict):
            role_cfg = {}

        descriptor = _descriptor_for_role(
            role,
            role_cfg,
            server_role,
            server_cfg,
            binding_kind,
            enrichment_index,
        )
        if descriptor is None:
            continue
        if alias_override:
            descriptor["role_bindings"].setdefault("alias_overrides", []).append(alias_override)
        existing = descriptors.get(descriptor["model_id"])
        if existing:
            _merge_descriptor(existing, descriptor)
        else:
            descriptors[descriptor["model_id"]] = descriptor

    for descriptor in descriptors.values():
        manual_gaps = [gap for gap in descriptor["known_gaps"] if not gap.startswith("Missing ")]
        descriptor["known_gaps"] = sorted(set(manual_gaps + _descriptor_gaps(descriptor)))

    missing_by_model = {
        model_id: descriptor["known_gaps"]
        for model_id, descriptor in descriptors.items()
        if descriptor["known_gaps"]
    }
    if missing_by_model and not allow_incomplete:
        raise DescriptorCompileError(missing_by_model)

    status = "compiled_with_gaps" if missing_by_model else "compiled"
    metadata: dict[str, Any] = {
        "descriptor_version": 3,
        "compiled_at": _timestamp(),
        "status": status,
        "coverage_scope": "active_roles_from_stack_manifest",
        "source_registries": {"lean": _source_metadata(lean_registry_path)},
        "model_id_policy": {
            "canonical_shape": "family-params-active-quant",
            "invariant": "model records are keyed by physical model identity, never by role name",
        },
        "known_global_gaps": [
            "Research registry and bench-artifact enrichment is provenance-recorded but not yet field-promoted.",
            "Source registry comments remain the measurement witness; do not reformat them in place.",
        ],
        "models": [descriptors[key] for key in sorted(descriptors)],
    }
    if research_registry_path is not None:
        metadata["source_registries"]["research"] = _source_metadata(research_registry_path)
    return metadata


def write_model_descriptors(
    output_path: Path,
    *,
    lean_registry_path: Path = DEFAULT_LEAN_REGISTRY,
    research_registry_path: Path | None = DEFAULT_RESEARCH_REGISTRY,
    active_roles: set[str] | None = None,
    allow_incomplete: bool = False,
) -> dict[str, Any]:
    descriptors = compile_model_descriptors(
        lean_registry_path=lean_registry_path,
        research_registry_path=research_registry_path,
        active_roles=active_roles,
        allow_incomplete=allow_incomplete,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            descriptors,
            fh,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=200,
        )
    return descriptors


def _roles_from_stack_manifest() -> set[str]:
    sys.path.insert(0, str(_REPO_ROOT / "scripts/server"))
    from stack_manifest import ROLE_LAUNCH_META  # type: ignore[import]

    active: set[str] = set()
    for role, meta in ROLE_LAUNCH_META.items():
        if not isinstance(meta, dict):
            active.add(str(role))
            continue
        if meta.get("launcher_only") is True:
            continue
        active.add(str(role))
        aliases = meta.get("shared_with_first_n") if isinstance(meta, dict) else None
        if isinstance(aliases, list):
            active.update(str(alias) for alias in aliases)
    return active


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile model-capability descriptors")
    parser.add_argument("--lean", type=Path, default=DEFAULT_LEAN_REGISTRY)
    parser.add_argument("--research", type=Path, default=DEFAULT_RESEARCH_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_DESCRIPTOR_OUTPUT)
    parser.add_argument("--roles", nargs="+", help="Explicit active role list")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print descriptors instead of writing"
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Emit descriptors with known_gaps instead of refusing incomplete records",
    )
    args = parser.parse_args(argv)

    active_roles = set(args.roles) if args.roles else _roles_from_stack_manifest()
    descriptors = compile_model_descriptors(
        lean_registry_path=args.lean,
        research_registry_path=args.research,
        active_roles=active_roles,
        allow_incomplete=args.allow_incomplete,
    )
    if args.dry_run:
        yaml.safe_dump(
            descriptors,
            sys.stdout,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=200,
        )
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(
                descriptors,
                fh,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
                width=200,
            )
        print(f"OK: wrote {len(descriptors.get('models', []))} descriptors to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
