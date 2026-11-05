Source-bound offline reconciliation packet; prepared only, comparator not executed.

Sealed runner: filler_run15.sh SHA256 21987e52ee02c609cd5a80f7b493b2d69fbaf367b4dd44bd9ff9fa3ec20c51b2.
Sealed job: df1edf33ebd95897311f2cb28653f0bc379184371f2575e388f437158ca90279.
Same-attempt native result: 7a8254c6b44c9eb04b51bb7ed7bcdeaaf8345f4d1164b3feb9365aae86655e91.

The actual source defect is FILLER_STOPFILE scope, not FILLER_ID. job.py complete(), line 391, immediately calls check_run_limits(); line 196 indexes os.environ['FILLER_STOPFILE']. runner line 227 exports this only within --inner. Outer is_complete(), line 208, runs a fresh bash child and suppresses its output. Outer line 293 exports END/CPUS/THREADS/NEEDGPU, but not STOPFILE or DEADLINE. Therefore absent inherited FILLER_STOPFILE, outer completion raises KeyError, returning nonzero; line 372 converts otherwise-zero job rc to rc75 partial-native-incomplete. Child exports never flow to the parent. No historical outer environment or checker stderr is retained here, so the exact historical exception remains inferred from a proven source defect. FILLER_ID is never referenced in job.py.

Native RESULT satisfies the visible values of the completion assertions on manual inspection; compare.py is an unexecuted, source-sealed comparator for those assertions only. It never executes/imports job.py, calls check_run_limits, opens models, runs inference or changes terminal files. Historical STOP/deadline checks cannot be recreated from today's environment.

Concrete prospective repair, requiring runner owner's source workflow: pass FILLER_STOPFILE="$STOPFILE", FILLER_ID="$ID", FILLER_DEADLINE="$((FILLER_END - 90))" to the outer completion subprocess when FILLER_END exists. Preserve pre-grant completion semantics explicitly, because is_complete is also called before a new END is set. Prefer splitting historical terminal-record verification from active-run STOP/deadline checks, rather than assigning a fabricated deadline. Capture completion checker stderr into an attempt-local diagnostic. New runner digest requires repinning future launchers. Do not modify the published single-use packet or replay this exposed request.

Disposition: keep existing inconclusive grant verdict; record native mechanics observations separately. Reconciliation can identify adapter failure without claiming historical outer environment or promotion acceptance.
