# Profile-write precision audit checklist (UTM-V7)

Source rubric: the Honcho deriver prompt (`src/deriver/prompts.py:67-86 @607438d`, intake-2237#record).
Applies to every ProfileStore / `user_conclude` write. Advisory; part of the UTM-V3 criteria.
Implementation: `epyc-orchestrator` `src/user_modeling/write_audit.py` (`python -m src.user_modeling.write_audit [db]`,
read-only), tests `tests/unit/test_profile_admission.py`.

| # | Check | Decided by |
|---|---|---|
| 1 | One fact per entry (single sentence, no `§` delimiter or newline) | deterministic `one_fact_per_entry` |
| 2 | The fact is about the target user (no first person, no assistant-directed text) | deterministic `about_target_user` for the surface cases; human label for third-party subjects |
| 3 | No conversational mechanics ("the user asked", "in this conversation", thanks) | deterministic `no_conversational_mechanics` |
| 4 | No paraphrase duplicates (token Jaccard >= 0.7 against an earlier entry; later one flagged) | deterministic `no_paraphrase_duplicate` |
| 5 | References and dates resolved (no relative dates, no dangling pronoun or deictic opener) | deterministic `references_dates_resolved` |
| 6 | The fact is true and durable | human-labelled sample (`sample_for_labelling`, seeded) |

Related admission schema (HS-PROF-1): allowed kinds identity, attribute, relationship, instruction; six-month stability;
no behavioural or inferred entries; entry cap. Opt-in via `ProfileStore(admission=AdmissionPolicy())` or
`ORCHESTRATOR_PROFILE_ADMISSION=1`; off by default.
