from __future__ import annotations

from pathlib import Path

import yaml

from scripts.validate.reasoning_effort_certifications import (
    validate_reasoning_effort_certifications,
)


FULL_TEMPLATE_SHA = "1443ea9ab4bb" + "0" * 52
CURRENT_KERNEL_NAME = "production-consolidated-v9"


def _write(path: Path, value: dict) -> Path:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _eras(
    *,
    kernel_name: str | None = CURRENT_KERNEL_NAME,
    era_id: str = "E9-cpu-kernel",
    from_ts: str = "2026-08-10T23:59:00Z",
    until: str | None = None,
    extra: list[dict] | None = None,
) -> dict:
    row: dict = {"id": era_id, "from": from_ts, "scope": "cpu_bench"}
    if kernel_name is not None:
        row["kernel_name"] = kernel_name
    if until is not None:
        row["until"] = until
    rows = [*(extra or []), row]
    return {"eras": rows}


def _registry(
    *,
    model: str = "Qwen-Test",
    quant: str = "Q8_0",
    level: str | None = "L2",
    template: str | None = "1443ea9ab4bb",
    server_mode_template: str | None = None,
) -> dict:
    role: dict = {"model": {"name": model, "quant": quant}}
    if level is not None:
        role["reasoning_effort"] = {"level": level}
    if template is not None:
        role["chat_template"] = {"served_template_sha256_12": template}
    registry: dict = {"roles": {"frontdoor": role}}
    if server_mode_template is not None:
        registry["server_mode"] = {
            "frontdoor": {"chat_template": {"served_template_sha256_12": server_mode_template}}
        }
    return registry


def _ledger(
    *,
    model: str = "Qwen-Test",
    quant: str = "Q8_0",
    era: str = CURRENT_KERNEL_NAME,
    level: str = "L2",
    template: str | None = "1443ea9ab4bb",
) -> dict:
    return {
        "schema_version": 1,
        "active_kernel_era": era,
        "role_certifications": {
            "frontdoor": {
                "level": level,
                "curve_artifact": "artifacts/reasoning-effort/frontdoor.json",
                "certified_against": {
                    "model": model,
                    "quant": quant,
                    "kernel_era": era,
                    "template_sha": template,
                },
            }
        },
    }


def _run(
    tmp_path: Path,
    *,
    registry: dict | None = None,
    ledger: dict | None = None,
    eras: dict | None = None,
):
    return validate_reasoning_effort_certifications(
        _write(tmp_path / "registry.yaml", registry if registry is not None else _registry()),
        _write(
            tmp_path / "certifications.yaml",
            ledger if ledger is not None else _ledger(),
        ),
        _write(tmp_path / "eras.yaml", eras if eras is not None else _eras()),
    )


