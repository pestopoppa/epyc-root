#!/bin/bash
# v13 (Pass 5 item 6, operator 2026-11-07): v12 + REAP-* lines logged ONCE per (dir, verdict) in live passes (they were 95 % of the log:
#   ~422k lines 11-05..11-07); state ws58-keeper-state/reap/logged.json, 7-day TTL, REAP_LOG_DEDUP=0 restores v12 logging;
#   dry-run/backfill output and the PASS/IDLE summaries are never deduplicated. Nothing else differs from v12.
# ws58-calendar-keeper v11 (ws58 2026-11-01 evening; operator: "compute keeps idling because of scheduling races, and that
# has to stop"). Every 120 s: (5) bin/rowflow/rowflow.py allocate - the ONE allocator: one snapshot of region-lock + open
# grants + live dry runs per tick, dry runs and grants assigned together (starved lane, rank, grantable before dry run,
# never the same region twice), grants WRITTEN by the allocator, dry runs spawned detached; self-healing invariants
# (HEAL stale-grant / HEAL conflict / CONFLICT / IDLE-WHY / UNDERUSED / IDLE-VIOLATION / ALERT on the 3rd repeat); and
# (6) REAP-AFTER-FILING (since 2026-11-03 only via --reap-now, run by the disk janitor; never in the tick). REMOVED vs v10: (1) quarter-queue carry-over, (2) FILLERS row lookup,
# (3) quarter/GPU grant-writer succession (the writers are retired: grant-ws58-quarters-<day>.sh, grant-gpu-<MMDD>-v<n>.sh),
# (4) the idle alarm (IDLE-WHY names the reason every tick instead), arm-time region resolution and dryrun-pick.
# History: v10 rowflow (arm-tick + one dry run per lane per tick); v9 qualification-slot starvation fix; v8 keeper-owned
# qualification; v7b-d succession rewriter; v5 reap-after-filing; v2 READY auto-arm; v1 2026-10-28.
# Usage: ws58-calendar-keeper-v13.sh [--dry-run | --reap-dry-run | --backfill-report]   (all three: one pass, change nothing;
#        --dry-run = the allocation step only)
#        ws58-calendar-keeper-v13.sh --reap-now   ONE live step-6 pass (legacy groups included), no allocation, then exit;
#        scripts/coordination/churn/disk_janitor.sh runs it every 30 min. Step 6 is NOT run by the loop (operator 2026-11-03).
set -u
F=/mnt/raid0/llm/tmp/compute-flags/
G=/mnt/raid0/llm/tmp/compute-flags/grants/
S=/mnt/raid0/llm/tmp/compute-flags/ws58-keeper-state/
STOP_AT=$(date -u -d '2036-01-01T00:00:00Z' +%s)  # v7d: no expiry; the calendar must never lapse (10-31 06:00Z outage)
DRY=0; REAPONLY=""; REAP_LEGACY=${REAP_LEGACY:-0}
case "${1:-}" in
  --dry-run) DRY=1;;
  --reap-dry-run) DRY=1; REAPONLY=reap;;          # read-only: ONLY step 6 against the live tree, prints one line per decision
  --backfill-report) DRY=1; REAPONLY=reap; REAP_LEGACY=1;;   # step 6 + legacy dirs (manifests without scratch_root/keep) + unmanifested dirs, classified
  --reap-now) REAPONLY=reap; REAP_LEGACY=1;;   # ws58 2026-11-02 (operator: four disk fixes): ONE live reaper pass, no allocation, then exit
esac
mkdir -p /mnt/raid0/llm/tmp/compute-flags/ws58-keeper-state

log() {
  local line; line="$(date -u +%FT%TZ) $*"
  if [ $DRY = 1 ]; then echo "[dry-run] $line"; else echo "$line" >> /mnt/raid0/llm/tmp/compute-flags/ws58-calendar-keeper.log; fi
}

# ---------- 5. ALLOCATE (v11) ----------
ROWFLOW=${WS58_ROWFLOW:-/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/rowflow.py}
KLOG=/mnt/raid0/llm/tmp/compute-flags/ws58-calendar-keeper.log
allocate_tick() {
  local l
  [ -f "$ROWFLOW" ] || { log "ROWFLOW: $ROWFLOW missing"; return 0; }
  if [ $DRY = 1 ]; then
    python3 -I "$ROWFLOW" --flags "$F" list 2>&1 | while IFS= read -r l; do log "ROW $l"; done
    python3 -I "$ROWFLOW" --flags "$F" allocate --plan 2>&1 | while IFS= read -r l; do log "$l"; done
    return 0
  fi
  python3 -I "$ROWFLOW" --flags "$F" allocate --log "$KLOG" 2>&1 | while IFS= read -r l; do [ -n "$l" ] && log "$l"; done
}

