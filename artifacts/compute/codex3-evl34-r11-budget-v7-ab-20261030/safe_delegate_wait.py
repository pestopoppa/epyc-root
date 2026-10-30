"""Prospective narrow adapter for pinned ReDel's empty-helper wait bug."""
from typing import Annotated
from kani import AIParam,ai_function
from redel.delegation.delegate_and_wait import DelegateWait
class SafeDelegateWait(DelegateWait):
 async def create_delegate_kani(self, *args, **kwargs):
  # A reservation persists even if creation fails; never silently exceed scope.
  count=getattr(self,'_evl34_children_reserved',0)
  if count>=16:raise RuntimeError('distinct child limit exhausted')
  self._evl34_children_reserved=count+1
  return await super().create_delegate_kani(*args, **kwargs)

 @ai_function(auto_truncate=6000)
 async def wait(self,until:Annotated[str,AIParam('The name of the helper. Pass "next" for the next helper, or "all" for all running helpers.')]):
  """Wait for a helper to finish their task and get their result."""
  if until in ('next','all') and not self.helper_futures:
   return 'No helpers are currently running.'
  return await super().wait(until)
