# KPF-60 GPU-X cell-selection preparation

`cell-selection.patch` extracts the existing chunk cell selection into a private
helper on experimental source `8952a0f693fb923918157eb25117641b74766230`.
Export still checks its existing eligibility before selection; this patch does
not enable hybrid export or implement the byte counter. The patch passed
`git diff --check` and a structural comparison of the extracted selection and
writer ordering. It has not been compiled or exercised against native data.

The independent `oracle.py` and `test_oracle.py` cover simple fixture row-size
arithmetic and overflow only. Four model-free tests passed; they do not validate
GGML types, physical cell selection, serialization metadata, or transfer.
The source-impact scan reported MEDIUM and LOW risks, with 25 large files and
one Python file skipped; those files remain outside its coverage. Native counter
implementation, CPU/HIP calibration and the target measurement remain open.
