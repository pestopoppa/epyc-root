"""Hosted synthetic APP-writer -> ROOT-reader conformance for SC42.

The named research checkout is an explicit source input. This test runs no model,
server, inference window, or repository mutation: those boundaries are replaced
with small synthetic fakes while the production adapter, writer, and ROOT reader
remain the actual implementations.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from scripts.vidya.adapters import odl_model_gated


def test_actual_odl_writer_record_projects_through_root_reader(tmp_path, monkeypatch):
    research = Path(os.environ["EPYC_INFERENCE_RESEARCH_REPO"]).resolve(strict=True)
    benchmark_package = research / "scripts" / "benchmark"
    assert (benchmark_package / "odl_bench" / "vidya_provenance.py").is_file()
    sys.path.insert(0, str(benchmark_package))
    from odl_bench import adapter as app_adapter
    from odl_bench import unlimited_ocr as app_unlimited
    from odl_bench import vidya_provenance as app_writer
    UNLIMITED_OCR_ENGINE = app_unlimited.UNLIMITED_OCR_ENGINE

    images = tmp_path / "images"
    images.mkdir()
    image_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    (images / "page1.png").write_bytes(image_bytes)
    gt_bytes = json.dumps([{"page_info": {"image_path": "page1.png"}}]).encode()
    gt_path = tmp_path / "gt.json"
    gt_path.write_bytes(gt_bytes)
    run = tmp_path / "run"
    config = app_unlimited.UnlimitedOcrConfig(
        binary=tmp_path / "not-launched-server",
        model=tmp_path / "not-opened-model.gguf",
        mmproj=tmp_path / "not-opened-mmproj.gguf",
        gpu_layers=0,
    )

    class FakeProc:
        pid = 424242
        returncode = 0

        def poll(self):
            return 0

    class FakeLease:
        path = str(tmp_path / "synthetic-inference-window.lock")
        waited_s = 0.0
        acquired_monotonic_s = time.monotonic()

    class FakeWindow:
        @contextmanager
        def hold(self):
            yield FakeLease()

    sent_images = []
    monkeypatch.setattr(app_unlimited.UnlimitedOcrProducer, "validate_inputs", lambda self: None)
    monkeypatch.setattr(app_unlimited, "_inference_call_window", lambda: FakeWindow())
    monkeypatch.setattr(app_unlimited.subprocess, "Popen", lambda *args, **kwargs: FakeProc())
    monkeypatch.setattr(app_unlimited, "wait_for_health", lambda *args, **kwargs: None)
    monkeypatch.setattr(app_unlimited, "terminate", lambda proc: {"dead": True})

    def fake_query(_config, _image_path, data=None):
        sent_images.append(data)
        return {"choices": [{"message": {"content": "synthetic OCR output"},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                "timings": {"prompt_per_second": 10.0, "predicted_per_second": 5.0}}

    monkeypatch.setattr(app_unlimited, "query_page", fake_query)
    app = app_adapter.OdlBenchAdapter(bench_root=research)
    source_before = app_writer.capture_source_identity(research)
    assert source_before["working_tree_clean"] is True
    assert source_before["commit"] == os.environ["EPYC_INFERENCE_RESEARCH_COMMIT"]
    row_set = app.build_model_gated_row_set(
        gt_path, run, engine=UNLIMITED_OCR_ENGINE, image_root=images,
        allow_inference=True, unlimited_config=config, do_score=False,
    )
    # This is the exact model-gated CLI row-set write performed before its
    # prospective writer call; build_model_gated_row_set itself only returns it.
    row_set_path = run / "model_gated_row_set.json"
    row_set_path.write_text(json.dumps(row_set.to_dict(), indent=2), encoding="utf-8")
    record_path = app_writer.write_unlimited_ocr_record(
        run_dir=run,
        response_dir=run / "responses" / UNLIMITED_OCR_ENGINE,
        prediction_dir=run / "predictions" / UNLIMITED_OCR_ENGINE,
        gt_json=gt_path,
        row_set=json.loads(row_set_path.read_bytes()),
        config=config,
        source_before=source_before,
    )

    native = odl_model_gated.native_rows(record_path)
    assert len(native) == 1
    claim = odl_model_gated.project_unlimited_ocr_run(native[0])
    assert claim.metric == "latency_ms_median"
    assert claim.reps == 1
    assert claim.category == "CANDIDATE"
    inputs = native[0]["payload"]["inputs"]
    assert inputs["ground_truth"]["sha256"] == hashlib.sha256(gt_bytes).hexdigest()
    assert inputs["images"][0]["sha256"] == hashlib.sha256(image_bytes).hexdigest()
    assert sent_images == [image_bytes]
    assert native[0]["payload"]["locator"]["input_manifest"] == str(
        run / "responses" / UNLIMITED_OCR_ENGINE / "producer_input_manifest.json"
    )
