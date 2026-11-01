# R22 predecessor retirement

The unqualified owned r2 READY predecessor was retired after checking its original manifest and row hashes, its absent full-result directory, and current managed grant, queue, registry and process state. Its exact manifest and row remain in `compute-flags/ready/withdrawn/`, and an exact-ID withdrawal marker records the reason. `RETIREMENT.json` records their hashes and the observation; `VERIFY.log` records the hash check.

The review-only predecessor guard also passed immediately after the transition. This observation does not prevent a future unmanaged writer; a successor must recheck retirement and shape custody under its own resource boundary. No original native result was altered, and no new qualifier receipt, grant, or GPU result is claimed. The existing keeper still needs the reviewed versioned-router transition before it can qualify the successor. [belief: cc]
