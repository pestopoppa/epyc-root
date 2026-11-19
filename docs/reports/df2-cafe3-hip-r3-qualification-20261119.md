# CAFE-3 HIP R3 build qualification

PASS full HIP gfx90a build qualification. Scheduled rc0, complete at 2026-11-19T21:52:50Z. The sealed packet's `driver.py check` exits 0 against RESULT.json. Configure/build/linkage supervisors each record command-exit rc0, child_rc0, no captured children and drain not-required.

Qualification binds the full experimental source to v10 base ffc1bac82eeca6f9099e1ccd9ba49703c460a115 and its tracked diff/generated sources. The validator checks adaptive/context/journal/poison markers in the local server implementation; HIP ON, backend DL OFF, ROCm Clang, gfx90a and enum-constexpr compatibility flag; UI build/fetch OFF; exact local numeric SONAME resolution and artifact hashes; defined CPU IQK and HIP registration exports and a compiled gfx90a image marker. The corrected SONAME validator accepts this full receipt.

This is build qualification only. No native model inference, live GPU residency, token identity, speed or P9 result was measured. Parent CAFE-3 remains open. The next task is repair of the parked CPU P9 input precondition; native HIP P9 must bind this receipt and the current residency producer/grader before publication.

Evidence references (existing files, no copied artifacts):

- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/RESULT.json` — SHA-256 `47b32712726fbb47f332185744f1fd7f70c984a1db2bfec03afbba6966cfff30`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/driver.py` — SHA-256 `da4b2d198a2cbb2e718434f4da87df4dcdfa085783b261fedadefb54fc196555`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/inputs.json` — SHA-256 `eec93bd906f7d35e4ab3af10c0eea84ec7c1ef45c6fd3f96b874d041408cd2db`.
- `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe3-full-hip-build-r3-20261119.ended` — SHA-256 `b63cda25a22bf6b4fdf0c10b4bd1224fc846622579ea52cebeae188b49e653e8`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/runs/build-vijlkg7u/configure.supervisor.json` — SHA-256 `9052e86eb960e486c17b04b412d321d2e4d690bfd9379b52876262053a1786ce`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/runs/build-vijlkg7u/build.supervisor.json` — SHA-256 `d0568ee92dc9db37074f900055a7cb161b735b25a7f83ceff28c4df77824d9d1`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/runs/build-vijlkg7u/linkage.supervisor.json` — SHA-256 `d31c84867fac57d188260daddae4059e519cb658065acdb091df4a8654e04236`.

Artifact identities from the validated receipt:

- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/runs/build-vijlkg7u/build/bin/llama-server` — SHA-256 `11202776bff8fa4b6a9c6319b8946547ed4f36b657d246c9790b2aa32a258101`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/runs/build-vijlkg7u/build/bin/libllama-server-impl.so` — SHA-256 `a1f0995de721367093f9c76e6f8ae41e1b0a50537ee485d9c5e4453c6d7acbdf`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/runs/build-vijlkg7u/build/bin/libggml-hip.so.0.16.0` — SHA-256 `33fc21d93488bbd15dd0a0b021d718b362e11d2d166ac14733759c3baa879fa8`.
- `/mnt/raid0/llm/tmp/df2/cafe3-hip-build-r3-20261119/runs/build-vijlkg7u/build/bin/libggml-cpu.so.0.16.0` — SHA-256 `b9cbaa522be53edb16ea04558f2bc5733d8123ca5ddd6139d3061986d9c4efdc`.

[no-belief: full HIP build qualification only]
