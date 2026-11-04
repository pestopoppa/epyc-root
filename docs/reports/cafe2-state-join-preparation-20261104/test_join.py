import copy, hashlib, json, pathlib, tempfile, unittest
import join
class JoinControls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);(self.root/'a.bin').write_bytes(b'state');(self.root/'b.bin').write_bytes(b'state');self.sha=hashlib.sha256(b'state').hexdigest();self.digest='a'*64
  plan={'prompt_tokens':[5,6], 'boundary':7,'draft_tokens':list(range(8))}
  base={'schema':'cafe2.state-join.arm.v1','status':'COMPLETE','child_reaped':True,'cutoff':None,'source_sha256':self.digest,'binary_sha256':self.digest,'model_sha256':self.digest,'state_sha256':self.sha,'state_bytes':5,'effective_threads':4,'effective_batch_threads':4,'libraries':{'libllama.so':self.digest}}
  self.e=copy.deepcopy(base);self.e.update(arm='expert_census',state_file='a.bin',plan=dict(plan,arm='expert_census'),cells=[])
  self.t=copy.deepcopy(base);self.t.update(arm='timing_no_callback',state_file='b.bin',plan=dict(plan,arm='timing_no_callback'),cells=[])
  for k in range(55):
   rep,idx=divmod(k,11);rows=join.ORDER[rep][idx];c={'window':k,'rep':rep,'cell':idx,'rows':rows,'position_start':2,'state_equal':True,'state_sha256':self.sha}
   t=dict(c,ns=2000,callback_enabled=False);self.t['cells'].append(t)
   layers=[]
   for lid in range(40):
    x=[list(range(8)) for _ in range(rows)]
    layers.append({'id':lid,'window':k,'rep':rep,'cell':idx,'position_start':2,'rows':rows,'tensor':f'ffn_moe_topk-{lid}','shape':[8,rows,1,1],'strides_bytes':[4,1024,1024*rows,1024*rows],'experts':256,'topk':8,'expert_ids_by_token':x,'union_count':8,'union_ids':list(range(8))})
   c.update(coverage_complete=True,decode_rc=0,expected_layers=40,experts=256,topk=8,target_tokens=[7]+list(range(rows-1)),layers=layers);self.e['cells'].append(c)
 def tearDown(self):self.tmp.cleanup()
 def unknown(self):
  with self.assertRaises(join.Unknown):join.join(self.e,self.t,self.root)
 def test_valid(self):self.assertEqual(join.join(self.e,self.t,self.root)['status'],'MATCHED_PRODUCER_SNAPSHOT_DECLARATIONS')
 def test_missing_digest(self):del self.e['state_sha256'];self.unknown()
 def test_wrong_digest(self):self.t['state_sha256']='b'*64;self.unknown()
 def test_changed_snapshot(self):(self.root/'a.bin').write_bytes(b'STATE');self.unknown()
 def test_distinct_valid_states(self):
  (self.root/'b.bin').write_bytes(b'OTHER');h=hashlib.sha256(b'OTHER').hexdigest();self.t['state_sha256']=h
  for c in self.t['cells']:c['state_sha256']=h
  self.unknown()
 def test_boolean_rc(self):self.e['cells'][0]['decode_rc']=False;self.unknown()
 def test_boolean_layer_rep(self):self.e['cells'][0]['layers'][0]['rep']=False;self.unknown()
 def test_duplicate_layer(self):self.e['cells'][0]['layers'][1]['id']=0;self.unknown()
 def test_wrong_layer_identity(self):self.e['cells'][0]['layers'][0]['rep']=3;self.unknown()
 def test_bad_shape(self):self.e['cells'][0]['layers'][0]['shape'][1]=2;self.unknown()
 def test_missing_cell(self):self.t['cells'].pop();self.unknown()
 def test_nonfinite(self):self.t['cells'][0]['ns']=float('nan');self.unknown()
 def test_incomplete(self):self.e['child_reaped']=False;self.unknown()
 def test_json_duplicate(self):
  p=self.root/'d.json';p.write_text('{"x":1,"x":2}')
  with self.assertRaises(join.Unknown):join.read_json(p)
 def test_json_nan(self):
  p=self.root/'d.json';p.write_text('{"x":NaN}')
  with self.assertRaises(join.Unknown):join.read_json(p)
if __name__=='__main__':unittest.main()
