#!/usr/bin/env python3
"""Proposed command construction; never starts a driver or writes measurements."""
from pathlib import Path
DRIVER='/mnt/raid0/llm/worktrees/research-kvu12-run/artifacts/np_context_kvu_cpu_study_20261020/driver/kvu_cpu_matrix.py'
BINARY='/mnt/raid0/llm/kernels/production/cpu/llama-server'
CPUS='72-95,168-191'

def command(mode,arm,output,ledger=None):
    output=Path(output)
    if not output.is_absolute():raise ValueError('absolute output required')
    common=['/usr/bin/python3','-B',DRIVER,'--binary',BINARY,'--cpu-list',CPUS,'--threads','24','--port','18970','--out',str(output)]
    if mode=='control':
        if arm!='control':raise ValueError('control requires independent short control')
        return common+['--kv-modes','split','--nps','1','--lens','8k','--pmodes','independent','--waves','1','--npredict','16']
    if mode=='target' and arm=='anchor':
        return common+['--kv-modes','none','--anchor','--only','t8anchor','--waves','3','--npredict','256']
    if mode!='target' or arm not in ('unified','split'):raise ValueError('unknown mode or arm')
    if not ledger or not Path(ledger).is_absolute():raise ValueError('absolute pair ledger required')
    cmd=common+['--kv-modes',arm,'--nps','8','--lens','64k','--pmodes','depth','--waves','4','--npredict','256','--aba-key','np8L64k','--aba-ledger',str(ledger)]
    if arm=='unified':cmd+=['--pools','524288']
    return cmd
