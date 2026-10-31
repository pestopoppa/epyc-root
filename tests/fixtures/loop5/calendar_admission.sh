    lm_attempt_begin
    r=$($F/grant_ok.sh $id $gib --window-s $W --regions $regs); rc=$?
    lm_admission_result "$rc"
