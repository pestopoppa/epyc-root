# CTC-Q-D registration integration — reviewed source packet

MAIN accepted the private source and fixture packet on 2026-10-27. This is **prepared source only**: live registration, producer closure, server residency and owner activation are not established. The parent CTC-Q-D remains open. No model load, server launch, grant, calendar edit, production kernel change or inference run is part of this packet.

`packet/` is the accepted source, with its detailed native-validation and recovery instructions. `baseline/` contains byte-for-byte pre-change copies of the three WS58 scripts. Their SHA-256 values, in GPU, quarter, registrar order, are `38d58055ebcf0c4e1e5d77612e82153f41ee15220a556c18833d8c91bc64060e`, `b9a11c0a82f705ca2473940fec2258295d9e9977782ad79442c77e2535da7a20`, and `08253aca479f0a73cf30d05f3a1881a0c315a18d1e22d1342cbf7ca881163415`. Compare each baseline with the corresponding packet copy to reconstruct the exact change. The checker, validator and dry-run helper copies are pinned ROOT source, not a new grading rule.

`proof/PACKET.SHA256SUMS` is the accepted scratch manifest, digest `3d295c570d45b6780944058923535162ed56d35b624082027b7eb808f103c146`. Proof files retain their original scratch paths and are not portable test runners; they are evidence of the named execution, not instructions to run against live files. `run24.log` records actual Research semantic checks on synthetic records plus 13 registration and 12 writer tests; `run26.log` records four atomic grant publication controls; `run27.log` records 14 registration, five GPU startup adoption, and four publication controls. All ran in the allowed q0 claim, one-thread environment and 4 GiB address-space/RSS envelope. Research source for the native test was fresh origin `55a4672a5d9412a3ac3f192cfbdaaee0f26586e1`. Synthetic results do not establish server residency, native inference or all-producer coverage.

## Owner cutover and rollback

At a WS58-owned writer restart boundary, first verify these sources against the current scripts and resolve any drift; this packet names the 2026-10-27 quarter writer and GPU v13, not future successors. Make all ad-hoc row, queue, grant and HOLD producers cooperate with the proposed `.publication.lock`, and establish immutable native record/report custody. Otherwise the serialization and coverage claims do not hold. Validate each model recipe and experiment plan with the exact commands in [`packet/README.md`](packet/README.md); separately check live server ownership and residency. UNKNOWN peers stay visible; the report does not authenticate an owner or grade measurements.

With those prerequisites met and writers stopped by their owner at the boundary, take an owner-named, unique backup **before** replacing anything. For example, after setting `F` to the owner's compute-flags directory and `BACKUP` to a new owner-controlled directory:

```bash
mkdir "$BACKUP"
cp -a "$F/FILLERS.md" "$F/ws58-quarters-20261027.queue" "$F/ws58-quarters-20261027.queue.done" "$F/ws58-gpu.queue" "$F/ws58-gpu.queue.held" "$BACKUP/"
cp -a "$F/ws58_register_row.py" "$F/grant-ws58-quarters-20261027.sh" "$F/grant-gpu-1026-v13.sh" "$BACKUP/"
sha256sum "$BACKUP"/* > "$BACKUP/SHA256SUMS"
```

Also preserve any pre-existing catalog, registration receipt, registry, legacy snapshot and pending journal if present. Do not overwrite a prior backup. Inspect outstanding grants and the pending marker first. Owner installs the reviewed packet as a new version, initializes the legacy snapshot exactly once with `python3 packet/initialize_legacy.py "$F"`, then starts the two successor writers under the existing owner protocol. The owner must establish the producer/custody preconditions and validate exact candidate metadata and normal admission before activating; this document itself is not cutover authority. A same-ID grant, including a dangling symlink, refuses registration.

If a registration is interrupted, the journal blocks later publication. Use `python3 packet/recover_registration.py "$F"` to complete only when recorded generations and native references still validate, or `python3 packet/recover_registration.py "$F" --abort` to restore recorded before-images, verify them, and rotate the generation. A generation conflict or corrupt journal stays blocked for owner investigation. For a broader rollback, stop only the owner-captured successor processes at their boundary, confirm no conflicting active grants, verify backup hashes with `sha256sum -c "$BACKUP/SHA256SUMS"`, and restore the owner-reviewed original scripts from that backup; reconcile rows and queues explicitly before restarting the old writers. Do not blindly restore an old whole queue or remove an active grant. No process termination or rollback is performed by this packet.
