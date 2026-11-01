# TD-17 CI run 41287440906 evidence

- Candidate: `027427c223d53a0b5a95541e5e2e49cd2cf0dc5d`
- Base: `da163c70cc347337f7d76d3ce5acc14fafc75411`
- Run: <https://github.com/pestopoppa/epyc-orchestrator/actions/runs/41287440906>
- Result: completed / success; Python 3.13.15; 70 tests passed, one pre-existing deprecation warning; pytest exit code 0.
- Raw run API response: `run.json`; job API response: `jobs.json`.
- Downloaded original ZIP: `artifact.zip`; GitHub artifact id `13075444395`; API SHA-256 `2674dbeaed1964424102692a73e7dbdb8df20baa04ebee737eedad1daadaa0e6`.
- `python3 -m zipfile -t` passed. ZIP SHA-256 matches the API artifact digest.
- Extracted original artifact files are under `artifact/`. The `source-files.sha256` manifest was checked against each path at the candidate commit with `git show <candidate>:<path> | sha256sum`; all entries matched.
- `pytest.exit-code` contains `0`; `pytest.stdout.txt` reports 70 collected and 70 passed; `junit.xml` is retained.
- Source paths in this run are exactly the five reviewed candidate paths; TU-owned files are absent from the candidate and its source hash manifest.