def test_accepts_matching_role_model_quant_and_kernel_era(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.ok


def test_rejects_model_swap(tmp_path: Path) -> None:
    result = _run(tmp_path, registry=_registry(model="Replacement"))
    assert any("bound model" in error for error in result.errors)


def test_rejects_quant_change(tmp_path: Path) -> None:
    result = _run(tmp_path, registry=_registry(quant="IQ2_XS"))
    assert any("bound quant" in error for error in result.errors)


def test_rejects_kernel_promotion_until_curve_is_recertified(tmp_path: Path) -> None:
    ledger = _ledger()
    ledger["active_kernel_era"] = "v9"
    result = _run(tmp_path, ledger=ledger)
    assert any("kernel era" in error for error in result.errors)


def test_rejects_declared_effort_without_certificate(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        ledger={
            "schema_version": 1,
            "active_kernel_era": CURRENT_KERNEL_NAME,
            "role_certifications": {},
        },
    )
    assert any("has no role_certifications entry" in error for error in result.errors)


def test_rejects_certificate_without_a_curve_record(tmp_path: Path) -> None:
    ledger = _ledger()
    del ledger["role_certifications"]["frontdoor"]["curve_artifact"]
    result = _run(tmp_path, ledger=ledger)
    assert any("curve_artifact" in error for error in result.errors)


def test_ignores_roles_without_a_prompt_effort_default(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(level=None),
        ledger={
            "schema_version": 1,
            "active_kernel_era": CURRENT_KERNEL_NAME,
            "role_certifications": {},
        },
    )
    assert result.ok


def test_accepts_matching_template_sha(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(template="1443ea9ab4bb"),
        ledger=_ledger(template="1443ea9ab4bb"),
    )
    assert result.ok


def test_accepts_matching_template_sha_bound_via_server_mode(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(template=None, server_mode_template="1443ea9ab4bb"),
        ledger=_ledger(template="1443ea9ab4bb"),
    )
    assert result.ok


def test_rejects_template_swap_until_curve_is_recertified(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(template="1443ea9ab4bb"),
        ledger=_ledger(template="deadbeef0011"),
    )
    assert any(
        "certified template sha" in error and "bound template sha" in error
        for error in result.errors
    )


def test_rejects_template_swap_when_bound_via_server_mode(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(template=None, server_mode_template="1443ea9ab4bb"),
        ledger=_ledger(template="deadbeef0011"),
    )
    assert any("bound template sha" in error for error in result.errors)


def test_no_bound_template_makes_template_check_vacuous(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(template=None),
        ledger=_ledger(template="1443ea9ab4bb"),
    )
    assert result.ok


def test_template_sha_is_required_even_without_a_bound_template(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(template=None),
        ledger=_ledger(template=None),
    )
    assert any("template_sha" in error for error in result.errors)


def test_full_sha_in_certificate_matches_short_sha_in_registry(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(template="1443ea9ab4bb"),
        ledger=_ledger(template=FULL_TEMPLATE_SHA),
    )
    assert result.ok


def test_short_sha_in_certificate_matches_full_sha_in_registry(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(template=FULL_TEMPLATE_SHA),
        ledger=_ledger(template="1443ea9ab4bb"),
    )
    assert result.ok


def test_full_sha_normalization_applies_to_server_mode_binding(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        registry=_registry(template=None, server_mode_template=FULL_TEMPLATE_SHA),
        ledger=_ledger(template="1443ea9ab4bb"),
    )
    assert result.ok


# ---------------------------------------------------------------------------
# Era cross-check: the ledger MUST agree with the current cpu-kernel era in
# instrument_eras.yaml — the promotion record. This is the enforcement that
# makes the era roll-forward structural instead of a comment.
# ---------------------------------------------------------------------------


def test_accepts_ledger_era_matching_current_cpu_kernel_era(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        ledger=_ledger(era=CURRENT_KERNEL_NAME),
        eras=_eras(kernel_name=CURRENT_KERNEL_NAME),
    )
    assert result.ok


def test_rejects_stale_ledger_era_after_kernel_promotion(tmp_path: Path) -> None:
    """The 2026-08-23 incident shape: eras file advanced, ledger did not."""
    result = _run(
        tmp_path,
        ledger=_ledger(era="production-consolidated-v8"),
        eras=_eras(kernel_name=CURRENT_KERNEL_NAME),
    )
    assert any("does not match the current production cpu-kernel era" in e for e in result.errors)


def test_rejects_missing_ledger_era_even_with_empty_certificates(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        ledger={
            "schema_version": 1,
            "active_kernel_era": None,
            "role_certifications": {},
        },
        eras=_eras(kernel_name=CURRENT_KERNEL_NAME),
    )
    assert any("missing non-empty active_kernel_era" in e for e in result.errors)


def test_rejects_unreadable_eras_registry(tmp_path: Path) -> None:
    result = validate_reasoning_effort_certifications(
        _write(tmp_path / "registry.yaml", _registry()),
        _write(tmp_path / "certifications.yaml", _ledger()),
        tmp_path / "does-not-exist.yaml",
    )
    assert any("instrument eras registry invalid" in e for e in result.errors)


def test_rejects_current_era_without_kernel_name(tmp_path: Path) -> None:
    """A promotion that forgets kernel_name on the new era row fails closed."""
    result = _run(
        tmp_path,
        eras=_eras(kernel_name=None),
    )
    assert any("lacks machine-readable kernel_name" in e for e in result.errors)


def test_rejects_no_active_cpu_kernel_era(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        eras={"eras": [{"id": "E9-eval-other", "from": "2026-08-10T23:59:00Z", "scope": "eval_quality"}]},
    )
    assert any("no active cpu-kernel era" in e for e in result.errors)


def test_current_era_is_newest_active_row_not_an_older_one(tmp_path: Path) -> None:
    """E8 and E9 both active; the ledger must match the NEWEST (E9), not E8."""
    result = _run(
        tmp_path,
        ledger=_ledger(era="production-consolidated-v8"),
        eras=_eras(
            kernel_name=CURRENT_KERNEL_NAME,
            extra=[
                {
                    "id": "E8-cpu-kernel",
                    "from": "2026-07-25T18:38:43Z",
                    "scope": "cpu_bench",
                    "kernel_name": "production-consolidated-v8",
                }
            ],
        ),
    )
    assert any("does not match the current production cpu-kernel era" in e for e in result.errors)
