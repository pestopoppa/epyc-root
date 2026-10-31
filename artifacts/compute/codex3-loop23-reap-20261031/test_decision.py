import os, pathlib, tempfile, unittest
P = pathlib.Path(__file__).parent
s = (P/'candidate.sh').read_text()
group = s[s.index('for root in sorted(groups):', s.index('# ---- group decisions ----')):s.index('# ---- 7-DAY RULE:')]
class Decisions(unittest.TestCase):
 def setUp(self):
  self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.p = pathlib.Path(self.tmp.name); (self.p/'filing-done').mkdir(); (self.p/'grants').mkdir(); (self.p/'root').mkdir(); (self.p/'root'/'discard.bin').write_bytes(b'x')
  self.root = str(self.p/'root'); self.filed_at=1000000000
  self.mark('grants/a.complete'); self.mark('filing-done/a.FILED')
 def mark(self, name):
  p=self.p/name; p.touch(); os.utime(p,(self.filed_at,self.filed_at))
 def run_decision(self, offset, *, vault_ok=True, keep=False):
  events=[]
  def delete(*args): raise AssertionError('dry decision called really_delete')
  ns={'os':os, 'groups':{self.root:{'ids':{'a'},'keep':['keep.txt'],'src':'declared'}}, 'F':str(self.p)+'/', 'G':str(self.p/'grants')+'/', 'now':self.filed_at+offset, 'DAYS':1, 'MODE':'dry', 'GUARD_ERR':'', 'RECENT_S':3600, 'unread':0,
      'out':lambda tag,who,msg: events.append((tag,msg)), 'keepset':lambda *a:set(), 'cited':lambda *a:([],set()), 'keepfiles':lambda *a:[], 'vault':lambda *a:(vault_ok,'fixture'), 'delplan':lambda *a:[str(self.p/'root'/'discard.bin')], 'du':lambda *a:1, 'gib':lambda b:str(b), 'keepmarkers':lambda *a:['KEEP'] if keep else [], 'other_refs':lambda *a:[], 'proc_uses':lambda *a:False, 'recent':lambda *a:False, 'take_budget':lambda *a:True, 'really_delete':delete}
  exec(compile(group,'candidate-group','exec'),ns)
  self.assertNotIn('SKIP-ERR',[tag for tag,_ in events], events)
  return events
 def tags(self, events): return [tag for tag,_ in events]
 def test_actual_boundary(self):
  self.assertIn('HOLD',self.tags(self.run_decision(86399)))
  boundary=self.tags(self.run_decision(86400)); self.assertIn('WOULD-REAP',boundary); self.assertNotIn('HOLD',boundary)
 def test_root_marker_cannot_replace_receipt(self):
  (self.p/'filing-done/a.FILED').unlink(); self.mark('root/FILED')
  tags=self.tags(self.run_decision(86400)); self.assertEqual(tags,['WAIT'])
 def test_keep_and_vault_guard(self):
  self.assertIn('BLOCKED',self.tags(self.run_decision(86400,keep=True)))
  events=self.run_decision(86400,vault_ok=False); self.assertIn('VAULT-REFUSED',self.tags(events)); self.assertIn('BLOCKED',self.tags(events)); self.assertNotIn('WOULD-REAP',self.tags(events))
if __name__=='__main__': unittest.main(verbosity=2)
