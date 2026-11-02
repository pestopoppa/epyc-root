# M4 GPU A/A calibration entry

This is a prospective, descriptive A/A producer. It needs the separately reviewed
`scripts/benchmark/m4_gpu_speed` V2 source and CPU ownership watcher; it does not
register either. Both measured arms are independently executed V2 `BASELINE` cells
with M4 off. The labels A1/A2 exist only in the separate calibration plan; they do
not reclassify the incumbent as an M4 candidate. No output is a gate or floor.

`aa_enrollment.py` is deliberately empty and refuses execution. The owning session
must review and seal that module, the native V2 enrollment and both plans *before*
any measurement. The V2 trust-root source seals must include this entry, launcher,
reducer, enrollment and the canonical run15 engine in addition to the required V2
writer, reader, runner and watcher. Never substitute producer-supplied seals.

The calibration plan schema is `epyc.m4.gpu.aa.execution.v1` with
`intent=descriptive_only`, `native_plan_sha256`, absolute `result_path`, `row`
(`id`, `regions=mi210_0,184-191`, `stopfile`, `min_window_s`, `port`) and ordered
`cells`. Each cell has unique `id` and `native_cell`, `arm` A1 or A2, integer
`pair`, and the fully bound `sweep` settings enforced by `validate_plans`.
Each pair is adjacent, contains one A1 and one A2, and must have the same V2
identity, grant, exact process argv, environment and sweep parameters; native
watch paths differ. Each native cell is BASELINE, points to a distinct watcher
and has the exact same row grant. The independently sealed V2 plan supplies
model/prompt/binary/ggml content, process arguments and environment, own-device
KFD path/VRAM limit, expected request count and source commit. Resolve actual
recipes, resource envelope, model hashes, request shape and source closure before
reviewed enrollment; sample fixture values are not authorized inputs.

After the existing rowflow's qualified publication and a coordinated grant,
`launch_gpu_aa.py` hands off to run15 with exclusive GPU + physical q3 claim.
Each run is contained through the shared watcher and the strict V2 reader must
validate its completed guardian receipt before reduction. Failure, grant change,
STOP/HOLD or incomplete output never produce a successful result. The completion
predicate independently replays the native captures and recomputes each reported
pair. No existing capture is overwritten. The launcher does not publish a row,
write a grant, or start any job while enrollment remains disabled.

Tests use model-free fakes for the outer orchestration boundary; they do not
qualify a real GPU launcher, grant, model load, measurement, or planning canary.
