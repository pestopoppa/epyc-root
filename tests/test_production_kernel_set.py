"""The production kernel SET projection — three kernels, four binaries.

KRD-AUDIT-20260812 (`mainC`, for `inference`). The freeze covers a kernel SET —
llama.cpp `production-consolidated-v9` plus whisper.cpp and qwentts.cpp at
`production-speech-v1` — and the dashboard projected only llama. Measured on the live
surface before the change: `whisper`, `qwentts`, `speech` and `ggml` appeared ZERO
times in `autokernel_current_state()`. Two of three frozen kernels could drift, be
rebuilt, or vanish with no panel saying so.

Every test here is a MUTATION: the value under test is one an operator would care
about, and the assertion is that the surface goes loud. A panel that cannot go red is
the incident-8 shape (a dead loop rendering as a clean, empty, trusted page).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "dashboard"))
import server as S  # noqa: E402

SPEECH = REPO / "artifacts/operator/ratify_speech_kernel_freeze_20260731.json"
V9 = REPO / "artifacts/operator/ratify_v9_final_freeze_20260811.json"


def _speech_with(tmp_path: Path, mutate) -> Path:
    data = json.loads(SPEECH.read_text(encoding="utf-8"))
    mutate(data)
    out = tmp_path / "speech.json"
    out.write_text(json.dumps(data), encoding="utf-8")
    return out


def test_all_three_kernels_are_projected() -> None:
    """The gap this audit was commissioned to find: two thirds of the freeze missing."""
    result = S.production_kernel_set()
    titles = {m["title"] for m in result["members"]}
    assert len(result["members"]) == 3
    assert any("whisper" in t for t in titles) and any("qwentts" in t for t in titles)
    assert result["expected_binaries"] == 4
    assert result["stable_links_proven"] == 4
    assert result["linkage_proven"] == 4


def test_llama_identity_is_NOT_read_from_the_speech_attestation(tmp_path: Path) -> None:
    """The stale-source trap, and the single most important test in this file.

    The speech attestation also carries a `kernels.llama_cpp` block pinned at **v8**
    and labelled in its own text "unchanged by this ratification; recorded for
    completeness". Folding the set from that one file would project a stale llama
    identity that still looks internally consistent. llama must come from the v9
    attestation, so corrupting the speech file's llama block must change nothing.
    """
    def wreck(data):
        data["kernels"]["llama_cpp"]["branch"] = "production-consolidated-v8"
        data["kernels"]["llama_cpp"]["commit"] = "67a433bf45a8a091d83b4ea0b32ff0735fd51800"

    result = S.production_kernel_set(speech_attestation_path=_speech_with(tmp_path, wreck))
    llama = next(m for m in result["members"] if m["key"] == "llama_cpp")
    assert llama["branch"] == "production-consolidated-v9"
    assert llama["matches_attestation"] is True


def test_a_missing_speech_attestation_is_loud_and_names_what_is_unproven(tmp_path) -> None:
    result = S.production_kernel_set(speech_attestation_path=tmp_path / "absent.json")
    assert result["intact"] is False
    assert result["alarms"]
    assert "whisper" in result["speech"]["error"] and "qwentts" in result["speech"]["error"]


def test_binary_drift_is_reported_as_drift_not_as_absence(tmp_path: Path) -> None:
    """A rebuilt frozen binary is the thing the digests exist to catch."""
    result = S.production_kernel_set(
        speech_attestation_path=_speech_with(
            tmp_path, lambda d: d["kernels"]["whisper_cpp"].update(binary_sha256="0" * 64)))
    assert result["intact"] is False
    assert any("BINARY DRIFT" in a for a in result["alarms"])


def test_a_tree_at_the_wrong_commit_is_reported(tmp_path: Path) -> None:
    result = S.production_kernel_set(
        speech_attestation_path=_speech_with(
            tmp_path, lambda d: d["kernels"]["qwentts_cpp"].update(commit="dead" * 10)))
    assert result["intact"] is False
    assert any("does NOT match attestation" in a for a in result["alarms"])


def test_an_attested_binary_missing_from_disk_is_reported(tmp_path: Path) -> None:
    result = S.production_kernel_set(
        speech_attestation_path=_speech_with(
            tmp_path, lambda d: d["kernels"]["whisper_cpp"].update(binary="/nonexistent/x")))
    assert result["intact"] is False
    assert any("absent from disk" in a for a in result["alarms"])


def test_unverifiable_is_NOT_the_same_as_matching(tmp_path: Path) -> None:
    """Three-valued on purpose: a digest we could not compute must never read as a pass."""
    identity = S._binary_identity("probe", tmp_path / "nope", "a" * 64)
    assert identity["matches"] is None and identity["present"] is False
    assert identity["error"]


def test_a_missing_llama_attestation_carries_a_REASON_not_just_a_blank() -> None:
    """D-1 residual. The render was made loud earlier; the reason string was still None."""
    result = S._production_kernel_summary(Path("/nonexistent/ratify.json"),
                                          Path("/mnt/raid0/llm/llama.cpp"))
    assert result["available"] is False
    assert result["error"] and "not exported" in result["error"]


def test_the_singular_llama_view_is_preserved_for_existing_consumers() -> None:
    """The brief asked for no duplicate panels and no broken compatibility."""
    state = S.autokernel_current_state()
    assert "production_kernel" in state and "production_kernel_set" in state
    assert state["production_kernel"]["branch"] == "production-consolidated-v9"


@pytest.mark.parametrize("field", ["ggml", "branch", "head"])
def test_each_speech_kernel_projects_the_identity_fields_that_must_match(field) -> None:
    """ggml generation is load-bearing: the three trees run three generations, and a
    binary inheriting another tree's ggml runs silently wrong (CLAUDE.md)."""
    speech = S._speech_kernel_summary()
    assert speech["available"] is True
    for kernel in speech["kernels"]:
        assert kernel[field], f"{kernel['key']} is missing {field}"


