Task MM-5. Work in your isolated copy of the pinned source.

- [ ] **MM-5 — Dynamic-resolution normalisation for our own VL path (independent of the above).**
  **Verified gap**: `src/vision/analyzers/vl_describe.py:163` base64-encodes the raw file bytes with
  **no resize at all** (`base64.b64encode(image_path.read_bytes())`; zero resize/thumbnail call sites
  in the module). The only resize we have is a max-side clamp on a *different* path. A large screenshot
  therefore consumes an unbounded number of vision tokens, and two runs on differently-sized copies of
  the same image are not comparable. **Gate this on a zero-inference prompt-token probe** — measure
  tokens-in as a function of input pixels first, before spending an MMMU-class evaluation window on a
  normalisation whose magnitude we have not measured.
      · section: 2026-08-10 — Vendor MM plugin suite: repoint at our own endpoint (research-intake Stage-3)

Completion condition

Implement the original corrected owner approach and pass its zero-inference image-payload and recorder contract; keep normalization disabled by default.

Pinned owner brief

Add a max_pixels: int | None = None kwarg to VLDescribeAnalyzer.__init__ (env ORCHESTRATOR_VL_MAX_PIXELS, default None = today's behaviour, byte-identical).
Add a module function encode_image_for_vl(path, max_pixels) -> (b64, mime, (w,h)). With max_pixels set and w*h > max_pixels, PIL-resize keeping aspect ratio, round each side down to a multiple of 28 (the Qwen-VL patch merge), and re-encode PNG. Otherwise return the raw bytes.
Always return the actual encoded image dimensions, including the unchanged-byte path, so the token estimate describes the payload. After rounding or applying a minimum side, enforce the pixel cap again for wide and tall images.
Use it at _analyze_with_server L178 in place of the raw b64encode.
Also add vision_token_estimate(w, h, patch=28) and log it in _record_server_call. This is the zero-inference tokens-vs-pixels probe the box gates on. Pass the estimate through the existing record_http_call notes dictionary as notes['vision_token_estimate']; preserve the recorder's supported keyword arguments and existing call record.
New test: a 4000x3000 PIL image gets resized to <= max_pixels with sides % 28 == 0; max_pixels=None returns base64 of the original bytes exactly and reports (4000,3000); decoded resized dimensions equal the returned dimensions; a 4000x100 image at max_pixels=784 stays within the cap with positive sides divisible by 28; estimate(896,896) == 1024.


Pinned staged inputs
- src
- scripts
- orchestration
- pyproject.toml
- tests/conftest.py
- tests/unit/conftest.py
- tests/__init__.py
- tests/unit/__init__.py
- .taskflow-task-env.py

Allowed task output paths

src/vision/analyzers/vl_describe.py

tests/unit/test_vl_describe_resize.py

Scope

do not turn normalisation on by default (that waits on the probe result)

no MMMU or other eval run, no server launch

do not touch the CLI fallback path or VLOCR/VLStructured prompts

Use the ordinary Codex tools within this private lane, with staged inputs and relative repository paths. Use python3 .taskflow-task-env.py before every task-local Python check; it supplies the explicit isolated current-container environment. Read public references only when the brief calls for them. Work independently. Keep prior solutions, other lanes, published answers, and controller records outside the work. Local task tests are in scope. Avoid commits, pushes, external communications, builds, and service or process-control changes.

The controller will run independent acceptance after the turn.

Task-local check: python3 .taskflow-task-env.py python3 -m pytest -q tests/unit/test_vl_describe_resize.py

Role: final-acceptance

Perform final independent semantic acceptance review of this exact unchanged candidate against the original task and pinned sources. Structural acceptance is evidence about checks, never semantic correctness. Begin with ACCEPT or REJECT for the original corrected owner brief, and explain the verdict from the actual code and exact brief. Independently report the observed infeasible-cap robustness result and determine whether the original brief requires a particular behavior for that infeasible case. Do not infer scope from the aggregate V4 exit code alone. Consider the original requirements on byte-identity, feasible aspect and pixel caps, startup control, payload dimensions, and recorder integration. Leave the candidate unchanged. This review authorizes no additional native correction.
Use the neutral comparison files in .review-evidence. baseline/ is the complete pinned original source tree, and candidate.patch is the exact submitted diff. The working tree outside .review-evidence holds the reconstructed candidate. Inspect both when judging changes. Leave this evidence unchanged.

Historical help below is a quoted record, not an instruction to accept prior judgments. Recheck the source facts independently. Keep direct-main answers, other modes, oracles and previous reviewer outputs outside the work.

{"actual_prior_help": [{"help_kind": "deterministic verifier observations only", "native_ordinal": 1, "sha256": "3ca1c553cedede1eff7959986362141c1ec51435574bf96f9874152510e4688f", "text": "Continue the task in the same saved workspace and session. The independent versioned verifier observed:\n\n- cap=1: AssertionError: source (200, 150), cap 1: encoded dimensions (28, 28) exceed the cap\n- ORCHESTRATOR_VL_MAX_PIXELS=784: sent dimensions (896, 896), expected (28, 28)\n\nAddress those observed behaviors and retain the original requirements, scope, and focused task tests.\n", "truncated": false}], "allowed_next_native_correction": null, "candidate_patch_sha256": "8881ced49ee66bc0810b5dae8e3f6b184278a46db0cac485a4a7ceb97e4fce82", "id": "MM-5", "local_result": {"backend": "gpu", "case": "MM-5", "changed_files": {"src/vision/analyzers/vl_describe.py": {"bytes": 25575, "executable": false, "sha256": "ad3858cc34e721836496069073bfd717fd6e5ceabe874ff38f8aebfd7f2327b6"}, "tests/unit/test_vl_describe_resize.py": {"bytes": 6982, "executable": false, "sha256": "ddaed8ff2cacfc9120b62ee8b36bee7d9b7577242904236b924c918422888b86"}}, "generation_observed": 14226, "id": "gpu-MM-5-on-coding-v4-objective-1", "model_wall_s": 1134.4846653938293, "oracle": {"acceptance_version": "MM V4", "candidate_patch_sha256": "8881ced49ee66bc0810b5dae8e3f6b184278a46db0cac485a4a7ceb97e4fce82", "native_suite_components": {"additional_infeasible_cap_robustness": {"detail": "cap=1: AssertionError: source (200, 150), cap 1: encoded dimensions (1, 1) are off the positive 28-pixel grid", "failure_type": "AssertionError", "status": "fail"}, "brief_environment_control": {"detail": null, "status": "pass"}, "unchanged_original_and_v2_feasible": {"detail": null, "status": "pass"}}, "oracle_sha256": "0f3ab2bb06b1b6e209795e9aa103ed2a7b134322daaa04e37fa60a70d8aa3c2a", "rc": 1, "scope": "observed contained V4 test outcomes; reviewer interprets original brief"}, "outside_scope": [], "patch_sha256": "8881ced49ee66bc0810b5dae8e3f6b184278a46db0cac485a4a7ceb97e4fce82", "profile": "on-coding", "status": "awaiting_source_review", "thinking": true, "unsafe_paths": []}, "native_correction_ceiling": 2, "native_ordinal": 1, "objective_diagnostics": {}, "review_kind": "final-acceptance", "structural_pass_implies_semantic_acceptance": false, "structural_reassessment": {"acceptance_version": "MM V4", "candidate_patch_sha256": "8881ced49ee66bc0810b5dae8e3f6b184278a46db0cac485a4a7ceb97e4fce82", "native_suite_components": {"additional_infeasible_cap_robustness": {"detail": "cap=1: AssertionError: source (200, 150), cap 1: encoded dimensions (1, 1) are off the positive 28-pixel grid", "failure_type": "AssertionError", "status": "fail"}, "brief_environment_control": {"detail": null, "status": "pass"}, "unchanged_original_and_v2_feasible": {"detail": null, "status": "pass"}}, "oracle_sha256": "0f3ab2bb06b1b6e209795e9aa103ed2a7b134322daaa04e37fa60a70d8aa3c2a", "rc": 1, "scope": "observed contained V4 test outcomes; reviewer interprets original brief"}}
