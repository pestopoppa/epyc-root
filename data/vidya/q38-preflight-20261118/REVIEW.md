# Research model preflight candidate review

The candidate is based on Research `6decaeda4481a841b3a85b55b0be87a6963b3042`.
It carries an optional, caller-trusted pre-grant model identity into the runner context.
It does not establish native Q38 acceptance or live Research adoption.

Reviewed paths under `scripts/kernel_rnd/autokernel/loop/`:

- `belief_model_preflight.py`: preflight resolves a single-file model, hashes its open
  descriptor against the expected digest, and compares descriptor and named-file identity
  before and after reading. Runtime verification compares the selected launch path/digest
  and device, inode, size, mtime and ctime without reading model content. Split models
  require a separate whole-model identity contract and are refused here.
- `run.py`: the explicit receipt is checked before the selected serving workflow proceeds;
  context construction rechecks identity before assigning `current_regime.model.sha256`.
  The option requires a selected serving launch. Without it, the model remains path-only.
- `belief_context.py`: forwards the authored digest into the existing reader target.
- `serial_run.py`: preserves the receipt as an input document for child invocations.
- The new preflight refusal controls cover wrong digest, missing receipt, alias replacement,
  same-length mutation with restored mtime, and split models. The existing GPU test helper
  accepts an optional prepared model artifact, preserving its default behavior while
  avoiding fixture rehashing inside this control.

The preflight receipt is trusted prepared input, not an independent signature or a new
measurement warrant. Its model file must stay outside the allocator work directory:
allocator permission changes alter ctime and correctly invalidate the receipt. A new
preflight is needed after changing the file, target or selected launch identity.

The queued structural control must use immutable source identities. Detached worktrees
share remote refs; freshness against moving `origin/main` cannot serve as an immutable
packet pin. Any isolated pinned-reader override must stay within the control and leave
the live reader freshness gate intact.

The original synthetic shared-planner control is filed separately at
`data/vidya/mi210-q38-planner-control-20261118/official/`.
