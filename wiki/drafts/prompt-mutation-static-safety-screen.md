# Draft — PromptForge mutation safety: the static screen, the effect enum, and the prompt/denylist drift guard

**Target page**: [safety.md](../safety.md) — fold as a new `### New (2026-09-14, …)` block under *Key Findings*, adjacent to the 2026-08-16 *promotion-gate integrity* block (same subject: what authority an automated optimizer holds over production code).
**Category**: `safety` (secondary: `autonomous_research`, `agent_architecture`)
**Confidence**: verified — read from `epyc-orchestrator` source at `origin/main` `35b05fde`; fix landed `7d4b40a8` + `c27eec6c`; 100 unit tests.
**Zero inference**: nothing here is a performance claim.

## Findings

- **A validator that writes the thing it is validating is not a validator.** PromptForge's Tier-2 code-mutation
  path had a four-layer `_validate_code_mutation` (`prompt_forge.py:1095` at `origin/main`) whose last layer was
  an "import test": it wrote the **model-generated candidate over the live repo file** (`:1149`), then
  `importlib.import_module()`-ed it (`:1157`) after deleting the module from `sys.modules`. Two distinct defects
  in one step. First, the candidate's **module top level executed unsandboxed in the autopilot process**, with
  that process's full filesystem and network authority — the validation step *was* the exploit. Second, for the
  duration of the check the live file on disk **was** the unvalidated candidate, so any concurrent reader (a
  parallel session, a uvicorn reload, another test run) saw it; the restore was in a `finally`, but a crash or a
  SIGKILL between write and restore left it there. A path that reverts correctly is still a path that published.
  The general rule: **validation must be a pure function of the candidate text.** If a check needs to run the
  candidate, that is a separate subprocess with a temp copy, a timeout, and no repo path on `sys.path` — never
  the live tree and never in-process.

- **Prefer static screening to dynamic validation when no caller consumes runtime behaviour.** The import test's
  stated purpose was "actually importable, no circular imports". Its single caller reads only `(valid, reason)`.
  So the replacement is `screen_static_safety()` — `ast.parse` plus a denylist walk — and there is no subprocess
  at all. Dynamic validation was removed rather than sandboxed, because a sandbox is a permanent maintenance
  surface bought for a check nobody's contract needed.

- **The denylist is three profiles, not one list.** (a) *Module level* may hold only a docstring, imports,
  defs/classes, and assignments — a bare top-level call is the "does work at import time" signature. (b)
  *Capability*: imports must be in a 30-entry pure-stdlib allowlist or a first-party root (`src`, `scripts`,
  `orchestration`); `os`/`subprocess`/`sys`/`pathlib`/`pickle`/`ctypes`/`importlib`/`socket`/`requests`/… are
  banned; `exec`/`eval`/`compile`/`__import__`/`globals`/`locals`/`vars`/`input`/`breakpoint`/`memoryview` are
  never callable; `open`/`getattr`/`setattr`/`delattr` are restricted; attribute calls rooted at a banned module
  (`os.system`, `subprocess.run`) and any `.system`/`.popen`/`.spawn` are rejected; dunder attribute access is
  rejected except `__name__`/`__doc__`/`__all__`, because `__class__.__subclasses__` is the standard escape. (c)
  *Strict inertness* for `new_file` proposals — the ratified `intake-1323` node denylist (Import, ImportFrom,
  With, While, Lambda, ClassDef, Raise, Global, Delete, Yield, Await) plus rejection of any underscore-prefixed
  name or attribute.

- **Grandfathering is what makes a capability denylist deployable on existing files.** A whole-file screen over
  a real module rejects the module itself: `src/api/routes/chat.py` already calls `getattr`, and the allowlisted
  files import first-party code freely. So the screen parses the **original** too and grandfathers the import
  roots and dotted call names it already contained — a mutation is judged on **what it adds**, not on what the
  file has always done. The hard-banned call set is deliberately exempt from grandfathering. A parameterized test
  asserts a no-op mutation of every one of the five allowlisted files passes; that test is the guard against a
  future denylist entry silently disabling the whole lane.

- **A closed effect enum, normalized totally.** `MutationEffect` = `inert | constrain | expand | replace |
  unsafe | unknown`, carried on `CodeMutation.effect` and reported by both apply paths, which refuse `unsafe`.
  `normalize()` is **total** — aliases (`noop`, `override`, `add-only`, `MutationEffect.expand`) map in, and
  anything unrecognised becomes `UNKNOWN` rather than defaulting to benign; tokens truncate at 32 chars and
  reasons at 240, so model text can never arrive unbounded. The CONSTRAIN/REPLACE split is **derived
  mechanically** from the candidate (no original definition removed and no original line removed ⇒ add-only ⇒
  CONSTRAIN; a new top-level def ⇒ EXPAND; otherwise REPLACE), which answers this lane's standing question of
  whether the CONSTRAIN/REPLACE risk prior needs its own label. It does not.

- **An enforced denylist and a prompt that asks for the forbidden shape is a silent, total lane failure — and
  the drift guard belongs in a test.** Making inertness compile-time exposed that the MH-9 AutoMem
  `schema_evolution` prompt (`prompt_forge.py:1264` at `origin/main`) asked the model for a `MemoryAction` /
  `MemoryActionStore` *contract* — i.e. a class, with `from dataclasses import dataclass` — which the strict
  profile rejects outright. Nothing would have errored: the lane would have proposed only rejects, forever,
  logged at WARNING. The ratified denylist was kept and the prompt rewritten to the shape the screen admits
  (module constants + pure public `def`s returning `(ok, reason)` instead of raising, no imports, no classes, no
  underscore names), with the rules stated to the model as enforcement rather than etiquette. The durable
  mechanism: the example the prompt ships is a **module constant** (`MEMORY_SCHEMA_SHAPE_EXAMPLE`) and a test
  screens **that exact text** through `screen_static_safety(strict=True)`, plus a negative test that the old
  class-shaped proposal is rejected for ClassDef + ImportFrom + Raise. **Any prompt that describes a shape an
  enforcement surface checks should ship that shape as a constant and screen it in CI** — otherwise the two
  drift apart and the failure is invisible.

## Open questions

- Should the strict profile admit an inert `ClassDef` and an allowlisted `ImportFrom` (a plain dataclass is
  harmless at import time), or is the prompt-side fix the permanent answer? Kept as-is because the denylist is
  ratified from `intake-1323`; the tradeoff is expressiveness in the schema-evolution lane against one more
  admitted node class.
- `apply_code_mutation` still writes the live file (git-checkpointed, pre-commit) rather than staging to a
  worktree first. `apply_code_mutation_in_context` is the isolated path and exists; nothing forces its use.
- `MutationEffect.UNKNOWN` is permitted by the apply gate (only `UNSAFE` is refused), so a hand-constructed
  `CodeMutation` that never passed the screen can still apply. Tightening to "only screened effects apply"
  requires auditing every construction site.

## Related

- `handoffs/active/promptforge-mutation-safety-contract.md` (RTG-55, MHS-1/MHS-2)
- `safety.md` → *promotion-gate integrity* (2026-08-16): same trust boundary, scored from the other side
- `docs/guides/meta-harness-operator-guide.md` → *The 4-layer validation*
- Defect class also recorded in this session's `progress/2026-09/2026-09-14.md`
