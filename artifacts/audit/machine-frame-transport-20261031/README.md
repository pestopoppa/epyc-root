# Machine-page opt-in — source proof

ROOT source base: `657395e7842b66a36cb618de7f928f723322fd95`. Approved page/test patch SHA-256: `65fc282a0f950ca207fa30af783555fd08de603aacb0d76e28a6dc22189a9337`.
APP source `ec6f81769020d695b046895d654e36a39595ac81` was published and independently verified on remote main first. Its native transport/control proof is `artifacts/audit/machine-frame-transport-20261031/` in epyc-orchestrator.

Both actual machine-page callers now request `view=machine`: EventSource and fallback polling. The two new Node controls execute those functions plus `applySnapshot` and verify delivery of the native renderer inputs. `root-final-tests.stdout`: 15 passing controls including syntax and provenance; the bounded static scan covers the materialized machine page only. The view remains on the existing page and uses the existing data-plane routes; no registry, health fold or handoff row changes.

APP retains the whole canonical frame and removes only an exact duplicate alias with an iterative comparison. Its final native suite passes 143 controls. Its inherited native `make gates` ShellCheck failure and dashboard formatting debt match the pristine base and are not reported as green. The native producer still builds/serializes the full frame: no production build-cost reduction, live payload size, bandwidth gain, deployment or live adoption is claimed. Fixture sizes are source controls only.

Both source publications use independent Git administration and the normal canonical pre-commit wrappers/extras, private exact-tree PII proof and protected-main serialization. Parent owns the original completion checkbox. Source publication alone does not reload either service.

[no-belief: source transport/page wiring and deterministic regression controls; no live measurement or deployment]
