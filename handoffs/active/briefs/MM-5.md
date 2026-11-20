---
schema: epyc.brief.v1
id: MM-5
box_text_sha: t:1b785876f77d2df9
author: owner
written: '2026-11-20'
accepted: pending
where:
- epyc-orchestrator:src/vision/analyzers/vl_describe.py::VLDescribeAnalyzer
- epyc-orchestrator:src/vision/analyzers/vl_describe.py::VLDescribeAnalyzer._analyze_with_server
- epyc-orchestrator:src/vision/pipeline.py::create_thumbnail
approach: 'Add a max_pixels: int | None = None kwarg to VLDescribeAnalyzer.__init__ (env ORCHESTRATOR_VL_MAX_PIXELS, default
  None = today''s behaviour, byte-identical).

  Add a module function encode_image_for_vl(path, max_pixels) -> (b64, mime, (w,h)). With max_pixels set and w*h > max_pixels,
  PIL-resize keeping aspect ratio, round each side down to a multiple of 28 (the Qwen-VL patch merge), and re-encode PNG.
  Otherwise return the raw bytes.

  Use it at _analyze_with_server L178 in place of the raw b64encode.

  Also add vision_token_estimate(w, h, patch=28) and log it in _record_server_call. This is the zero-inference tokens-vs-pixels
  probe the box gates on.

  New test: a 4000x3000 PIL image gets resized to <= max_pixels with sides % 28 == 0; max_pixels=None returns base64 of the
  original bytes exactly; estimate(896,896) == 1024.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_vl_describe_resize.py
new_tests:
- epyc-orchestrator:tests/unit/test_vl_describe_resize.py
non_goals:
- do not turn normalisation on by default (that waits on the probe result)
- no MMMU or other eval run, no server launch
- do not touch the CLI fallback path or VLOCR/VLStructured prompts
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/vision/analyzers/vl_describe.py: 2e2f88a8e33017d98eef07256733d907a5dc4922
    epyc-orchestrator:src/vision/pipeline.py: b3dcb9634ec04516112c2bdf2c34397ca57c30b9
---
