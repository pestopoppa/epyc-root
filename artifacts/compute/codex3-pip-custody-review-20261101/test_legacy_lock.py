import fcntl,os,pathlib,tempfile,unittest
import legacy_lock_reference as legacy
class Custody(unittest.TestCase):
 def test_missing_directory_creation_and_competing_fd(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);fd=legacy.acquire(root,122)
   try:
    p=root/'shard-122/campaign.serial.lock';self.assertTrue(p.is_file());self.assertFalse(os.get_inheritable(fd))
    with p.open('r+') as other:
     with self.assertRaises(BlockingIOError):fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
   finally:os.close(fd)
   with p.open('r+') as other:fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
 def test_unsafe_symlink_refused(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);target=root/'other';target.mkdir();(root/'shard-122').symlink_to(target,target_is_directory=True)
   with self.assertRaises(OSError):legacy.acquire(root,122)
 def test_lock_replacement_is_not_same_inode(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);fd=legacy.acquire(root,122)
   try:
    p=root/'shard-122/campaign.serial.lock';old=os.fstat(fd);p.unlink();p.touch();new=p.stat();self.assertNotEqual((old.st_dev,old.st_ino),(new.st_dev,new.st_ino))
   finally:os.close(fd)
if __name__=='__main__':unittest.main()
