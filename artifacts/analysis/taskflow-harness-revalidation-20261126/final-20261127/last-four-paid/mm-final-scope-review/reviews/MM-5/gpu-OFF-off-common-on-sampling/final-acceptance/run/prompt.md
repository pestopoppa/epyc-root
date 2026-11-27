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

{"actual_prior_help": [{"help_kind": "deterministic verifier observations only", "native_ordinal": 1, "sha256": "d285bf86c3b939b91284a3bb770abec0110c367ec1139074d61b7f9127f7e7fe", "text": "Continue the same task and scope from the saved workspace and session.\n\nThe independent verifier reported:\n\nsource (100, 4000), cap 7840: encoded dimensions (28, 28) lose source orientation.\n\nAddress that observed failure. Preserve the original requirements and rerun the task-local check.\n", "truncated": false}, {"help_kind": "deterministic verifier observations only", "native_ordinal": 2, "sha256": "a75ac13b0028e6281782cc84a6a1a931a95ceae601cb7d044eaa63fe33181073", "text": "Continue the task in the same saved workspace and session. The independent versioned verifier observed:\n\n- cap=1: encoder did not return within 8 seconds\n\nAddress those observed behaviors and retain the original requirements, scope, and focused task tests.\n", "truncated": false}], "allowed_next_native_correction": null, "candidate_patch_sha256": "b9a257627af85dc1f2f024afee7aac3d2675f48a1ebec65c502b5a08f0c0c80b", "id": "MM-5", "local_result": {"backend": "gpu", "case": "MM-5", "changed_files": {"src/vision/analyzers/vl_describe.py": {"bytes": 25134, "executable": false, "sha256": "d2925db56a8210bc0fda465164ff06852bfbdf6a595696edac570ce4d67c6090"}, "tests/unit/test_vl_describe_resize.py": {"bytes": 8387, "executable": false, "sha256": "04ed9e60a7cb373bd526d121ae14f94adf8396f733fea5132ac32363c3e1a267"}}, "generation_observed": 5032, "id": "gpu-MM-5-off-common-on-sampling-v4-objective-2", "model_wall_s": 585.8623330593109, "oracle": {"acceptance_version": "MM V4", "candidate_patch_sha256": "b9a257627af85dc1f2f024afee7aac3d2675f48a1ebec65c502b5a08f0c0c80b", "native_suite_components": {"additional_infeasible_cap_robustness": {"detail": "cap=1: AssertionError: source (200, 150), cap 1: encoded dimensions (28, 28) exceed the cap", "failure_type": "AssertionError", "status": "fail"}, "brief_environment_control": {"detail": null, "status": "pass"}, "unchanged_original_and_v2_feasible": {"detail": null, "status": "pass"}}, "oracle_sha256": "0f3ab2bb06b1b6e209795e9aa103ed2a7b134322daaa04e37fa60a70d8aa3c2a", "rc": 1, "scope": "observed contained V4 test outcomes; reviewer interprets original brief"}, "outside_scope": [], "patch_sha256": "b9a257627af85dc1f2f024afee7aac3d2675f48a1ebec65c502b5a08f0c0c80b", "profile": "off-common-on-sampling", "status": "awaiting_source_review", "thinking": false, "unsafe_paths": []}, "native_correction_ceiling": 2, "native_ordinal": 2, "objective_diagnostics": {}, "review_kind": "final-acceptance", "structural_pass_implies_semantic_acceptance": false, "structural_reassessment": {"acceptance_version": "MM V4", "candidate_patch_sha256": "b9a257627af85dc1f2f024afee7aac3d2675f48a1ebec65c502b5a08f0c0c80b", "native_suite_components": {"additional_infeasible_cap_robustness": {"detail": "cap=1: AssertionError: source (200, 150), cap 1: encoded dimensions (28, 28) exceed the cap", "failure_type": "AssertionError", "status": "fail"}, "brief_environment_control": {"detail": null, "status": "pass"}, "unchanged_original_and_v2_feasible": {"detail": null, "status": "pass"}}, "oracle_sha256": "0f3ab2bb06b1b6e209795e9aa103ed2a7b134322daaa04e37fa60a70d8aa3c2a", "rc": 1, "scope": "observed contained V4 test outcomes; reviewer interprets original brief"}}
