# KPF-26 code diagnostic ELF-closure correction

This is a separate corrected generation for the SAME existing off/on row IDs and
owner. The published `kpf26-code-requal-20261104` scratch is unchanged.
New scratch/specs: `/mnt/raid0/llm/tmp/kv-prefix-fork/kpf26-code-requal-v2-20261104/{off,on}-spec.json`.

The old retained-bin manifest covered26 of36 files and omitted the loaded
`libllama-server-impl.so`, `libllama-common.so.0`, and `libmtmd.so.0` families.
`closure-coverage.json` lists all10 omissions. The corrected manifest hashes all36
retained-bin files, while `LINKAGE-CLOSURE.json` pins the actual loader closure:
17 on-disk ELFs including7 own DSOs. System library paths/digests are recorded
separately from own-bin membership. The new pre-spawn verifier refuses uncovered
or missing bin files, changed content, unresolved/changed loader dependencies,
and project DSOs outside the manifested bin tree. The preexisting source pin and
own-ggml-tree guard remain. This does not invent source-to-binary build provenance.

Source/workload, off/on flags, same-ID lineage, isolated native smoke semantics,
ports and result split remain as in the earlier packet. The source-input snapshot
contains three copied cohort files, not a checkout; retained bin copies are
hardlinked and never modified. No existing READY manifest or source tree changed.
Only main may atomically republish these same IDs after checking current grant
state; preparation ran no server, inference, qualification or publication.

Validation: seven focused deterministic guard tests pass, covering actual closure
coverage, content mutation, path escape, external dependency mutation and failed
resolution. All three shell inputs pass bash syntax checks; Python compiles. The
new native closure/content validation passes against the actual retained inputs.

SUPERSEDED PREPARATION: same-ID replacement was refused because the original OFF ID had become terminal. The complete ELF/closure guard was carried forward into v3. Do not reuse a terminal row ID.

Archived row inputs only: no service imports or installs this packet. Published rows execute their pinned scratch launchers. This archive is not a deployment of fleet coordination code.
