# AutoKernel strategy ablation: costed design, no launch

Owner: S3-AKU-11 in [AutoKernel](../../handoffs/active/autokernel-loop.md).
Authority: [2026-11-02 decision, task S3-AKU-11](backlog-refactor-2026-11/decision-packages/decisions-batch2-4-20261102.json):
“Keep launch gated; deliver the costed design only.” This document completes the design deliverable;
it neither authorizes execution nor changes a validator, keep rule, or production artifact.
All costs and power figures below are planning assumptions, not measurements.

## Question and experimental unit

Does the production critic improve the probability of an accepted candidate per initiated proposal
enough to justify its actor cost on one fixed GPU screen target? Higher candidate yield and lower
cost per accepted candidate are better. The screen instrument is `bench`, category `CANDIDATE`;
it cannot establish serving benefit or promotion eligibility.

One unit is an initiated planner proposal, including formation refusal, critic rejection, author
failure, build failure and a completed measured result. An accepted candidate must pass the
unchanged build/oracle/paired-A-B tail and existing keep eligibility policy. It remains a candidate;
it never replaces the frozen champion during this experiment. Measuring only critic-approved
proposals would remove the intervention's refusals from the denominator and bias the comparison.

## Arms and fixed inputs

| Arm | Strategy intervention | Common tail |
| --- | --- | --- |
| A | Production planner and production critic, including its bounded revision policy | Existing author, build, correctness, screen and eligibility checks |
| B | Same planner; critic returns accept without feedback or revisions | Identical tail and hard safety/integrity refusals |
| C, optional | Catalog planner samples uniformly without replacement from mechanism tokens not previously measured on this target | Same accept-all critic and identical tail |

Recommend A/B only. C asks a different question and adds another arm's budget; launching it would
need a separate primary contrast and multiplicity plan. A historical do-not-repeat token is not
permission to retry a declined, prohibited or already falsified mechanism. C's eligible catalog
must be reviewed, target-scoped, versioned and emptied of such entries before sampling.

Freeze the champion source/build/library digests, target/model artifact, runtime recipe, workload,
actor model/backend/config, prompts, tool permissions, evidence snapshot, candidate allowlist,
random seeds, build recipe, oracle, screen protocol and keep policy before assignment. Both arms
start from the same champion for every proposal. Retain successful patches without compounding them.
Keep arm-local histories; do not leak rejects, patches or results across arms. The absence of critic
feedback in B is intentional. All other prompt inputs and actor budgets stay equal. A's bounded
revision work is part of the strategy and is charged, rather than silently granted free work.

Use 52 blocks of 10 proposal slots (five A, five B); uniformly shuffle each block with a
seed and PRNG implementation recorded in the pre-launch manifest. Commit the complete 520-slot
schedule before any actor call. Run the measured tails serially
under the resource broker. Do not treat shared-host parallelism as experimental replication.
Record each proposal's arm, block and sequence before the call begins. A process restart resumes
that assignment, rather than drawing another arm or erasing an inconvenient outcome.

## Primary endpoint, size and interpretation

Primary endpoint: accepted candidates / initiated proposals at a fixed **N=260 proposals per arm**.
The primary contrast is A minus B in percentage points, with its two-sided 95% interval.
Report every disposition count and the numerator/denominator alongside it. Preserve infra failures
in the intention-to-treat denominator and report their rate by arm; also provide a clearly secondary
infra-excluded sensitivity view. Clustered/repeated mechanism proposals can invalidate an independent
Bernoulli power calculation, so preregister the mechanism clusters and a block/cluster-aware analysis
before launch; N=260 is only a planning floor, not a guaranteed effective sample size.

The handoff's ~255 attempts/arm for a keep-rate halving is conditional: a halving is not an absolute
effect size. For illustration, rates 0.16 versus 0.08 give pooled p=0.12 and the approximate normal
sample size `2*(1.96+0.84)^2*p*(1-p)/(0.16-0.08)^2`, about 259 per arm. This motivates rounding
to 260, rather than claiming 255 is universally sufficient. No historical keep rate or independence
estimate has been established here. A near-zero yield makes this endpoint degenerate; a null then
cannot show the critic is dispensable. The unpooled approximation
`(1.96+0.84)^2*(0.16*0.84+0.08*0.92)/(0.16-0.08)^2` is about 255, which could explain
the historical estimate; its actual original assumptions remain unverified. Before launch, reuse
the S3-AKU-10 retrospective records to
select a target with credible nonzero yield and recost/repreregister N if its rate or clustering
makes this assumption unsuitable. Do not select a target using unblinded results of this ablation.

Secondary endpoints: actor decoded/input tokens and wall time per proposal, critic call/revision
counts, tail GPU-seconds per proposal, oracle/build failure rates, and total actor tokens and
GPU-seconds per accepted candidate. With zero accepted candidates the latter ratios are undefined,
not zero. Report costs per proposal as well. Best candidate effect is exploratory and subject to
selection; it cannot replace the primary yield contrast or justify deployment.

## Budget and checkpoints

The handoff estimates ~31 GPU-h per 255-proposal arm on the screen surface: an implied planning
mean of ~7.3 GPU-min per initiated proposal. At the same rate, N=260 costs approximately 31.6
GPU-h/arm, or 63.2 GPU-h for A/B; optional C adds ~31.6 GPU-h. These figures exclude actor-serving
GPU consumption, build CPU time, queue delay, profiling and reruns. They are not calendar ETAs.

A launch request must price those exclusions from existing logs, including critic/author revision
costs and per-arm tail admission rates. The equal 7.3-minute assumption may overprice a rejecting
critic arm and underprice an accept-all arm. State GPU-hours separately for tail and actor service,
CPU core-hours for builds, token counts per backend, and broker availability. No CPU launch is
proposed: the owning decision package describes that alternative as infeasible at this scope.

Save original records incrementally. Check after each balanced block for missing dispositions,
identity drift, claim leakage, resource overrun and unusable endpoints. Stop immediately on such
faults and retain all assignments. At 65, 130 and 195 proposals/arm, inspect blinded pooled yield
and projected cost only: stop for futility or budget exhaustion, never for an interim favorable
arm comparison. A zero-yield checkpoint prompts an explicitly inconclusive/futility disposition;
no synthetic successful samples and no automatic N extension. At N=260 report the fixed-sample
answer and stop. No early keep, promotion or sequential significance rule is introduced.

## Reviewable launch packet and durable outputs

A future operator launch request must contain the exact frozen input manifest, approved protocol
IDs, target suitability evidence, finalized independent/clustered power analysis, executable
assignment schedule, budget ceilings including excluded costs, resource ownership plan and an
explicit approval reference. Launch stays gated until that request is approved. This design does
not amend the measurement constitution or authorize a native transition-validator change.

The future producer must preserve assignments, every refusal/failure/result, actor telemetry,
validator provenance, candidate patches, exact tail evidence and cost units. Historical absent
critic pass-1 lineage remains unavailable; do not reconstruct it as observed data. Before adding
that measurement-producing process, register its source in the Vidya adapter source table and
owning substrate handoff, and capture native claim inputs on write. Existing validators and
`claim_tuple.grade()` retain authority; this design creates no new grading ladder.

The final report must distinguish the primary contrast, secondary costs and exploratory effects,
state the actual independent unit count and limitations, and label an early stop inconclusive.
No generated candidate becomes the champion as part of this experiment.
