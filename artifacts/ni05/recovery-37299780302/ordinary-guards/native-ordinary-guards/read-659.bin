"""Conformance suite for the reload/teardown disposal contract.

WHY THIS FILE EXISTS AND WHY MOST OF IT IS xfail
------------------------------------------------
The 2026-08-20 research intake dived Cordis (intake-1208 / intake-1209), a framework whose
headline claim is *reversible effects*, and measured four reentrant disposal defects in it by
execution. Porting those probes here answered a standing question from intake-1180:

    "Does our reload path revert everything a component registered, or only what someone
     remembered to unregister?"

Measured answer: **only what someone remembered.** There is no disposer registry in this codebase
at all -- `disposer`, `AsyncExitStack`, `weakref.finalize` and `register_cleanup` each return zero
files across `src/`, against 22 `register*` entry points and zero unregister functions. And
`orchestrator_stack.py reload orchestrator` is kill-by-port + `sleep 1` + restart, i.e. a
SIGTERM/SIGKILL escalation with no drain, which contradicts axiom 4's quiesce-and-drain.

So these tests cannot exercise a registry -- there is nothing to exercise. They do two jobs:

1. `TestDisposerRegistryGap` is a **gap witness**. It passes today *because* the gap exists. When
   someone builds a registry it will FAIL, which is the signal to replace it with the real
   conformance tests below.
2. The five invariant tests are `xfail(strict=True)`. They encode the contract now, while the
   reasoning is fresh, and cost nothing until the machinery exists. Strict means that if one ever
   *passes*, pytest fails the run and tells you to flip the marker -- so this file cannot silently
   rot into a green no-op.

THE CONTRACT (agents/shared/OPERATING_CONSTRAINTS.md, pending operator ratification 2026-08-20):
  1. register the inverse BEFORE the setup body runs, roll back if setup throws
  2. reject registrations while UNLOADING, re-checked under the drain's own lock
  3. teardown JOINS an in-flight cleanup, never declares completion over it   <- axiom 4
  4. pop the callable before invoking it, so single-shot is structural
  5. contain teardown-notification failures per observer

What remains impossible in any language: verifying that a registered inverse actually inverts.
Cordis type-checks the disposer and nothing more, and shipped one that deleted the wrong map entry
for months. A registry buys *invocation*, never *reversal*.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"

# The four symbols that would indicate a disposer/teardown registry exists.
REGISTRY_MARKERS = ("disposer", "AsyncExitStack", "weakref.finalize", "register_cleanup")


def _files_containing(needle: str) -> list[str]:
    """Return src/ files mentioning `needle`. Empty list means the concept is absent."""
    result = subprocess.run(
        ["grep", "-rl", "--", needle, str(SRC)],
        capture_output=True,
        text=True,
        check=False,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


class TestDisposerRegistryGap:
    """Gap witness. These PASS because the gap exists; they FAIL when it is closed."""

    @pytest.mark.parametrize("marker", REGISTRY_MARKERS)
    def test_no_disposer_registry_exists_yet(self, marker: str):
        found = _files_containing(marker)
        assert found == [], (
            f"'{marker}' now appears in {found}. A teardown registry may exist. "
            "If so, DELETE TestDisposerRegistryGap and un-xfail the invariant tests below -- "
            "they are the real conformance suite and they were written for exactly this moment."
        )

    def test_register_entrypoints_have_no_unregister_counterparts(self):
        """22 register* functions, 0 unregister* -- the asymmetry IS the finding."""
        registers = subprocess.run(
            ["grep", "-rhoE", r"def register[A-Za-z_]*", str(SRC)],
            capture_output=True, text=True, check=False,
        ).stdout.split()
        unregisters = subprocess.run(
            ["grep", "-rhoE", r"def (un|de)register[A-Za-z_]*", str(SRC)],
            capture_output=True, text=True, check=False,
        ).stdout.split()
        assert registers, "expected register* entry points to exist"
        assert not unregisters, (
            f"unregister counterparts appeared: {unregisters}. The teardown story changed; "
            "revisit this suite."
        )


@pytest.mark.xfail(
    strict=True,
    reason="No disposer registry exists yet. Encodes the contract; flip when one lands.",
)
class TestDisposalInvariants:
    """The five invariants a component-teardown mechanism must satisfy.

    Each maps to a defect measured in upstream Cordis at 4.0.0-rc.8 by execution, which is why
    they are stated as tests rather than prose -- every one of them is a real failure mode that
    a real framework shipped.
    """

    def test_inverse_registered_before_setup_runs(self):
        """(1) Registering after setup means an unload begun inside setup misses the effect."""
        raise NotImplementedError("no registry to exercise")

    def test_registration_rejected_while_unloading(self):
        """(2) Cordis ACCEPTED an effect created from inside a cleanup handler during UNLOADING;
        it escaped the unload snapshot, stayed tracked on a dead owner, and never ran."""
        raise NotImplementedError("no registry to exercise")

    def test_teardown_joins_inflight_cleanup(self):
        """(3) AXIOM 4. Cordis's fiber.dispose() RESOLVED BEFORE an in-flight cleanup settled --
        the supervisor is told the component unloaded while it is still releasing, and the
        replacement starts on top of a resource the predecessor still holds."""
        raise NotImplementedError("no registry to exercise")

    def test_disposer_is_single_shot_structurally(self):
        """(4) Pop the callable before invoking it; do not guard with a flag."""
        raise NotImplementedError("no registry to exercise")

    def test_teardown_notification_failures_contained_per_observer(self):
        """(5) A throwing observer STARVED its peers and left a zombie registry entry with no
        handle returned to the caller -- registered, never applied, impossible to dispose."""
        raise NotImplementedError("no registry to exercise")

    def test_effects_attached_while_pending_are_drained(self):
        """Bonus defect: Cordis never drained effects attached while a fiber was PENDING."""
        raise NotImplementedError("no registry to exercise")
