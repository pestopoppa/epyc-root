# Codebase Refactoring Analysis

Analyze a code scope for technical debt and produce an actionable refactoring handoff.

**Target scope:** $ARGUMENTS

## Your Task

Analyze the specified scope (module path, file, directory, or description like "the routing layer") and produce a refactoring handoff at `handoffs/active/refactoring.md`. This handoff is **recurring** — it is never archived, only reset after implementation.

If `$ARGUMENTS` is empty, analyze the entire `src/` tree and prioritize the worst areas.

## Analysis Steps

### Step 1: Scope Discovery

Map the target's boundaries:

```bash
# File inventory
find $ARGUMENTS -type f -name "*.py" | head -100

# Line counts
find $ARGUMENTS -name "*.py" -exec wc -l {} + | sort -rn | head -20

# Import graph (who depends on what)
grep -rn "^from \|^import " $ARGUMENTS --include="*.py" | head -50
```

Identify:
- All files in scope with line counts
- External dependencies (imports from outside the scope)
- Internal dependency graph (which files import which)
- Public API surface (what other modules call into this scope)

### Step 2: Complexity Analysis

For each file in scope, assess:

**Structural complexity:**
- Functions/methods over 50 lines (extract candidates)
- Classes over 300 lines (split candidates)
- Files over 500 lines (decomposition candidates)
- Nesting depth > 3 levels (flatten candidates)

**Duplication:**
- Near-identical code blocks across files
- Copy-paste patterns (similar structure, different names)
- Repeated boilerplate that could be abstracted

**Dead code:**
- Unreachable branches, unused imports, commented-out blocks
- Functions/classes with zero callers (verify with grep)
- Feature-flagged code where the flag is permanently on/off

**Naming and clarity:**
- Inconsistent naming conventions within the scope
- Misleading names (function does more/less than name implies)
- Magic numbers or hardcoded strings that should be constants/config

### Step 3: Dependency & Coupling Analysis

Map problematic coupling patterns:

- **Circular imports**: A imports B imports A
- **God modules**: Files that everything depends on
- **Shotgun surgery**: A single logical change requires touching 5+ files
- **Feature envy**: Functions that use more of another module's data than their own
- **Layer violations**: Lower layers importing from higher layers

Use this to identify natural module boundaries and refactoring seams.

### Step 4: Test & Coverage Analysis

Map the testing landscape for the scope:

**Coverage mapping:**
```bash
# Find test files corresponding to source files in scope
for src in $(find $ARGUMENTS -name "*.py" -not -name "__init__.py"); do
  base=$(basename "$src" .py)
  match=$(find tests/ -name "test_${base}.py" 2>/dev/null)
  if [ -n "$match" ]; then
    echo "✓ $src → $match"
  else
    echo "✗ $src → NO TEST FILE"
  fi
done
```

For each source file, determine:
- **Has test file?** Does `tests/unit/test_{name}.py` or `tests/integration/test_{name}.py` exist?
- **Coverage depth**: Does the test file actually exercise the key functions, or just import the module? Check for test methods that call the source's public API.
- **Untested paths**: Identify public functions/classes in the source that have zero test coverage (grep test files for function names).

**Test quality assessment:**
- **Duplicated setup**: Repeated fixture construction across test files (should be in `conftest.py`)
- **Overly broad assertions**: Tests that assert `True` or just check `is not None` without verifying behavior
- **Dead fixtures**: `conftest.py` fixtures that no test actually uses
- **Brittle mocking**: Tests that mock internals so heavily they'd pass even if the source is broken
- **Missing edge cases**: Only happy-path tests, no error/boundary testing

**Test-to-source coupling (from git history):**
```bash
# When source files changed, did the corresponding tests change too?
# Files that change without test updates are higher risk
git log --format='' --name-only --since="2025-12-01" -- $ARGUMENTS | sort -u | while read src; do
  base=$(basename "$src" .py)
  test_changes=$(git log --format='' --name-only --since="2025-12-01" -- "tests/**/test_${base}.py" | wc -l)
  echo "$src → test changes: $test_changes"
done
```

**CI/gate constraints:**
- Read `Makefile` targets (`gates`, `unit`, `test-all`) to understand what the refactoring must not break
- Check `tests/conftest.py` for shared fixtures, memory guards, or environment assumptions
- Note any test markers (`@pytest.mark.slow`, `@pytest.mark.integration`) that affect which tests run when

**Output of this step feeds into prioritization:**
- Untested source code gets a **risk multiplier** in the priority score — it needs tests *before* refactoring (Phase 0)
- Source files with test quality issues get their test cleanup bundled into the same phase as the source refactoring
- Test-only debt (dead fixtures, duplication in test files) gets its own entries in the issue inventory

