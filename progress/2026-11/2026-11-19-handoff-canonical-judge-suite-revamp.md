# 2026-11-19 — handoff canonical-judge-suite-revamp

## 06:23Z — Qualify and publish the CJ-6a IFBench 27B diagnostic row

CJ-6a: published `codex-ifbench-cj6a-27b-v4-20261104` after four-CPU native smoke PASS on 140–143, rc=0 (2026-11-19T06:23:24Z). Restored IFBench detached source at `1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d`; model SHA-256 `a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348` verified before publication, with runtime file-identity check replacing grant-time model hashing. Fixed sudo smoke-environment forwarding and rebound current Python/libseccomp seals. Retained only the local runner patch and path/hash references in `docs/evidence/ifbench-cj6a-readiness-20261104/qualification-20261119.{json,patch}`; PASS receipt SHA-256 `c1bda149dac56f0091a9f48700870f173bedc9823db86cf5c574bc57f0b108e1`. The smoke uses one synthetic noncohort prompt; full IFBench capture/scoring and parent tick remain pending. [belief: cc]
