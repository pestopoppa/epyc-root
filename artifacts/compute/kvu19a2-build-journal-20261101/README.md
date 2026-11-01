# Prospective KVU build journal

This isolated component creates a new private JSONL receipt with exclusive creation, directory and file fsync, ordered command start/end records, and a terminal partial result when command or cleanup verification fails. Qualification and target modes are explicit. It does not execute commands, authenticate caller assertions, manage children, attest source/toolchain or make the build packet runnable. No build or inference was run. Same-UID directory authority, interrupted writes, journal recovery, process supervision, STOP, actual in-claim admission, ELF/linkage and native collector integration remain open. Do not use this journal alone as evidence of a successful build.

Offline checks: `python3 -B artifacts/compute/kvu19a2-build-journal-20261101/test_journal.py`.

A write or fsync failure now poisons the writer; later transitions cannot append or mark completion. Constructor failures close captured descriptors while retaining the incomplete exclusive file for inspection. Seven offline tests include injected partial writes and directory/file fsync failures. Poisoning does not provide crash recovery or authenticate records.
