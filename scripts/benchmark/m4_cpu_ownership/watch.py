"""Private source-only watch: fresh cgroup contains every inherited descendant."""
import fcntl, hashlib, json, os, select, signal, time, uuid
from pathlib import Path
import owned
import m4_cgroup_guard

def run(cmd, grant, stop, hold, deadline, out, env=None):
    out=Path(out); grant=Path(grant); stop=Path(stop); hold=Path(hold)
    # Nonblocking single writer; never recover a stale output/cgroup by PID or name.
    lock=(out.parent/'watch-owner.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    registry=out/'server-pids.txt'; registry.touch(exist_ok=False)
    original=hashlib.sha256(grant.read_bytes()).digest()
    signals=[]; prior={}; proc=None; fd=None; cg=None; guardian=None; guardian_fd=None; done_fd=None; result={'status':'error'}
    e=dict(os.environ if env is None else env)
    def guard():
        if guardian_fd is not None and select.select([guardian_fd],[],[],0)[0]: return 'GUARDIAN_LOST'
        if signals: return 'SIGNAL_'+str(signals[0])
        if stop.exists(): return 'STOP'
        if list(hold.glob('HOLD_*')): return 'HOLD'
        try:
            if hashlib.sha256(grant.read_bytes()).digest()!=original: return 'GRANT_CHANGED'
        except OSError: return 'GRANT_MISSING'
        if time.time()>=deadline: return 'DEADLINE'
        return None
    def populated():
        fields=dict(line.split() for line in (cg/'cgroup.events').read_text().splitlines())
        return fields.get('populated')!='0'
    try:
        reason=guard()
        if reason: result.update(reason=reason,rc=124); return 124
        parent=Path(e['M4_DELEGATED_CGROUP_PARENT']).resolve(strict=True)
        parent.relative_to(Path('/sys/fs/cgroup').resolve(strict=True))
        if not (parent/'cgroup.controllers').is_file(): raise RuntimeError('cgroup v2 delegation required')
        cg=parent/('m4-private-'+uuid.uuid4().hex); cg.mkdir(mode=0o700)
        # No fallback if hierarchy is undelegated or cgroup.kill is unavailable.
        if not (cg/'cgroup.kill').is_file(): raise RuntimeError('cgroup.kill required')
        (out/'containment.json').write_text(json.dumps({'path':str(cg),'state':'owned'})+'\n')
        # Guardian stays outside the workload cgroup and watches both this
        # watcher and the original outer owner by birth-checked pidfds.
        guardian,guardian_fd,done_fd=m4_cgroup_guard.start(cg,int(e['M4_OUTER_OWNER_PID']),int(e['M4_OUTER_OWNER_BIRTH']))
        (out/'guardian.json').write_text(json.dumps({'pid':guardian.pid,'birth':m4_cgroup_guard.birth(guardian.pid)})+'\n')
        if guard(): raise RuntimeError('guardian or admission lost before spawn')
        e['M4_OWNED_CGROUP']=str(cg)
        e['M4_SERVER_PID_REGISTRY']=str(registry)
        e.pop('FILLER_PIDFILE',None)  # never feed numeric-only run13 fallback
        for sig in (signal.SIGTERM,signal.SIGINT):
            prior[sig]=signal.signal(sig,lambda number,frame:signals.append(number))
        proc,fd,stamp=owned.spawn(cmd,env=e,attach=cg)
        (out/'supervisor.json').write_text(json.dumps({'pid':proc.pid,'birth':stamp})+'\n')
        while not owned.exited(fd):
            reason=guard()
            if reason: break
            time.sleep(.1)
        reason=reason or guard()
        if reason: owned.stop(proc,fd,stamp)
        else: proc.wait(timeout=10)
        result.update(reason=reason or 'none',rc=proc.returncode)
        return 124 if reason else proc.returncode
    finally:
        try:
            if cg is not None:
                # Includes detached server sessions and descendants even after supervisor SIGKILL.
                # Kernel cgroup target has no PID-reuse window.
                (cg/'cgroup.kill').write_text('1')
                end=time.monotonic()+10
                while populated() and time.monotonic()<end: time.sleep(.05)
                if populated(): raise RuntimeError('cgroup remains populated; quarantined')
                result['containment_empty']=True
                cg.rmdir()
            if guardian is not None:
                # The guardian accepts disarm only after independently observing
                # that the cgroup is empty; EOF before this triggers a drain.
                if guardian_fd is not None and select.select([guardian_fd],[],[],0)[0]:
                    raise RuntimeError('guardian exited before verified drain')
                os.write(done_fd,b'D'); os.close(done_fd); done_fd=None
                if guardian.wait(timeout=10)!=0: raise RuntimeError('guardian rejected disarm')
            result['status']='closed'
        except BaseException as exc:
            result['cleanup_error']=repr(exc)
            raise  # a failed drain overrides a successful/STOP return
        finally:
            if done_fd is not None: os.close(done_fd)
            if guardian_fd is not None: os.close(guardian_fd)
            if guardian is not None and guardian.poll() is None:
                guardian.wait(timeout=10)
            if fd is not None: os.close(fd)
            for sig,handler in prior.items(): signal.signal(sig,handler)
            (out/'watch-result.json').write_text(json.dumps(result,sort_keys=True)+'\n')
            lock.close()
