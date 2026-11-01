# Worktree common-directory gate regression

Source commit: `92385a1d1161b5709be446f74bd918f21bf7a076`.

Source pins (SHA-256):

- `scripts/system/worktree_gate.py`: `2af977ff13f540fafc4f2d1d584d05bae9cf62882705f8e02a75f0f880f163a3`
- `tests/test_worktree_gate.py`: `dd06365ebe6fe7c42a5d5f9d286ca8974d02ec80613d8ccbe8270035954b5922`

`native-regression.txt` records the complete native gate test file: 25 passed. It covers real external non-bare and bare common directories, main and unregistered paths, dirty and unlanded worktrees, keep markers, and existing removal safety checks. Run under the R6 admission and process-tree supervisor with CPUs 122–123, two thread limits and 900-second deadline. The reported peak is sampled RSS, not a hard-enforced peak. Tests use temporary Git repositories and do not prove the state of any live cleanup target.

Before this change, `_owning_repo` returned no owner for a valid common directory whose basename was not `.git`; the remove command consequently reported a registered linked worktree as unregistered. The new context is accepted only after Git resolves the same common-directory filesystem identity; existing registration and classification checks remain in force.
