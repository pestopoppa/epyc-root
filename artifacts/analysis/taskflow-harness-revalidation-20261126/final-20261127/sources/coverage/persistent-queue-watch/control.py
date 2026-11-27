"""Read-only live watcher control. This program never launches an approved callback."""
from copy import deepcopy
import fcntl
from pathlib import Path
import tempfile
from types import SimpleNamespace

import watch


def main():
    _, ctx = watch.load_base()
    bridge, engine, legacy, _, _, mechanical = ctx
    observed = {}
    with tempfile.TemporaryDirectory(dir=watch.HERE) as temp:
        folder = Path(temp)
        for queue, (root, seal, name, plan_sha, out, _) in watch.QUEUES.items():
            plan, expected_out = watch.qualified(queue)
            bridge.lease.verify_receipts(legacy, plan["lease"])
            assert expected_out == root / "runs" / out
            observed[queue] = watch.poll(queue, ctx, plan) is not None
            fixture = folder / f"{queue}.json"
            proof = {"approved_by": "main", "runner_seal_sha256": seal,
                     "plan": str(root / name), "plan_sha256": plan_sha}
            legacy.write(fixture, proof)
            cmd = watch.approval_command(queue, fixture, watch.digest(fixture))
            assert cmd[3] == str(root / "callback.py") and cmd[-1] == str(expected_out)
            legacy.write(fixture, dict(proof, plan_sha256="0" * 64))
            try:
                watch.approval_command(queue, fixture, watch.digest(fixture))
            except ValueError:
                pass
            else:
                raise AssertionError("wrong plan bytes admitted")
            changed = deepcopy(plan["lease"])
            changed["controller"]["start_ticks"] += 1
            try:
                bridge.lease.prove(engine, legacy, mechanical, changed, "gpu")
            except RuntimeError:
                pass
            else:
                raise AssertionError("stale owner birth admitted")
        fake = SimpleNamespace(LOCKS=folder)
        path = folder / "gpu-0.lock"
        path.touch()
        with path.open("rb") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with watch.locks_free(fake, [0]) as idle:
                assert not idle
        with watch.locks_free(fake, [0]) as idle:
            assert idle
    record = {"passed": True, "native_calls": 0, "model_callbacks_spawned": 0,
              "live_lease_and_exact_prior_receipts_tested": True, "current_ready_observation": observed,
              "wrong_approval_plan_and_owner_birth_rejected": True, "busy_slot_lock_rejected": True}
    legacy.write(watch.HERE / "CONTROL.json", record)
    print(watch.json.dumps(record))


if __name__ == "__main__":
    main()