def test_the_panel_declares_its_own_receipt_coverage() -> None:
    """A curated view must say it is curated.

    Measured at audit time: 5 receipt schemas projected, 29 further schemas across 98
    receipt files present under the probe root and not shown. Most are legitimately
    intermediate, so the repair is not "render them all" — it is that a reader acts on
    what the page implies, and silence implied completeness.
    """
    coverage = S.autokernel_current_state()["receipt_coverage"]
    assert coverage["projected_schemas"], "coverage must enumerate what it shows"
    assert coverage["probe_root"]
    assert "CURATED" in coverage["note"] and "not absence of evidence" in coverage["note"]


def test_every_contract_section_reaches_the_page_no_allowlist() -> None:
    """Loop-state reconciliation (KRD-AUDIT-20260812, scope arm 1).

    The contract-v2 producer exports the AutoKernel loop's own state — campaign,
    champion, release_package, backend_standing, blocking_conditions, headroom,
    resource_claims. The page must receive ALL of them, so that coverage cannot
    silently lag the producer when a new section is added.

    CORRECTION WORTH KEEPING: I first "found" that resource_claims and headroom were
    rendered nowhere, by counting their name in kernel.html and getting 0. That
    counted BESPOKE DETAIL BRANCHES, not rendering — the renderer iterates
    Object.keys(sections) and always drew them. A grep count standing in for the
    property, which is the same proxy-key error twice over. The real gap was small:
    those two fell through to the bare word "reported", discarding their content.
    """
    import json as _json
    payload = S.kernel_payload()
    if (payload.get("_render") or {}).get("mode") != "contract_v2":
        pytest.skip("live contract is not v2 on this host")
    contract = _json.loads(Path(S.KERNEL_DASHBOARD_JSON).read_text(encoding="utf-8"))
    assert set(payload["sections"]) == set(contract["sections"]), (
        "the page must receive every section the producer exports — a filtered view "
        "would make a newly added section invisible by construction")


def test_not_reported_sections_are_flagged_not_silently_empty() -> None:
    """`not_reported` is a VALUE, not an omission — the incident-8 distinction."""
    payload = S.kernel_payload()
    if (payload.get("_render") or {}).get("mode") != "contract_v2":
        pytest.skip("live contract is not v2 on this host")
    unreported = set((payload.get("_freshness") or {}).get("unreported") or ())
    silent = {n for n, s in payload["sections"].items()
              if isinstance(s, dict) and s.get("status") == "not_reported"}
    assert silent <= unreported, f"not_reported sections missing from freshness: {silent - unreported}"


def test_stable_link_drift_is_loud_and_breaks_the_fold(tmp_path: Path) -> None:
    wrong = tmp_path / "wrong"
    wrong.mkdir()
    links = {name: dict(spec) for name, spec in S.PRODUCTION_KERNEL_SLOTS.items()}
    drift = tmp_path / "cpu"
    drift.symlink_to(wrong)
    links["cpu"] = {**links["cpu"], "stable_link": drift}
    result = S.production_kernel_set(kernel_slots=links)
    assert result["intact"] is False
    assert any("STABLE LINK DRIFT" in alarm for alarm in result["alarms"])


def test_foreign_ggml_linkage_is_loud(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    binary = tmp_path / "binary"
    binary.write_bytes(b"ELF fixture")
    foreign = tmp_path / "foreign" / "libggml.so.0"
    foreign.parent.mkdir()
    foreign.write_bytes(b"")

    class Result:
        returncode = 0
        stderr = ""
        stdout = f"libggml.so.0 => {foreign} (0x1)\n"

    monkeypatch.setattr(S.subprocess, "run", lambda *a, **kw: Result())
    result = S._linked_library_identity("fixture", binary, tmp_path / "expected")
    assert result["matches"] is False
    assert "FOREIGN GGML LINKAGE" in result["error"]


def test_ldd_failure_is_unverified_not_green(monkeypatch: pytest.MonkeyPatch,
                                              tmp_path: Path) -> None:
    binary = tmp_path / "binary"
    binary.write_bytes(b"ELF fixture")

    class Result:
        returncode = 1
        stderr = "not a dynamic executable"
        stdout = ""

    monkeypatch.setattr(S.subprocess, "run", lambda *a, **kw: Result())
    result = S._linked_library_identity("fixture", binary, tmp_path)
    assert result["matches"] is None
    assert "unverifiable" in result["error"]


def test_wrong_ggml_generation_is_loud(tmp_path: Path) -> None:
    tree = tmp_path / "kernel" / "ggml"
    tree.mkdir(parents=True)
    (tree / "CMakeLists.txt").write_text(
        "set(GGML_VERSION_MAJOR 0)\nset(GGML_VERSION_MINOR 17)\n"
        "set(GGML_VERSION_PATCH 0)\n", encoding="utf-8")
    result = S._ggml_generation_identity(tree.parent, "0.18.0")
    assert result["matches"] is False
    assert "GENERATION DRIFT" in result["error"]


def test_unattested_llama_ggml_generation_keeps_the_fold_pessimistic() -> None:
    """The v9 operator artifact currently omits ggml; the page must say so, not infer."""
    result = S.production_kernel_set()
    llama = next(m for m in result["members"] if m["key"] == "llama_cpp")
    assert llama["ggml_generation"]["observed"] == "0.16.0"
    assert llama["ggml_generation"]["matches"] is None
    assert result["intact"] is False
    assert any("ggml generation unverified" in alarm for alarm in result["alarms"])
