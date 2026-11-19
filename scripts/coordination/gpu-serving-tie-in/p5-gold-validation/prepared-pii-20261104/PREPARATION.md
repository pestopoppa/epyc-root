# Prepared P5 candidate privacy controls

READY means prepared, not executed. Publish spec.json through a real row smoke to execute all seven existing staged-blob controls. Smoke and full modes run the identical job. Exactly four FILLER_CPUS and a 300-second window are required; the child has a maximum 270-second timeout.

pins.json seals the canonical hook, test file and candidate question input plus the producer sources. The original question input remains at its canonical tracked path (no duplicate copy). launch.sh verifies its embedded SOURCE.sha256 digest and then the manifest before job execution. job.py verifies canonical sources before/after pytest and parses actual JUnit counts plus exit status. complete.py independently checks seven distinct successful testcases, source identities, JUnit digest, and cleaned temporary repositories. Cache and bytecode generation are disabled.

Successful evidence is RESULT.json, junit.xml and pytest.log alongside pins.json, SOURCE.sha256 and launch.sh. Errors/incomplete execution write INCOMPLETE.json separately and cannot satisfy the explicit smoke predicate. Retain those generated evidence files here after the publisher run; no execution evidence exists at preparation time.
