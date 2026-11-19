import unittest
from job import gauge
class GaugeTest(unittest.TestCase):
 def test_supported_with_labels(self):self.assertEqual(gauge('# HELP x foo\nllamacpp:kv_cache_used_cells{model="x"} 7\n'),7)
 def test_missing_is_not_zero(self):
  with self.assertRaises(ValueError):gauge('llamacpp:other 0\n')
 def test_ambiguous_is_rejected(self):
  with self.assertRaises(ValueError):gauge('llamacpp:kv_cache_used_cells 1\nllamacpp:kv_cache_used_cells 2\n')
 def test_negative_and_fraction_rejected(self):
  for value in ('-1','1.5'):
   with self.subTest(value=value),self.assertRaises(ValueError):gauge('llamacpp:kv_cache_used_cells '+value+'\n')

class CustodyTest(unittest.TestCase):
 def test_exact_overlap_accepted_and_outside_refused(self):
  from job import require_overlap
  require_overlap(10,20,{'start_monotonic_ns':11,'end_monotonic_ns':19})
  for sample in ({'start_monotonic_ns':9,'end_monotonic_ns':11},{'start_monotonic_ns':19,'end_monotonic_ns':21},{'start_monotonic_ns':14,'end_monotonic_ns':13}):
   with self.subTest(sample=sample),self.assertRaises(RuntimeError):require_overlap(10,20,sample)
 def test_device_inode_and_content_binding(self):
  import hashlib,os,tempfile
  from pathlib import Path
  from job import verify_sample
  with tempfile.TemporaryDirectory() as d:
   samples=[];files={}
   for name in ('libggml-cpu.so','libggml-base.so','libllama.so'):
    p=Path(d)/name;p.write_bytes(name.encode());st=p.stat();key=str(p.resolve());files[key]=hashlib.sha256(p.read_bytes()).hexdigest();samples.append({'path':key,'dev_major':os.major(st.st_dev),'dev_minor':os.minor(st.st_dev),'inode':st.st_ino})
   self.assertEqual(len(verify_sample({'libraries':samples},files)),3)
   samples[0]['inode']+=1
   with self.assertRaises(RuntimeError):verify_sample({'libraries':samples},files)
   samples[0]['inode']-=1;Path(samples[0]['path']).write_bytes(b'altered')
   with self.assertRaises(RuntimeError):verify_sample({'libraries':samples},files)

class GrantPathTest(unittest.TestCase):
 def test_filler_grant_suffix_and_bare_decoy(self):
  import tempfile
  from pathlib import Path
  from job import grant_path
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'sample').write_text('wrong');expected=root/'sample.grant';expected.write_text('grant')
   actual=grant_path({'FILLER_GRANTS_DIR':d,'FILLER_ID':'sample'})
   self.assertEqual(actual,expected);self.assertEqual(actual.read_text(),'grant')
 def test_default_grant_directory(self):
  from pathlib import Path
  from job import grant_path
  self.assertEqual(grant_path({'FILLER_ID':'sample'}),Path('/mnt/raid0/llm/tmp/compute-flags/grants/sample.grant'))

class PreservedBuildTest(unittest.TestCase):
 def make_fixture(self, root):
  import gzip,hashlib,json,os
  from pathlib import Path
  from reuse_guard import HEAD
  root=Path(root);bindir=root/'bin';bindir.mkdir()
  server=bindir/'llama-server';server.write_bytes(b'\x7fELFserver');server.chmod(0o755)
  lib=bindir/'libllama-server-impl.so';lib.write_bytes(b'\x7fELFkv_cache_used_cells');(bindir/'libalias.so').symlink_to(lib.name)
  evidence=root/'v1-evidence';evidence.mkdir()
  files={'CMakeCache.txt':b'cache','compile_commands.json':b'commands','v1-evidence/INPUTS.sha256':b'inputs','v1-evidence/job.py':b'job','v1-evidence/launch.sh':b'launch','v1-evidence/RESULT.json':b'result'}
  for name,data in files.items():(root/name).write_bytes(data)
  raw=b'Built target llama-server';(root/'build-full.log.gz').write_bytes(gzip.compress(raw,mtime=0))
  digest=lambda x:hashlib.sha256(x).hexdigest()
  ev={'cmake_cache_sha256':digest(files['CMakeCache.txt']),'compile_commands_sha256':digest(files['compile_commands.json']),'build_log_gzip_sha256':digest((root/'build-full.log.gz').read_bytes()),'build_log_raw_sha256':digest(raw),'v1_inputs_sha256':digest(files['v1-evidence/INPUTS.sha256']),'v1_job_sha256':digest(files['v1-evidence/job.py']),'v1_launcher_sha256':digest(files['v1-evidence/launch.sh']),'v1_result_sha256':digest(files['v1-evidence/RESULT.json'])}
  entries={p.name:{'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size,'symlink_target':os.readlink(p) if p.is_symlink() else None} for p in bindir.iterdir()}
  manifest=root/'manifest.json';manifest.write_text(json.dumps({'schema':'kvu126.preserved-build.v1','declared_source_commit':HEAD,'current_source_commit_checked':HEAD,'fix_specific_metric':'kv_cache_used_cells','metric_library':lib.name,'evidence':ev,'bin_entries':entries}));return manifest
 def test_valid_bundle_and_metric_name_without_full_prefix(self):
  import tempfile
  from pathlib import Path
  from reuse_guard import verify_reused
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);manifest=self.make_fixture(root)
   self.assertEqual(len(verify_reused(root,manifest)),2)
 def test_mutated_binary_and_escaping_symlink_fail(self):
  import tempfile
  from pathlib import Path
  from reuse_guard import verify_reused
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);manifest=self.make_fixture(root);lib=root/'bin/libllama-server-impl.so';old=lib.read_bytes();lib.write_bytes(b'\x7fELFbad')
   with self.assertRaises(ValueError):verify_reused(root,manifest)
   lib.write_bytes(old);alias=root/'bin/libalias.so';alias.unlink();alias.symlink_to('../elsewhere')
   with self.assertRaises((ValueError,FileNotFoundError)):verify_reused(root,manifest)
 def test_original_evidence_tampering_fails(self):
  import tempfile
  from pathlib import Path
  from reuse_guard import verify_reused
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);manifest=self.make_fixture(root);(root/'CMakeCache.txt').write_text('changed')
   with self.assertRaises(ValueError):verify_reused(root,manifest)

if __name__=='__main__':unittest.main()
