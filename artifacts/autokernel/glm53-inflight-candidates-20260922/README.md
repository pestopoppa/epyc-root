# GLM-5.3 AutoKernel in-flight candidates (preserved 2026-09-22)

These are the uncommitted `git diff` of the 11 dirty AutoKernel worker worktrees. The worktrees were
under `/mnt/raid0/llm/tmp/aku-glm53-*` and `aku12a-glm53-five-loop-workers`, and were removed when
GLM-5.3-Flash was retired. Each is the candidate a lane was evaluating when its run stopped:
**unmeasured**, with no keep or refuse verdict. The file name is `<run>-<lane>`. Apply each onto the
base commit its run used (from the llama.cpp fork):

| Patch | Base |
|---|---|
| aku-glm53-continuous-20260911-v2-lane0, -v3-lane0, profile-proof-20260911-v9-lane0, five-loop-workers lane0 | c463f601b |
| aku-glm53-continuous-20260912-v4-lane0 | ec8b707c2 |
| aku-glm53-continuous-20260912-v7-lane0 | 0f3e8aa99 |
| aku-glm53-continuous-20260914-v9 / 20260915-v12 / -v13 / 20260916-v17 lane0 | 34a8b446f |
| aku-glm53-continuous-20260916-v18-lane0 | 614ff2ba0 |

Consumer: `handoffs/active/deepseek-v41-flash-evaluation.md` DS41-K2.
