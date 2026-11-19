# Astropy native scorer readiness

Row `vb-p5-astropy-scorer-native-20261118` stages the known-gold and no-op arms for model-free SWE-bench Verified case `astropy__astropy-12907`. Each arm requires named statuses for two FAIL_TO_PASS and thirteen PASS_TO_PASS tests. The row requests one CPU quarter with a 360-second estimate. The scorer stops after both arms, on a refusal or STOP, or at its allocation deadline or 270-second cap.

The retained software and spec mirror the prepared scratch packet. The build receipt, build log, grant, image ID and historical source are included in the source seal. `preflight-receipt.json` records the local image identity, pinned dataset, 73 original harness source digests, and official and offline evaluation-script bindings. `SHA256SUMS` seals the retained copy, including the final spec.

The smoke and official native results are pending. The 19 focused software controls passed during staging development. This preparation establishes source and input custody for one functional control case. [no-belief: readiness and source packet]