# ---------- 6. REAP-AFTER-FILING (2026-10-28, operator-approved; design: disk-audit-20261028/LOGS-AND-REAP-DESIGN.md) ----------
# A manifest declares scratch_root + keep globs. When ALL manifests naming that root are complete and have filing-done/<id>.FILED (the owner
# touching <scratch_root>/FILED cannot bypass this gate) the keeper (a) VAULTS the keep files into /mnt/raid0/llm/archive/scratch-vault/ (tar.gz + sha256 +
# index.json, verified), (b) REAP_DAYS (1) after all filing receipts deletes everything NOT in the keep set via guarded_rm.sh into a dedicated
# trash (/mnt/raid0/llm/.trash-reap) and trash-sweep.sh --older-than REAP_TRASH_DAYS (1) frees the bytes for real.
# Keep files stay IN PLACE (handoff citations stay valid); the vault is the durable copy. Guards (any one blocks deletion, never the vault):
# live process names/maps/cwd's the root; another non-complete grant/ready/armed manifest names it; KEEP marker; active handoff names the
# root itself (file-level citations are protected in place); a non-terminal FILLERS row names it. One log line per decision.
# INPUT RULE (operator 2026-11-03, session review 3.1; 2026-11-02 the reaper deleted a packet's inputs/ and helper/*.json and the
# job died 9 s after its grant): the reaper never deletes a file the job did not write. A file (or empty dir) whose mtime is
# before the group's first recorded job start (`started=` in grants/<id>.ended, written when the granted job starts; the
# manifest's published_at only when no start is recorded) is INPUT: kept in place, not vaulted, whatever the keep globs say.
# keep globs (and the manifest's result_path) only ADD protection; an empty keep = inputs + result. No recorded start and no
# published_at => every file is input and nothing is deleted (REAP-INPUT-ONLY names the fix).
# REAP_LEGACY=1 also synthesises groups for old manifests (root=tmp/<first dir of launcher>, keep=small files <=4 MiB + evidence names).
# IDLE RULE (operator 2026-10-28; REAP_IDLE_DAYS 7 -> 1 on 2026-11-02): a tmp dir no manifest names, idle >= REAP_IDLE_DAYS (newest mtime of anything inside), with no
# guard hit, has its small files (<=10 MiB *.json/md/txt/tsv/csv/yaml/yml/log + receipts/verdicts) vaulted with a sha256 index, then the
# rest deleted. Those small files stay in place. KEEP-marked dirs are NEVER reaped automatically; a dir holding a .git only when EVERY
# .git under it is a full clone or a registered, unlocked worktree that is clean (no change, no untracked file, no stash) and whose
# `git cherry origin/main` is empty (git_reapable; operator 2026-11-02); any git error keeps it. All other guards still apply.
# REAL FREE: guarded_rm.sh moves into /mnt/raid0/llm/.trash-reap (audit + manifest), then this pass deletes exactly the trash entries
# guarded_rm reported (trash-sweep.sh refuses --older-than 0); trash-sweep --older-than 1 on that trash is the backstop.
# Caps per pass: REAP_MAX_GIB (50) and REAP_MAX_DIRS (200); every decision logged. Any guard error => that item is skipped (SKIP-ERR).
# Hook exception: operator 2026-10-28: keeper v5 reap-after-filing (pinned path+sha256 in destructive_scratch_scan.py; see
# disk-audit-20261028/destructive-scratch-keeper-v5.patch).
REAP_DAYS=${REAP_DAYS:-1}
REAP_MAX_GIB=${REAP_MAX_GIB:-50}; REAP_MAX_DIRS=${REAP_MAX_DIRS:-200}; REAP_IDLE=${REAP_IDLE:-1}; REAP_IDLE_DAYS=${REAP_IDLE_DAYS:-1}
# SCRATCH LEASE (operator-directed scratch-leak structural fix 2026-11-04, Phase 1): a KEEP marker with an EXPIRED lease
# (scripts/system/scratch_lease.py; leases in tmp/.scratch-leases/) no longer blocks; a marker WITHOUT a lease keeps the old
# never-auto behaviour; lease module unloadable => every marker blocks (fail closed).
# REAP_WORKTREES=1 (default 0 = OFF) extends the idle rule to /mnt/raid0/llm/worktrees/* linked worktrees, acted on ONLY through
# scripts/system/worktree_gate.py: its `check` must say REMOVABLE (landed + clean + unreferenced + idle), removal is its own
# `remove` (git worktree remove, never --force, never prune).
REAP_WORKTREES=${REAP_WORKTREES:-0}
reap_filed() {   # called only by --reap-now / --reap-dry-run / --backfill-report (never by the loop); the janitor owns the cadence
  local mode=live ln
  if [ $DRY = 1 ]; then mode=dry; else
    touch "${S}reap-last"; mkdir -p "${S}reap"   # disk_janitor.sh reads this stamp so a manual --reap-now and its own pass never double up
  fi
  REAP_MODE=$mode REAP_LEGACY=$REAP_LEGACY REAP_DAYS=$REAP_DAYS REAP_MAX_GIB=$REAP_MAX_GIB REAP_MAX_DIRS=$REAP_MAX_DIRS REAP_IDLE=$REAP_IDLE REAP_IDLE_DAYS=$REAP_IDLE_DAYS REAP_WORKTREES=$REAP_WORKTREES REAP_STATE="${S}reap/" REAP_REPORT="${REAP_REPORT:-0}" \
  python3 -I - <<'PY' | while IFS= read -r ln; do log "$ln"; done
import os, sys, re, json, glob, time, hashlib, tarfile, subprocess, fnmatch, shutil, datetime as dt
E = os.environ; MODE = E['REAP_MODE']; LEGACY = E['REAP_LEGACY'] == '1'; DAYS = float(E['REAP_DAYS'])
ST = E['REAP_STATE']; REPORT = E['REAP_REPORT'] == '1'
MAXB = float(E['REAP_MAX_GIB']) * 2**30; MAXDIRS = int(E['REAP_MAX_DIRS'])
IDLE = E.get('REAP_IDLE', '1') == '1'; IDLE_DAYS = float(E.get('REAP_IDLE_DAYS', '1'))
IDLE_MAX = 10 << 20; IDLE_EXT = ('.json', '.md', '.txt', '.tsv', '.csv', '.yaml', '.yml', '.log', '.sh', '.py', '.patch', '.diff', '.jinja', '.toml', '.ini', '.cfg', '.c', '.cc', '.cpp', '.h', '.hpp', '.rs', '.go', '.js', '.ts', '.cmake', 'makefile', 'dockerfile')
RECENT_S = 3600   # any write inside a root within the last hour blocks deletion (proxy for processes /proc cannot show us)
budget = dict(b=0, n=0)   # bytes and dirs reaped (or would-be reaped) this pass
F = '/mnt/raid0/llm/tmp/compute-flags/'; G = F + 'grants/'; R = F + 'ready/'; TMP = '/mnt/raid0/llm/tmp/'
VAULT = '/mnt/raid0/llm/archive/scratch-vault/'; TRASH = '/mnt/raid0/llm/.trash-reap'
GRM = '/workspace/scripts/safety/guarded_rm.sh'
VMAX = 2048 << 20; FMAX = 512 << 20; SMALL = 4 << 20
MARKERS = ('.epyc-keep', '.epyc-load-bearing', 'KEEP', 'LOAD-BEARING')
PROTECT = {'compute-flags', 'disk-audit-20261028', 'ws58-loop-audit'}
EVID = re.compile(r'(VERDICT|receipt|attest|RESULT|SUMMARY|MANIFEST|\.sha256$|ENDED|COMPLETE|FILED)', re.I)
now = time.time()
DEDUP = E.get('REAP_LOG_DEDUP', '1') == '1' and MODE == 'live'
ALWAYS = ('PASS-SUMMARY', 'IDLE-SUMMARY', 'SWEPT')   # carry changing numbers; a handful of lines per pass
LOGGED_P = ST + 'logged.json'
try: LOGGED = {k: v for k, v in json.load(open(LOGGED_P)).items() if now - float(v) < 7 * 86400}
except Exception: LOGGED = {}
def _save_logged():
    try:
        tmp = LOGGED_P + '.tmp%d' % os.getpid(); json.dump(LOGGED, open(tmp, 'w')); os.replace(tmp, LOGGED_P)
    except OSError: pass
import atexit; atexit.register(_save_logged)
def out(tag, who, msg):
    if DEDUP and tag not in ALWAYS:
        k = '%s|%s' % (who, tag)
        if k in LOGGED: return
        LOGGED[k] = now
    print('REAP-%s %s: %s' % (tag, who, msg), flush=True)
def gib(b): return '%.2fGiB' % (b / 2**30)
def du(p):
    t = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            try: t += os.lstat(os.path.join(dp, f)).st_size
            except OSError: pass
    return t
def valid_root(sr):
    if not isinstance(sr, str) or not os.path.isabs(sr): return 'scratch_root missing'
    n = os.path.normpath(sr)
    if not n.startswith(TMP) or n.count('/') < 5: return 'scratch_root not under tmp/'
    if n.split('/')[5] in PROTECT: return 'scratch_root protected'
    return None
def valid_keep(k):   # an empty list is valid: keep = inputs + result (operator 2026-11-03)
    return isinstance(k, list) and all(isinstance(g, str) and g and not g.startswith('/') and '..' not in g for g in k)
# ---- manifests (ready/, armed/, refused/) ----
mans = {}
for d in (R, R + 'armed/', R + 'refused/'):
    for p in glob.glob(d + '*.json'):
        try: m = json.load(open(p))
        except Exception: continue
        if isinstance(m, dict) and m.get('id'): mans[m['id']] = (m, p)
groups = {}   # root -> dict(ids, keep, src)
for rid, (m, p) in mans.items():
    sr = m.get('scratch_root'); kp = m.get('keep'); bad = valid_root(sr) if sr else 'no scratch_root'
    if sr and not bad and valid_keep(kp):
        g = groups.setdefault(os.path.normpath(sr), dict(ids=set(), keep=[], src='declared'))
        g['ids'].add(rid); g['keep'] += [x for x in kp if x not in g['keep']]
        rp = m.get('result_path')   # the result is always protected (keep only adds to it)
        if isinstance(rp, str) and os.path.normpath(rp).startswith(os.path.normpath(sr) + '/'):
            rel = os.path.relpath(os.path.normpath(rp), os.path.normpath(sr))
            if '..' not in rel and rel not in g['keep']: g['keep'].append(rel)
    elif LEGACY:
        L = m.get('launcher'); lp = L.get('path') if isinstance(L, dict) else L
        if isinstance(lp, str) and lp.startswith(TMP):
            root = TMP + lp[len(TMP):].split('/')[0]
            if root.split('/')[-1] in PROTECT: continue
            g = groups.setdefault(root, dict(ids=set(), keep=['__LEGACY_SMALL__'], src='legacy'))
            g['ids'].add(rid)
            rp = m.get('result_path')
            if isinstance(rp, str) and os.path.normpath(rp).startswith(root + '/'):
                rel = os.path.relpath(os.path.normpath(rp), root)
                if '..' not in rel and rel not in g['keep']: g['keep'].append(rel)
    else:
        out('LEGACY', rid, 'manifest has no valid scratch_root/keep (%s); no auto-reap (run --backfill-report)' % (bad or 'keep invalid'))
# ---- /proc snapshot (one pass) ----
blob = []; unread = 0
for q in os.listdir('/proc'):
    if not q.isdigit(): continue
    try:
        blob.append(open('/proc/%s/cmdline' % q, 'rb').read().replace(b'\0', b' ').decode('utf8', 'replace'))
        try: blob.append(os.readlink('/proc/%s/cwd' % q))
        except OSError: unread += 1
        try:
            for l in open('/proc/%s/maps' % q):
                i = l.find('/')
                if i > 0 and TMP in l: blob.append(l[i:].strip())
        except OSError: pass
        try:
            for fd in os.listdir('/proc/%s/fd' % q):
                try:
                    t = os.readlink('/proc/%s/fd/%s' % (q, fd))
                    if t.startswith(TMP): blob.append(t)
                except OSError: pass
        except OSError: pass
    except OSError: pass
PB = '\n'.join(blob)
def proc_uses(root):
    return (root + '/') in PB or PB.endswith(root) or (root + ' ') in PB or (root + '\n') in PB
def read(p):
    try: return open(p, errors='replace').read()
    except OSError: return ''
def sread(p):   # strict: a guard input we cannot read raises => caller skips the item (never fail open)
    with open(p, errors='replace') as f: return f.read()
GUARD_ERR = None
try:
    HDIR = '/workspace/handoffs/active' if os.path.isdir('/workspace/handoffs/active') else '/mnt/raid0/llm/views/epyc-root-main/handoffs/active'
    HOFF = {p: sread(p) for p in glob.glob(HDIR + '/*.md')}
    if not HOFF: GUARD_ERR = 'no active handoffs readable'
    FILLTXT = sread(F + 'FILLERS.md')
except OSError as e:
    HOFF = {}; FILLTXT = ''; GUARD_ERR = 'guard input unreadable: %r' % e
if GUARD_ERR: out('GUARD-ERR', 'all', GUARD_ERR + '; every deletion this pass is skipped')
FILL = []
for l in FILLTXT.splitlines():
    c = l.split('|')
    if len(c) > 18: FILL.append((c[1].strip(), c[8].strip(), l))
def cited(root, ids):
    """-> (root_blockers, set of cited paths under root to protect in place)"""
    b, prot = [], set()
    pat = re.compile(re.escape(root) + r'(/[^\s`|;,\)\]\'"<>]*)?')
    for p, t in HOFF.items():
        for mm in pat.finditer(t):
            if mm.group(1) and mm.group(1) != '/':
                fp = (root + mm.group(1)).rstrip('.:')
                if os.path.exists(fp): prot.add(fp)
            else:
                b.append('handoff-live:' + os.path.basename(p)); break
    for rid, stt, l in FILL:
        if rid in ids or re.match(r'(COMPLETE|DONE|RETIRED)', stt): continue
        if re.search(re.escape(root) + r'(?![A-Za-z0-9_.-])', l): b.append('FILLERS-live:' + rid)
    return sorted(set(b)), prot
def other_refs(root, ids):
    b = []
    for gf in glob.glob(G + '*.grant'):
        gid = os.path.basename(gf)[:-6]
        if gid not in ids and root in sread(gf): b.append('open-grant:' + gid)
    for rid, (m, p) in mans.items():
        if rid in ids or os.path.exists(G + rid + '.complete'): continue
        if root in json.dumps(m): b.append('ready-manifest:' + rid)
    return sorted(set(b))
SYSDIR = E.get('SCRATCH_LEASE_SYSDIR', '/workspace/scripts/system')
try:
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location('scratch_lease', os.path.join(SYSDIR, 'scratch_lease.py'))
    LEASE = _ilu.module_from_spec(_sp); _sp.loader.exec_module(LEASE)
except Exception as _e:
    LEASE = None; out('LEASE-ERR', 'all', 'scratch_lease unloadable (%r); every KEEP marker blocks' % (_e,))
try:   # prompt input release + supersession (operator-directed 2026-11-04; scripts/system/scratch_release.py)
    _sp = _ilu.spec_from_file_location('scratch_release', os.path.join(SYSDIR, 'scratch_release.py'))
    SREL = _ilu.module_from_spec(_sp); _sp.loader.exec_module(SREL)
except Exception as _e:
    SREL = None; out('RELEASE-ERR', 'all', 'scratch_release unloadable (%r); inputs wait for the filing rules' % (_e,))
ALLIDS = set()   # filled before the group pass (mans is built above it)
def release_inputs(root, ids, tag):
    '''INPUTS are freed as soon as every row naming the root is released (ended any rc / dry run complete / superseded):
    verified re-derivable => freed directly (no trash, no idle wait); a DECLARED input that fails verification => guarded_rm;
    a derived one that fails => kept. Same guards as outputs (process, KEEP marker, other refs, handoff/FILLERS, guard error).'''
    if SREL is None or not ids: return
    why = [SREL.row_released(F.rstrip('/'), i, ALLIDS) for i in sorted(ids)]
    if not all(ok for ok, _ in why): return
    decls = []
    for i in sorted(ids):
        for d in SREL.row_inputs(mans[i][0]):
            if d['path'] not in [x['path'] for x in decls] and os.path.lexists(os.path.join(root, d['path'])): decls.append(d)
    if not decls: return
    bl, _p = cited(root, ids)
    blockers = keepmarkers(root) + bl + other_refs(root, ids) + (['process-uses-root'] if proc_uses(root) else []) + ([GUARD_ERR] if GUARD_ERR else [])
    rsn = ';'.join(sorted({w for _, w in why}))
    for d in decls:
        p = os.path.join(root, d['path']); itag = '%s/%s' % (tag, d['path'])
        if blockers: out('INPUT-BLOCKED', itag, ','.join(blockers)); continue
        ok, vwhy = SREL.verify_input(root, d); b = du(p)
        if not ok and d.get('derived'): out('INPUT-KEEP', itag, 'derived input not re-derivable (%s); filing rules apply' % vwhy); continue
        if not take_budget(itag, b): continue
        if MODE == 'dry': out('WOULD-FREE-INPUT' if ok else 'WOULD-TRASH-INPUT', itag, '%s, %s (%s)' % (gib(b), vwhy, rsn)); continue
        if not ok: really_delete(itag, root, [p], b, 'declared input not re-derivable: ' + vwhy); continue
        chk = subprocess.run(['bash', '-c', 'for q in /proc/[0-9]*; do tr "\\0" " " < $q/cmdline 2>/dev/null | grep -qF "$0/" && exit 3; ls -l $q/fd 2>/dev/null | grep -qF "$0/" && exit 3; done; exit 0', p]).returncode
        if chk != 0: out('INPUT-BLOCKED', itag, 'process appeared at free time'); continue
        try: SREL.free_input(root, d); out('FREED-INPUT', itag, '%s directly (%s; %s)' % (gib(b), vwhy, rsn))
        except Exception as e: out('FREE-FAIL', itag, repr(e)[:200])
def keepmarkers(root):
    '''markers that still BLOCK. Legacy (no lease) => every marker blocks; an EXPIRED lease releases them; any error blocks.'''
    f = [m for m in MARKERS if os.path.exists(os.path.join(root, m))]
    if os.path.exists(root + '.epyc-keep'): f.append('sibling .epyc-keep')
    if f and LEASE is not None:
        try:
            if not LEASE.marker_blocks(root, now): out('LEASE-EXPIRED', os.path.basename(root), 'KEEP marker released by expired lease'); return []
        except Exception: pass
    return f
# ---- keep set ----
def keepset(root, globs):
    ks = set()
    for pat in globs:
        if pat == '__LEGACY_SMALL__':
            for dp, dn, fn in os.walk(root):
                for f in fn:
                    fp = os.path.join(dp, f)
                    try: sz = os.lstat(fp).st_size
                    except OSError: continue
                    if sz <= SMALL or (EVID.search(f) and sz <= 64 << 20): ks.add(fp)
            continue
        for fp in glob.glob(os.path.join(root, pat), recursive=True): ks.add(fp)
    for m in ('FILED',) + MARKERS:
        if os.path.exists(os.path.join(root, m)): ks.add(os.path.join(root, m))
    return ks
def keepfiles(ks):
    fs = []
    for k in sorted(ks):
        if os.path.isdir(k) and not os.path.islink(k):
            for dp, dn, fn in os.walk(k): fs += [os.path.join(dp, f) for f in fn]
        elif os.path.exists(k) or os.path.islink(k): fs.append(k)
    return fs
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for ch in iter(lambda: f.read(1 << 20), b''): h.update(ch)
    return h.hexdigest()
def vault(name, root, files, filed_at):
    """returns (ok, msg). dry: only sizes."""
    tot = 0; big = []
    for f in files:
        try: sz = os.lstat(f).st_size
        except OSError: continue
        tot += sz
        if sz > FMAX: big.append(os.path.relpath(f, root))
    if big: return False, 'keep file(s) >512MiB (narrow the glob): %s' % big[:3]
    if tot > VMAX: return False, 'keep set %s > 2GiB vault cap' % gib(tot)
    idx = []
    for f in files:
        try:
            if os.path.isfile(f) and not os.path.islink(f): idx.append(dict(path=os.path.relpath(f, root), size=os.path.getsize(f), sha256=sha(f), mtime=int(os.path.getmtime(f))))
        except OSError: pass
    dig = hashlib.sha256(json.dumps(sorted((i['path'], i['sha256']) for i in idx)).encode()).hexdigest()
    rec = ST + name + '.vault.json'
    try:
        r = json.load(open(rec))
        if r.get('digest') == dig and os.path.exists(r['tar']) and sha(r['tar']) == r['tar_sha256']: return True, 'vault ok %s (%d files, %s) digest unchanged' % (r['tar'], len(idx), gib(tot))
    except Exception: r = None
    if r and os.path.exists(r.get('tar', '')) and sha(r['tar']) == r.get('tar_sha256') and any(now - os.lstat(f).st_mtime < RECENT_S for f in files if os.path.lexists(f)):
        return True, 'vault deferred: keep files written <1h ago (prior verified vault %s)' % r['tar']   # no new version per churn tick
    if MODE == 'dry': return True, 'WOULD-VAULT %d files %s -> %s<YYYY-MM>/%s.tar.gz' % (len(idx), gib(tot), VAULT, name)
    d = VAULT + dt.datetime.utcfromtimestamp(filed_at).strftime('%Y-%m') + '/'
    os.makedirs(d, exist_ok=True)
    vrx = re.compile('^' + re.escape(name) + r'\.v(\d+)\.tar\.gz$')   # max+1, not first free slot: pruning leaves holes at the low end
    ver = 1 + max([0] + [int(m.group(1)) for m in (vrx.match(f) for f in os.listdir(d)) if m])
    tar = '%s%s.v%d.tar.gz' % (d, name, ver)
    with tarfile.open(tar + '.part', 'w:gz') as t:
        for i in idx: t.add(os.path.join(root, i['path']), arcname=i['path'], recursive=False)
    ts = sha(tar + '.part')
    with tarfile.open(tar + '.part') as t:
        if len(t.getnames()) != len(idx): os.replace(tar + '.part', tar + '.bad'); return False, 'vault verify failed (member count)'
    os.replace(tar + '.part', tar)
    open(tar + '.sha256', 'w').write('%s  %s\n' % (ts, os.path.basename(tar)))
    json.dump(dict(root=root, filed_at=filed_at, files=idx, tar_sha256=ts), open(tar[:-7] + '.index.json', 'w'), indent=1)
    json.dump(dict(tar=tar, tar_sha256=ts, digest=dig, n=len(idx)), open(rec, 'w'))
    pr = prune_vault(d, name)
    return True, 'VAULTED %s (%d files, %s, sha256 %s)%s' % (tar, len(idx), gib(tot), ts[:16], pr)
def prune_vault(d, name, keep=2):
    """after a verified new tar: drop versions of `name` older than the newest `keep` (tar, .sha256, .index.json) via guarded_rm
    (TRASH_ROOT=reap trash; trash-sweep frees it); if guarded_rm fails, move the paths into TRASH."""
    rx = re.compile('^' + re.escape(name) + r'\.v(\d+)\.tar\.gz$'); vs = sorted(int(m.group(1)) for m in (rx.match(f) for f in os.listdir(d)) if m)
    old = []
    for n in vs[:-keep]:
        for suf in ('.tar.gz', '.tar.gz.sha256', '.index.json'):
            q = '%s%s.v%d%s' % (d, name, n, suf)
            if os.path.lexists(q): old.append(q)
    if not old: return ''
    os.makedirs(TRASH, exist_ok=True); moved = 0
    for i in range(0, len(old), 150):
        chunk = old[i:i + 150]
        r = subprocess.run(['bash', GRM] + chunk, env=dict(os.environ, TRASH_ROOT=TRASH), capture_output=True, text=True)
        if r.returncode == 0: moved += len(chunk); continue
        for q in chunk:
            if os.path.lexists(q):
                try: os.replace(q, '%s/%s.%d' % (TRASH, os.path.basename(q), int(now))); moved += 1
                except OSError: pass
    return '; pruned %d old version file(s) of %s (kept newest %d)' % (moved, name, keep)
def delplan(root, ks, prot):
    keepp = set(ks) | set(prot); anc = set()
    for k in keepp:
        x = os.path.dirname(k)
        while len(x) > len(root): anc.add(x); x = os.path.dirname(x)
    dels = []
    def walk(d):
        for e in sorted(os.scandir(d), key=lambda e: e.path):
            p = e.path
            if p in keepp: continue
            if e.is_dir(follow_symlinks=False):
                if any(os.path.exists(os.path.join(p, m)) for m in MARKERS): continue   # nested KEEP: whole subtree stays
                if p in anc: walk(p)
                else: dels.append(p)
            elif p not in anc: dels.append(p)
    walk(root); return dels
def _raise(e): raise e
def iso_epoch(s):
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%MZ'):
        try: return dt.datetime.strptime(str(s).strip(), fmt).replace(tzinfo=dt.timezone.utc).timestamp()
        except ValueError: pass
    return None
def first_start(ids):
    '''INPUT RULE cutoff -> (epoch|None, source). The earliest recorded job start over the group's ids (`started=` in
    grants/<id>.ended|.complete); when no id records one, the earliest manifest published_at; else (None, why).'''
    st, pub = [], []
    for rid in sorted(ids):
        for term in ('.ended', '.complete'):
            for l in read(G + rid + term).splitlines():
                e = iso_epoch(l[8:]) if l.startswith('started=') else None
                if e: st.append(e)
        e = iso_epoch((mans.get(rid) or ({}, ''))[0].get('published_at') or '')
        if e: pub.append(e)
    if st: return min(st), 'first job start'
    if pub: return min(pub), 'publish time'
    # 2026-11-07 (operator: automatic reclamation; 99 groups sat INPUT-ONLY forever): a row that recorded neither still
    # has a published manifest file and an end record on disk. The manifest's mtime is never later than the job start
    # (a republish rewrites it before the keeper re-dry-runs and re-grants), so it is a CONSERVATIVE cutoff: anything
    # older stays input; only files the job wrote after publication can be reclaimed.
    mt = [os.path.getmtime(mans[rid][1]) for rid in sorted(ids) if rid in mans and os.path.isfile(mans[rid][1])]
    if mt: return min(mt), 'manifest mtime (no started=/published_at)'
    return None, 'no started= in grants/<id>.ended, no published_at and no manifest file'
def input_set(root, cutoff):
    '''every file / symlink / empty dir under root whose mtime is before cutoff (+1 s: recorded times are whole seconds):
    written before the job started => INPUT, never deleted. Any walk error raises (the item is skipped).'''
    lim = cutoff + 1; ins = set()
    for dp, dn, fn in os.walk(root, onerror=_raise):
        for x in fn + dn:
            fp = os.path.join(dp, x); st = os.lstat(fp)
            if x in dn and not os.path.islink(fp) and os.listdir(fp): continue   # a non-empty dir: its entries decide
            if st.st_mtime < lim: ins.add(fp)
    return ins
def scan_tree(p):
    '''-> (newest mtime of the root and anything inside it, bytes, holds .git); any walk error raises'''
    newest = os.lstat(p).st_mtime; size = 0; git = False
    for dp, dn, fn in os.walk(p, onerror=_raise):
        if '.git' in dn or '.git' in fn: git = True
        for x in dn + fn:
            st = os.lstat(os.path.join(dp, x))
            if st.st_mtime > newest: newest = st.st_mtime
            if x in fn: size += st.st_size
    return newest, size, git
def git_reapable(p):
    '''ws58 2026-11-02 (operator): -> (ok, why). ok only if EVERY .git under p is a full clone or a registered, unlocked worktree
    rooted exactly there, clean (no change, no untracked file, no stash) and with `git cherry origin/main` empty. Any error => keep.'''
    n = 0
    for dp, dn, fn in os.walk(p, onerror=_raise):
        if '.git' not in dn and '.git' not in fn: continue
        if '.git' in dn: dn[:] = [x for x in dn if x != '.git']
        n += 1
        def q(*a): return subprocess.run(['git', '-c', 'safe.directory=*', '-C', dp] + list(a), capture_output=True, text=True, timeout=120)
        top = q('rev-parse', '--show-toplevel')
        if top.returncode or os.path.realpath(top.stdout.strip()) != os.path.realpath(dp): return False, 'git: %s is not a work-tree root' % dp
        if os.path.isfile(os.path.join(dp, '.git')):   # a worktree: its gitdir must point back here and not be locked
            gd = q('rev-parse', '--absolute-git-dir').stdout.strip()
            back = os.path.join(gd, 'gitdir')
            bp = open(back).read().strip() if gd and os.path.isfile(back) else ''
            if not bp or os.path.realpath(os.path.join(gd, bp)) != os.path.realpath(os.path.join(dp, '.git')):   # join keeps an absolute bp
                return False, 'git: %s is not a registered worktree' % dp
            if os.path.exists(os.path.join(gd, 'locked')): return False, 'git: worktree %s is locked' % dp
        st = q('status', '--porcelain')
        if st.returncode or st.stdout.strip(): return False, 'git: %s is not clean' % dp
        sl = q('stash', 'list')
        if sl.returncode or sl.stdout.strip(): return False, 'git: %s holds a stash' % dp
        ch = q('cherry', 'origin/main')
        if ch.returncode or ch.stdout.strip(): return False, 'git: %s has commits not in origin/main' % dp
    return n > 0, 'git: %d clean checkout(s), cherry origin/main empty' % n
def recent(root):
    for dp, dn, fn in os.walk(root, onerror=_raise):
        for x in dn + fn:
            if now - os.lstat(os.path.join(dp, x)).st_mtime < RECENT_S: return True
    return False
def idle_keep(root):
    ks = set()
    for dp, dn, fn in os.walk(root, onerror=_raise):
        for f in fn:
            fp = os.path.join(dp, f); st = os.lstat(fp)
            if os.path.islink(fp) or st.st_size > IDLE_MAX: continue
            if f.lower().endswith(IDLE_EXT) or EVID.search(f): ks.add(fp)
    return ks
def take_budget(tag, b):
    if budget['n'] + 1 > MAXDIRS or budget['b'] + b > MAXB:
        out('DEFER', tag, 'per-pass cap (%d dirs / %s) reached; %s waits for the next pass' % (MAXDIRS, gib(MAXB), gib(b))); return False
    budget['n'] += 1; budget['b'] += b; return True
def really_delete(tag, root, dels, dbytes, note=''):
    # re-check right before delete (a process may have started since the snapshot)
    chk = subprocess.run(['bash', '-c', 'for q in /proc/[0-9]*; do tr "\\0" " " < $q/cmdline 2>/dev/null | grep -qF "$0/" && exit 3; ls -l $q/fd 2>/dev/null | grep -qF "$0/" && exit 3; done; exit 0', root]).returncode
    if chk != 0: out('BLOCKED', tag, 'process appeared at delete time'); return
    r = subprocess.run(['bash', GRM] + dels, env=dict(os.environ, TRASH_ROOT=TRASH), capture_output=True, text=True)
    moved = re.findall(r'^trashed: .* -> (' + re.escape(TRASH) + r'/[^/\n]+) \(', r.stdout, re.M)
    out('REAPED' if r.returncode == 0 else 'REAP-FAIL', tag, '%d entries %s moved=%d rc=%d %s%s' % (len(dels), gib(dbytes), len(moved), r.returncode, r.stdout.strip().splitlines()[-1][:120] if r.stdout.strip() else r.stderr.strip()[:120], ('; ' + note) if note else ''))
    freed = 0; bad = 0
    for dest in sorted(set(moved)):   # ONLY entries guarded_rm just reported, each a direct child of the reap trash
        if os.path.dirname(os.path.realpath(dest)) != os.path.realpath(TRASH) or not os.path.lexists(dest): continue
        try:
            if os.path.isdir(dest) and not os.path.islink(dest): shutil.rmtree(dest)
            else: os.unlink(dest)
            freed += 1
        except OSError as e: bad += 1; out('FREE-FAIL', tag, '%s %r (stays in trash; backstop sweep after 1d)' % (dest, e))
    out('FREED', tag, '%d trash entries deleted, %d failed, ~%s' % (freed, bad, gib(dbytes)))
# ---- group decisions ----
ALLIDS |= set(mans) | {os.path.basename(x)[:-6] for x in glob.glob(G + '*.ended')}
for root in sorted(groups):
  g = groups[root]; ids = g['ids']; name = os.path.basename(root); tag = '%s[%s]' % (name, g['src'])
  try:
    if not os.path.isdir(root): out('GONE', tag, 'scratch_root does not exist'); continue
    release_inputs(root, ids, tag)
    # Every associated run must have completed and have its own filing receipt.
    # A root FILED marker alone cannot assert that each result was filed.
    filed = []
    for rid in ids:
        c = G + rid + ".complete"
        if not os.path.isfile(c): c = G + rid + ".ended"  # ws58 2026-11-02 (operator: reclaim): an ended+FILED run is terminal too
        receipt = F + "filing-done/" + rid + ".FILED"
        if os.path.isfile(c) and not os.path.exists(G + rid + ".grant") and os.path.isfile(receipt):
            filed.append(max(os.path.getmtime(c), os.path.getmtime(receipt)))
    if not ids or len(filed) != len(ids):
        out("WAIT", tag, "not complete and filed (%d/%d ids)" % (len(filed), len(ids))); continue
    filed_at = max(filed)
    fm = os.path.join(root, "FILED")
    if os.path.exists(fm): filed_at = max(filed_at, os.path.getmtime(fm))
    cutoff, csrc = first_start(ids)
    if cutoff is None:
        out('INPUT-ONLY', tag, '%s, so every file counts as input and nothing is deleted; fix: bash /workspace/scripts/safety/guarded_rm.sh <the job-written paths under %s>' % (csrc, root)); continue
    ins = input_set(root, cutoff)
    inote = 'inputs kept=%d (mtime before %s %s)' % (len(ins), csrc, dt.datetime.fromtimestamp(cutoff, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    ks = keepset(root, g['keep']); blockers = []
    bl, prot = cited(root, ids); ks |= prot
    files = [f for f in keepfiles(ks) if f not in ins]   # inputs stay in place and are never deleted: nothing to vault
    vok, vmsg = vault(name, root, files, filed_at)
    out('VAULT' if vok else 'VAULT-REFUSED', tag, vmsg)
    age_d = (now - filed_at) / 86400
    dels = delplan(root, ks, prot | ins); dbytes = sum(du(x) if os.path.isdir(x) and not os.path.islink(x) else (os.lstat(x).st_size if os.path.lexists(x) else 0) for x in dels)
    if not vok: out('BLOCKED', tag, 'vault not verified; nothing deleted (%d entries, %s waiting)' % (len(dels), gib(dbytes))); continue
    if not dels: out('CLEAN', tag, 'nothing outside keep set and inputs; ' + inote); continue
    sup = SREL is not None and SREL.all_superseded(ids, ALLIDS)   # superseded + filed: no idle wait
    if age_d < DAYS and not sup: out('HOLD', tag, 'filed %.1fd ago, reap in %.1fh (%d entries, %s)' % (age_d, (DAYS - age_d) * 24, len(dels), gib(dbytes))); continue
    blockers += keepmarkers(root) + bl + other_refs(root, ids)
    if proc_uses(root): blockers.append('process-uses-root')
    if blockers: out('BLOCKED', tag, '%s (would free %s)' % (','.join(blockers), gib(dbytes))); continue
    if recent(root): out('BLOCKED', tag, 'write inside root within %ds' % RECENT_S); continue
    if GUARD_ERR: out('SKIP-ERR', tag, GUARD_ERR); continue
    if not take_budget(tag, dbytes): continue
    if MODE == 'dry': out('WOULD-REAP', tag, '%d entries, %s, filed %.1fd ago, keep=%d files, %s (unreadable procs=%d)' % (len(dels), gib(dbytes), age_d, len(files), inote, unread)); continue
    really_delete(tag, root, dels, dbytes, inote)
  except Exception as e:
    out('SKIP-ERR', tag, 'guard/plan error %r; item skipped' % (e,))
# ---- 7-DAY RULE: unmanifested tmp dirs idle >= IDLE_DAYS (live when REAP_IDLE=1; always shown by --backfill-report) ----
if IDLE or LEGACY:
    manifested = set(groups)
    for rid, (m, p) in mans.items():
        L = m.get('launcher')
        for v in (m.get('scratch_root'), L.get('path') if isinstance(L, dict) else L):
            if isinstance(v, str) and v.startswith(TMP): manifested.add(TMP + v[len(TMP):].split('/')[0])
    cnt = {}
    def tally(c, b): x = cnt.setdefault(c, [0, 0]); x[0] += 1; x[1] += b
    for d in sorted(os.scandir(TMP), key=lambda e: e.name):
        p = d.path; name = d.name; tag = name + '[idle]'
        try:
            if not d.is_dir(follow_symlinks=False) or name in PROTECT or name.startswith('.'): continue
            if p in manifested: continue
            if keepmarkers(p): tally('KEEP-MARKED(never auto)', du(p) if LEGACY else 0); out('KEEP', tag, 'KEEP marker; never auto-reaped'); continue
            newest, size, git = scan_tree(p)
            idle_d = (now - newest) / 86400
            if idle_d < IDLE_DAYS: tally('IDLE-WAIT(<%gd)' % IDLE_DAYS, size); out('IDLE-WAIT', tag, 'newest write %.1fd ago (%s)' % (idle_d, gib(size))); continue
            if git:
                gok, gwhy = git_reapable(p)
                if not gok: tally('BLOCKED-git', size); out('BLOCKED', tag, 'holds a .git not provably landed: %s (%s)' % (gwhy, gib(size))); continue
                out('GIT-CLEAN', tag, gwhy)
            if GUARD_ERR: tally('SKIP-ERR', size); out('SKIP-ERR', tag, GUARD_ERR); continue
            bl = []
            if proc_uses(p): bl.append('process-uses-root')
            bl += other_refs(p, set())
            pat = re.compile(re.escape(p) + r'(?![A-Za-z0-9_.-])')
            bl += ['handoff-live:' + os.path.basename(h) for h, t in HOFF.items() if pat.search(t)]
            bl += ['FILLERS-live:' + rid for rid, stt, l in FILL if not re.match(r'(COMPLETE|DONE|RETIRED)', stt) and pat.search(l)]
            if bl: tally('BLOCKED-referenced', size); out('BLOCKED', tag, '%s (idle %.0fd, %s)' % (','.join(sorted(set(bl))[:4]), idle_d, gib(size))); continue
            ks = idle_keep(p); files = sorted(ks)
            vok, vmsg = vault(name, p, files, newest)
            out('VAULT' if vok else 'VAULT-REFUSED', tag, vmsg)
            if not vok: tally('VAULT-REFUSED', size); continue
            dels = delplan(p, ks, set())
            dbytes = sum(du(x) if os.path.isdir(x) and not os.path.islink(x) else (os.lstat(x).st_size if os.path.lexists(x) else 0) for x in dels)
            if not dels: tally('CLEAN(vaulted only)', 0); out('CLEAN', tag, 'only vaulted small files remain'); continue
            if not take_budget(tag, dbytes): tally('DEFER(cap)', dbytes); continue
            if MODE == 'dry': tally('WOULD-REAP-IDLE', dbytes); out('WOULD-REAP-IDLE', tag, '%d entries, %s, idle %.0fd, vault=%d small files' % (len(dels), gib(dbytes), idle_d, len(files))); continue
            n2 = scan_tree(p)[0]
            if (now - n2) / 86400 < IDLE_DAYS: out('BLOCKED', tag, 'written to since scan'); continue
            tally('REAPED-IDLE', dbytes); really_delete(tag, p, dels, dbytes)
        except Exception as e:
            tally('SKIP-ERR', 0); out('SKIP-ERR', tag, 'guard/plan error %r; item skipped' % (e,))
    for c, (n, b) in sorted(cnt.items()): out('IDLE-SUMMARY', c, '%d dirs, %s' % (n, gib(b)))
# ---- WORKTREE IDLE RULE (REAP_WORKTREES=1 only; default OFF): worktree_gate REMOVABLE trees only, removed only by its `remove` ----
if E.get('REAP_WORKTREES', '0') == '1':
    WTROOT = E.get('REAP_WORKTREE_ROOT', '/mnt/raid0/llm/worktrees'); WG = os.path.join(SYSDIR, 'worktree_gate.py')
    for d in (sorted(os.scandir(WTROOT), key=lambda e: e.name) if os.path.isdir(WTROOT) else []):
        p = d.path; tag = d.name + '[worktree]'
        try:
            if not d.is_dir(follow_symlinks=False) or d.name in ('mains', 'pool') or d.name.startswith('.'): continue
            if not os.path.isfile(os.path.join(p, '.git')): continue   # linked worktrees only; nested dirs are never walked
            if keepmarkers(p): out('KEEP', tag, 'KEEP marker; never auto-reaped'); continue
            if GUARD_ERR: out('SKIP-ERR', tag, GUARD_ERR); continue
            ck = subprocess.run(['python3', WG, 'check', '--min-idle-days', str(IDLE_DAYS), p], capture_output=True, text=True, timeout=1800)
            verdict = (ck.stdout.strip().split('\t') + ['', ''])[1]
            if ck.returncode != 0 or verdict != 'REMOVABLE': out('WT-KEEP', tag, (ck.stdout.strip() or ck.stderr.strip())[:200]); continue
            if not take_budget(tag, 0): continue
            if MODE == 'dry': out('WOULD-REMOVE-WT', tag, ck.stdout.strip()[:200]); continue
            rm = subprocess.run(['python3', WG, 'remove', '--min-idle-days', str(IDLE_DAYS), p], capture_output=True, text=True, timeout=3600)
            out('REMOVED-WT' if rm.returncode == 0 else 'WT-REFUSED', tag, (rm.stdout.strip() or rm.stderr.strip())[:200])
        except Exception as e:
            out('SKIP-ERR', tag, 'worktree guard error %r; item skipped' % (e,))
out('PASS-SUMMARY', MODE, 'reaped-or-would %d dirs, %s (caps %d dirs / %s)' % (budget['n'], gib(budget['b']), MAXDIRS, gib(MAXB)))
if MODE == 'live' and os.path.isdir(TRASH):
    r = subprocess.run(['bash', '/workspace/scripts/safety/trash-sweep.sh', '--older-than', '1'], env=dict(os.environ, TRASH_ROOT=TRASH), capture_output=True, text=True)
    if r.stdout.strip(): out('SWEPT', 'trash-backstop', r.stdout.strip().splitlines()[-1][:160])
PY
}
# Operator 2026-11-03 (session review 3.1): the tick only allocates. Reaping runs from the disk janitor alone
# (scripts/coordination/churn/disk_janitor.sh -> --reap-now every 30 min); a ~100 s reap pass inside the tick blocked granting.
tick() { if [ -n "$REAPONLY" ]; then reap_filed; return 0; fi; allocate_tick; }

if [ $DRY = 1 ]; then tick; echo "[dry-run] one pass done; nothing changed"; exit 0; fi
if [ -n "$REAPONLY" ]; then reap_filed; echo "reap-now pass done"; exit 0; fi   # --reap-now (disk_janitor.sh): one live pass
log "keeper v12 start pid=$$ (no expiry; rowflow allocate)"; echo $$ > ${F}ws58-calendar-keeper.pid  # main-loop pid for ws58-keeper-watchdog.sh
while [ "$(date -u +%s)" -lt "$STOP_AT" ]; do
  tick || log "tick error rc=$?"
  # v12 (ws58 2026-11-02): wake at once when a run ends or a row becomes ready (short rows must not leave a quarter
  # idle until the next 2-min tick); 120 s stays the fallback.
  m0=$(stat -c %Y ${F}grants ${F}ready 2>/dev/null | sort -n | tail -1)
  for _ in $(seq 24); do sleep 5; [ "$(stat -c %Y ${F}grants ${F}ready 2>/dev/null | sort -n | tail -1)" != "$m0" ] && break; done
done
log "keeper past STOP_AT; exiting"
