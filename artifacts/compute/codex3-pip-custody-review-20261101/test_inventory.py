import hashlib,importlib.util,json,pathlib,tempfile,unittest
from unittest.mock import patch
D=pathlib.Path(__file__).resolve().parent;spec=importlib.util.spec_from_file_location('inv',D/'exposure_inventory.py');inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
class Inventory(unittest.TestCase):
 def run_scenario(self,kind):
  with tempfile.TemporaryDirectory() as td:
   t=pathlib.Path(td);root=t/'campaigns-fresh';root.mkdir();pages=[{'index':i,'image':str(i)+'.png'} for i in range(755)];plan=t/'plan.json';plan.write_text(json.dumps({'pages':pages,'prior_original_page_exposures_unknown':[]}));page=pages[40];prefix='region-'+hashlib.sha256(canon(page)).hexdigest()[:24]+'-000001.start.json';outer=root/'shard-08';outer.mkdir()
   for inner in (['shard-8'] if kind=='unpadded' else ['shard-8','shard-08'] if kind=='both' else []):
    d=outer/inner;d.mkdir();(d/prefix).write_text('{}')
   runs=[]
   if kind in ('missing','unscanned','ambiguous','partial','corrupt','unbound','verified','alternate','config_mismatch','discovered','declared_mismatch'):
    run=t/('pip-omitted' if kind=='discovered' else 'run');cap=run/'attempts/a';cap.mkdir(parents=True);obj={'id':'test','shards':[8]}
    if kind=='unscanned':obj['output_roots']=[str(t/'other/campaigns-fresh/shard-08/shard-8')]
    if kind=='alternate':obj['output_roots']=[str(root/'alternate/shard-8')]
    if kind=='declared_mismatch':obj['output_roots']=[str(root/'shard-08/shard-08')]
    if kind=='ambiguous':obj['shards']=[]
    raw=json.dumps(obj).encode();(cap/'capture.json').write_bytes(raw);runs=[run]
    if kind!='ambiguous':(cap/'worker-config.json').write_text(json.dumps({'capture_path':str(cap/'capture.json'),'shards':[8],'mode':'normal','output_roots':[str(root/'shard-08/shard-7' if kind=='config_mismatch' else root/'shard-08/shard-8')]}))
    if kind in ('partial','corrupt','unbound','verified'):
     val={'schema':'pip02-paddle-parallel-owner/v1','capture_sha256':hashlib.sha256(raw).hexdigest(),'shards':[8],'smoke':None,'rc':0,'partial':False,'error':None,'factory':{'worker_rc':0}}
     if kind=='partial':val['partial']=True
     if kind=='unbound':val['capture_sha256']='0'*64
     rb=b'{' if kind=='corrupt' else json.dumps(val).encode();(cap/'result.json').write_bytes(rb);(cap/'result.json.durable').write_text(hashlib.sha256(rb).hexdigest())
   with patch.multiple(inv,P=plan,EXPECTED_PLAN=hashlib.sha256(plan.read_bytes()).hexdigest(),ROOTS=[root],RUNS=([] if kind=='discovered' else runs),ATTEMPT_SEARCH_ROOTS=([t] if kind=='discovered' else []),SUCCESSOR=t/'none',R25=t/'r25'):
    result=inv.inventory()
   return next(x for x in result['pages'] if x['shard']==8 and x['page']['index']==40)
 def test_region_capture_provenance_is_not_inferred(self):
  grant='regions=0-23';pins={'source.py':'a'*64};models={'binary':'0aadef69f2b75a1bf5a839a22ed88a5e2f895e5dc492acaae058354690ea9b05','mmproj':'204d757d7610d9b3faab10d506d69e5b244e32bf765e2bab2d0167e65e0a058a','model':'f3ae46ec885050acf4b3d31944431e1fd90d50664fb09126af4a3c050ba14ee8'};prov={'origin_capture_sha256':'abc','origin_grant':grant,'identity':{'campaign_sha256':'7df42c37a8df3a4d35133a8adbeb82af834a06a13ecd074c42bbbee1330f2e15','model_pins':models,'source_pins':pins}};caps={'abc':{'shards':[8],'source_pins':pins,'grant':grant,'grant_sha256':hashlib.sha256(grant.encode()).hexdigest()}}
  self.assertTrue(inv.region_provenance_ok(8,prov,caps));self.assertFalse(inv.region_provenance_ok(8,prov,{}));self.assertFalse(inv.region_provenance_ok(9,prov,caps));changed=dict(prov,origin_grant='different');self.assertFalse(inv.region_provenance_ok(8,changed,caps));changed=dict(prov,identity=dict(prov['identity'],source_pins={'source.py':'b'*64}));self.assertFalse(inv.region_provenance_ok(8,changed,caps))
 def test_metadata_or_order_drift_refuses(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'plan';p.write_text(json.dumps({'pages':[],'prior_original_page_exposures_unknown':[]}))
   with patch.multiple(inv,P=p,EXPECTED_PLAN='0'*64):
    with self.assertRaisesRegex(ValueError,'original plan hash mismatch'):inv.inventory()
 def test_reordered_and_metadata_modified_plan_refuse(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'plan';pages=[{'index':i,'image':str(i)+'.png'} for i in range(755)];original=json.dumps({'pages':pages,'prior_original_page_exposures_unknown':[]}).encode();expected=hashlib.sha256(original).hexdigest()
   for mode in ('metadata','order'):
    rows=[dict(x) for x in pages]
    if mode=='metadata':rows[40]['new_metadata']='changed'
    else:rows[40],rows[41]=rows[41],rows[40]
    p.write_text(json.dumps({'pages':rows,'prior_original_page_exposures_unknown':[]}))
    with patch.multiple(inv,P=p,EXPECTED_PLAN=expected):
     with self.assertRaisesRegex(ValueError,'original plan hash mismatch'):inv.inventory()
 def test_duplicate_index_refuses_even_if_hash_matches(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'plan';pages=[{'index':i,'image':str(i)+'.png'} for i in range(755)];pages[40]['index']=pages[39]['index'];p.write_text(json.dumps({'pages':pages,'prior_original_page_exposures_unknown':[]}))
   with patch.multiple(inv,P=p,EXPECTED_PLAN=hashlib.sha256(p.read_bytes()).hexdigest()):
    with self.assertRaisesRegex(ValueError,'population invalid'):inv.inventory()
 def test_unpadded_prior_request_never_eligible(self):
  x=self.run_scenario('unpadded');self.assertEqual(x['disposition'],'PROTECTED_REGION_UNKNOWN');self.assertEqual(len(x['regions']),1)
 def test_missing_capture_protects_entire_shard(self):
  x=self.run_scenario('missing');self.assertEqual(x['disposition'],'PROTECTED_SCOPE_UNKNOWN');self.assertEqual(x['scope_unknown_shard'],8)
 def test_partial_corrupt_and_unbound_results_protect_scope(self):
  for kind in ('partial','corrupt','unbound'):
   with self.subTest(kind=kind):self.assertEqual(self.run_scenario(kind)['disposition'],'PROTECTED_SCOPE_UNKNOWN')
 def test_verified_bound_complete_can_clear_scope(self):
  self.assertEqual(self.run_scenario('verified')['disposition'],'CANDIDATE_NO_OBSERVED_START')
 def test_unsupported_nested_layout_refuses(self):
  with self.assertRaisesRegex(ValueError,'unsupported capture journal layout'):self.run_scenario('alternate')
 def test_worker_config_scope_mismatch_refuses(self):
  with self.assertRaisesRegex(ValueError,'unsupported capture journal layout'):self.run_scenario('config_mismatch')
 def test_discovered_attempt_root_cannot_be_omitted(self):
  self.assertEqual(self.run_scenario('discovered')['disposition'],'PROTECTED_SCOPE_UNKNOWN')
 def test_capture_and_worker_roots_must_match(self):
  with self.assertRaisesRegex(ValueError,'capture worker config mismatch'):self.run_scenario('declared_mismatch')
 def test_unscanned_declared_root_refuses(self):
  with self.assertRaisesRegex(ValueError,'unscanned capture-declared root'):self.run_scenario('unscanned')
 def test_empty_capture_scope_refuses(self):
  with self.assertRaisesRegex(ValueError,'capture shard scope invalid'):self.run_scenario('ambiguous')
 def test_competing_padded_and_unpadded_fail_closed(self):
  x=self.run_scenario('both');self.assertNotEqual(x['disposition'],'CANDIDATE_NO_OBSERVED_START');self.assertTrue(x['issues'])
if __name__=='__main__':unittest.main()
