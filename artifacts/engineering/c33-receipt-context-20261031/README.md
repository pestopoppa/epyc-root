# C33 receipt context: retained source controls

The coordinator source change preserves validation refusal and operator authority. It adds one keyed-receipt context notice after an older unpresented notice was consumed. No signing/admission policy, operator checkbox, daemon configuration or receipt parser/status set changes.

The original task paragraph is retained byte-for-byte in ORIGINAL-TASK.md. Source base is ROOT `2a2421e5d63a6bd05377a9fb542790a36726897a`; the source implementation commit is cited in the separate handoff checkpoint. No live deployment is claimed.

## Retained execution

Do not use default pytest for this local qualification. After applying the reviewed source patch, execute under the approved existing R6 wrapper:

```
python3 -B /mnt/raid0/llm/tmp/refactor-01a16fc3/two_family_admitted_run.py /mnt/raid0/llm/tmp/c33-integration-unique01 /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B artifacts/engineering/c33-receipt-context-20261031/retained_runner.py --source-root "$PWD" --new-tests "$PWD/tests/test_c33_receipt_context.py" --output /mnt/raid0/llm/tmp/c33-integration-retained-unique01
```

Use fresh output names; existing paths refuse instead of being removed or reused. The new test module uses its own mkdir-only retained fixture and no pytest tmp_path dependency. The runner additionally disables pytest tmpdir/cache/autoload, supplies mkdir-only retained fixtures with no cleanup/current-symlink/lock lifecycle, uses memory capture/no bytecode, refuses Python filesystem delete/rmdir/rename and child-process escape events, and flushes guarded atexit callbacks before its receipt. It verifies the selected coordinator module was imported and records exact source/test hashes. It is a guard for these reviewed Python controls, not a kernel sandbox for arbitrary native extensions.

Independent integrated checkout controls: 19 passed; see integrated-controls.log and integrated-retained-receipt.json. Actual retained candidate:19 passed,57 fixture files retained,zero real forbidden attempts. Actual retained baseline:6 intended failures/13 passes,57 retained files,zero forbidden attempts. The15 behavioral test bodies and4 existing pure receipt/relay cases are unchanged; the new module now allocates mkdir-only retained fixture directories without requesting pytest tmp_path. The retained runner still supplies safe temporary fixtures for the4 existing cases. Other existing fixtures exercise atomic rename helpers and are not silently replaced to force a compliant pass. Raw green/red logs and retained inventories are in this directory; all fixture content is synthetic.

## Prior execution disclosure

The earlier default pytest invocations were not compliant with the standing no-delete/no-rename rule. The broad original-module run included explicit synthetic fixture unlink calls, bus provisioning used existing os.replace, and pytest managed shared numbered temp directories/current symlinks/cleanup locks. Some old fixtures are gone. Exact cleanup counts/attribution cannot be recovered without a pre-run inventory or syscall log. PRIOR-DELETION-DISCLOSURE.json records what is known and unknown. The retained runs correct the final execution path; they do not erase or re-label the earlier operations.