### Step 5: Risk-Prioritized Issue List

For each issue found, score it:

```
Priority = (Severity × Change_Frequency × Risk_Multiplier) / Effort
```

Where:
- **Severity** (1-5): How much does this hurt readability, correctness, or extensibility?
- **Change_Frequency** (1-5): How often does this code get modified? (check git log)
- **Risk_Multiplier**: 1.0 if well-tested, 1.5 if partially tested, 2.0 if untested (from Step 4)
- **Effort** (1-5): How many files/lines need to change?

```bash
# Check change frequency for files in scope
git log --oneline --since="2025-12-01" -- $ARGUMENTS | wc -l
git log --format='' --name-only --since="2025-12-01" -- $ARGUMENTS | sort | uniq -c | sort -rn | head -20
```

### Step 6: Design the Refactoring Plan

For each prioritized issue, determine:

1. **What changes**: Exact files and functions affected
2. **How to change**: Concrete approach (extract method, split module, introduce interface, etc.)
3. **Verification**: How to confirm the change didn't break anything
4. **Dependencies**: Which changes must happen before others

Group changes into implementation phases where each phase:
- Is independently deployable (doesn't leave the codebase half-refactored)
- Has a clear verification step
- Touches a bounded set of files
- **Phase 0** (if needed): Add missing tests for untested code that later phases will refactor
- Bundle test cleanup (dead fixtures, duplicated setup) with the source refactoring it relates to

### Step 7: Write the Handoff

Write the refactoring handoff to `handoffs/active/refactoring.md` using the template below. If the file already exists with stale content, overwrite it — this handoff is recurring.

Include:
- Concrete file paths with line numbers
- Code sketches for non-obvious transformations
- Copy-paste ready verification commands
- Feature flag recommendation if the change is risky

### Step 8: Validate

```bash
# Ensure the handoff is well-formed and referenced files exist
for f in $(grep -oP '`[^`]*\.py`' handoffs/active/refactoring.md | tr -d '`'); do
  [ -f "$f" ] && echo "✓ $f" || echo "✗ MISSING: $f"
done

# Run gates
make gates
```

## Handoff Template

The output must follow this structure:

```markdown
# Handoff: Refactoring — {Scope Description}

**Status**: READY TO IMPLEMENT
**Created**: {date}
**Updated**: {date}
**Priority**: {High/Medium/Low}
**Scope**: {path or description}
**Estimated effort**: {N changes across M files}

## Problem

{1-3 sentences: What's wrong, why it matters, what triggered this analysis}

## Test Coverage Map

| Source File | Test File | Coverage | Notes |
|-------------|-----------|----------|-------|
| `src/...` | `tests/unit/test_...` | Good / Partial / None | {key gaps} |

## Issue Inventory

| # | Issue | File:Line | Severity | Freq | Risk | Effort | Priority | Phase |
|---|-------|-----------|----------|------|------|--------|----------|-------|
| 1 | {description} | `path:NN` | 4 | 5 | 1.5 | 2 | 15.0 | 1 |
| ... | | | | | | | | |

Risk column: 1.0 = well-tested, 1.5 = partially tested, 2.0 = untested

## Phase 0: Safety Net (if needed)

{Only include if untested code will be refactored in later phases.
Add tests for critical paths BEFORE touching the source.
List specific functions needing tests and what to assert.}

## Phase 1: {Theme}

### Files to Modify

| File | Changes |
|------|---------|
| `src/...` | {specific change description} |

### Implementation Order

1. {First change — what and why}
2. {Second change — dependency on first}
3. ...

### Code Sketches (if non-obvious)

{Before/after examples for complex transformations}

### Verification

{Copy-paste ready commands: tests, grep checks, import validation}

## Phase 2: {Theme}

{Same structure as Phase 1}

## Success Criteria

1. {Measurable criterion}
2. {Test count expectation}
3. No test regressions
4. `make gates` passes

## Notes

- {Gotchas, risks, things the implementer should watch for}
```

## Important Rules

- **Do NOT implement changes** — analysis and planning only. The handoff is for a separate implementation session.
- **Every recommendation needs evidence** — file paths, line numbers, concrete examples. No generic advice.
- **Respect existing patterns** — if the codebase uses a convention (feature flags, Role enum, etc.), refactoring recommendations must preserve it.
- **Verify referenced files exist** — don't recommend changes to files that aren't there.
- **Keep phases independently deployable** — each phase should leave the codebase in a working state.
- **Check git history** — recently modified files are higher priority (active development = more pain from debt).
