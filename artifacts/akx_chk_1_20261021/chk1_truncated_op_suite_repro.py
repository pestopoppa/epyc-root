import sys
sys.path.insert(0,'/workspace/repos/epyc-inference-research')
from scripts.kernel_rnd.autokernel.execution import t0_provider as t0
text=("Testing 1 devices\n\nBackend 1/1: CPU\n"
"  MUL_MAT(type_a=q8_0,type_b=f32): OK\n  MUL_MAT_ID(type_a=q8_0,type_b=f32): OK\n")  # killed between cases
run=t0.parse_backend_ops_console(text)
run.reconcile()
print("parsed without error; exercised:",run.exercised_ops(),"cases_by_op:",run.cases_by_op(),"failed:",run.failed_ops())
