import asyncio,contextlib,unittest
from redel.delegation.delegate_and_wait import DelegateWait
from safe_delegate_wait import SafeDelegateWait
class Kani:
 @contextlib.contextmanager
 def run_state(self,*args):yield
class T(unittest.TestCase):
 def test_native_bug_and_prospective_fix(self):
  async def run():
   old=DelegateWait(app=None,kani=Kani());new=SafeDelegateWait(app=None,kani=Kani())
   for kind in ('all','next'):
    with self.assertRaisesRegex(ValueError,'empty'):await old.wait(kind)
    self.assertEqual(await new.wait(kind),'No helpers are currently running.')
   self.assertIn('must be the name',await new.wait('missing'))
   async def helper():return ('real child response','alpha')
   new.helper_futures['alpha']=asyncio.create_task(helper())
   self.assertEqual(await new.wait('all'),'alpha:\nreal child response')
  asyncio.run(run())
if __name__=='__main__':unittest.main()
