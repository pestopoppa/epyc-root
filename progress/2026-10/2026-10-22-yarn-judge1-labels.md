# 2026-10-22 yarn-judge1-labels (3c4ca599 subagent): YARN-JUDGE-1 labels and cloud judge

Operator ruling 2026-10-22: "Why do you need me to manually label? Build the labels yourself. Don't overcomplicate this".
Coordinator 3c4ca599 correction: the labels must not come from a Claude model, because the judge is Claude. They are
produced by the cross-family `codex-luna-low` labeller plus deterministic rules. **The labels are agent-produced under
operator delegation, not human.**

- **Source data.** `judge_validation_kit.py context` resolves all 50 items to their dataset rows: hotpotqa by qid, simpleqa by prompt prefix. The logged prompt was cut at 200 characters, so the hotpotqa question itself was missing from the kit. The labeller gets the full question, the reference, the dataset answer and the supporting facts (hotpotqa) or source URLs (simpleqa). The judge gets the full question only.
- **Labels.** 19 by rule:
  - 6 no-answer (turn-limit or tool error);
  - 5 exact normalised match;
  - 1 yes/no;
  - 7 numeric mismatch.

  31 by `codex-luna-low` (gpt-5.6-luna, codex_exec, 31 calls), each prompt gated to contain the reference. The result is 10 correct and 40 incorrect, with none undecided. Borderline calls were j008, labelled 0 (unfinished meta-reasoning naming Atlético Madrid), and j037, labelled 1 ("~580 years" against "500+ years"). Files: `/mnt/raid0/llm/tmp/yarn-judge1-kit/labels_sheet_filled.csv` (sha256 `e3a4dfbe…`) and `labels.jsonl` with `.meta.json`.
- **Judge switched** to `--judge-backend cloud --cloud-judge sonnet-5-5-low` (research `cloud_judge.py`, the HS-PROF-1 `judge_beam_run.py` pattern). It uses the frozen registry copy of orch `fa25cfbd` via `ORCHESTRATOR_CLOUD_JUDGES_FILE` (sha256 `2c50caff…`). `helmet_judged_cell.py` gained the same backend. The kappa 95% CI was added to `agree`.
- **Commits.** Research `ddf985a51` and `e5173d638` on `yarn-native-gate-runner-20261022`, pushed. `yarn_gate_lib.sh` `YG_RESEARCH_SHA` is repinned to `e5173d638724bde7b2e395033097a20eda9efc88`, and the pinned worktree was fast-forwarded with no job running.
- **Job.** `yarn_judge1_job.sh` is now a post-step with no server, no GPU and no RAM booking. It runs the cloud judge, then agree, then pin, and refuses unless the research sha and the registry sha256 match.
- **Result (n=50).**
  - Accuracy 0.98 (Wilson 95% 0.895 to 0.996).
  - Cohen kappa 0.940 (95% CI 0.823 to 1.0 by analytic SE; 0.766 to 1.0 by bootstrap).
  - Confusion: 39 / 1 / 0 / 10.
  - Judge usage: 50 calls, $0.2156, envelope model `claude-sonnet-5-5`.
  - The only disagreement is j008.
  - The task text sets no threshold; acceptance is that agreement is reported with the pin.
  - Record: `/mnt/raid0/llm/tmp/yarn-judge1-out/run-20261022T125515Z/judge_pin.json`.

  This is agreement between two model families, not agreement with humans.
- **Open.** The parent YARN-JUDGE-1 stays unticked because "one judged HELMET cell scored end to end" is not done. No plan contains a judged HELMET category, so a cell has to be generated in a GPU window first.
- **Belief kernel.** The existing VB-YARN-AGG-1 write side covers the judge pin. The cloud pin carries every `yarn_gate_agg.JUDGE_PIN_KEYS` key, with `max_tokens` and `temperature` set to null.
