"""Synthetic fetch-to-anchor boundary fixtures; no live source or model call."""

from __future__ import annotations

import email.message
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import machine_anchor  # noqa: E402


@pytest.fixture
def fetch_store(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_VIDYA_RAW_ANCHOR_ROOT", str(tmp_path / "raw-vault"))

    def fetch(name: str, body: bytes | None, media_type: str = "text/html"):
        url = f"https://fixtures.invalid/{name}"
        if body is None:
            def unavailable(*_args, **_kwargs):
                raise urllib.error.HTTPError(url, 404, "missing synthetic page", {}, None)

            monkeypatch.setattr(machine_anchor.urllib.request, "urlopen", unavailable)
        else:
            class Response:
                def __init__(self):
                    self.headers = email.message.Message()
                    self.headers["Content-Type"] = f"{media_type}; charset=utf-8"

                def __enter__(self):
                    return self

                def __exit__(self, *_args):
                    return False

                def read(self, _limit):
                    return body

                def geturl(self):
                    return url

            monkeypatch.setattr(machine_anchor.urllib.request, "urlopen", lambda *_a, **_k: Response())
        return url, machine_anchor.fetch_document(url)

    return fetch


FIXTURES = (
    (
        "abstract-only",
        ("<html><body><p>We describe a new method for long-context reasoning and evaluate it "
         "on several tasks. The abstract introduces the architecture, training procedure, "
         "and experimental setting. It gives no detailed benchmark result, no comparison table, "
         "and no reported numerical outcome. " * 3 + "</p></body></html>").encode(),
        "The method improves long-context benchmark accuracy by 48 percent.",
    ),
    (
        "results-table-stripped",
        ("<html><body><p>The study compares the proposed method with a baseline across four "
         "benchmark tasks. The extracted page contains the introduction and methods, while the "
         "results table is unavailable in this representation. The text describes the evaluation "
         "protocol and hardware but contains no outcome figures or comparative measurements. " * 3
         + "</p></body></html>").encode(),
        "The proposed method improves benchmark accuracy by 37 percent.",
    ),
    (
        "figure-number-only",
        ("<html><body><figure><img src='figure3.png'><figcaption>Figure 3 plots accuracy "
         "curves for each model and condition. The image itself is not represented in extracted "
         "text. The surrounding paper describes the evaluation protocol, datasets, and model "
         "families, but does not state a numeric outcome in this caption. " * 3
         + "</figcaption></figure></body></html>").encode(),
        "Model accuracy reaches 91.4 percent in the full-data condition.",
    ),
    (
        "readme-without-license",
        ("This repository contains experimental code for model evaluation. Setup instructions "
         "and examples follow. The README explains how to install dependencies, prepare data, "
         "run the evaluation script, and inspect generated output. It identifies no license "
         "grant or redistribution terms in the supplied text. " * 4).encode(),
        "The repository is licensed under MIT.",
    ),
)


@pytest.mark.parametrize("name,raw,claim", FIXTURES, ids=[row[0] for row in FIXTURES])
def test_retained_synthetic_response_can_propose_no_anchor(name, raw, claim, fetch_store):
    url, (document, artifact) = fetch_store(name, raw)
    assert artifact is not None
    assert document is not None and len(document) > 400
    entry = {"url": url, "key_claims": [claim]}
    anchors = machine_anchor.anchor_entry(entry, document=document, source_artifact=artifact)
    # This asserts only that the current mechanical locator proposed no span. It does not
    # adjudicate whether the source semantically supports/refutes the claim or whether a
    # repository is legally licensed; the README case lacks enough locator terms by design.
    assert anchors == []


def test_missing_synthetic_source_is_unknown_not_a_negative_claim(fetch_store):
    url, (document, artifact) = fetch_store("missing", None)
    assert document is None and artifact is None
    # A failed fetch creates no source record and no evidence about the claim's truth.
    assert url.endswith("/missing")


def test_present_claim_is_positive_control_from_retained_response(fetch_store):
    body = ("<html><body><p>We compare several decoding paths on long sequences and summarize "
            "the implementation boundaries for each method. The state-recomputation kernel is "
            "written to a fixed 64-wide block dimension throughout. Compiler diagnostics record "
            "memory movement, launch structure, and device-specific scheduling. The evaluation "
            "uses multiple model families and hardware targets, with setup details described "
            "separately from the numerical results. Ablation notes explain which modules are "
            "enabled for each run and distinguish the reference configuration from optimizations. "
            "The appendix gives environment details, source revisions, and limitations of the "
            "measurement process for future replication.").encode()
    url, (document, artifact) = fetch_store("positive", body)
    claim = "The state-recomputation kernel uses a fixed 64-wide block dimension."
    assert artifact is not None and document is not None
    anchors = machine_anchor.anchor_entry(
        {"url": url, "key_claims": [claim]}, document=document, source_artifact=artifact
    )
    assert len(anchors) == 1
    assert anchors[0]["quote"] in document
    assert machine_anchor.verify_source_anchor(anchors[0], entry_url=url, claim=claim) == (True, "verified")
