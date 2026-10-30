"""Task-private ReDel tool mixin using the shared browser broker."""
from kani import ai_function
from redel.tools import ToolBase
from browse_adapters import redel_exchange

class SearchAndVisit(ToolBase):
    def __init__(self,*args,queue,**kwargs):
        super().__init__(*args,**kwargs)
        self.queue=queue
    @ai_function()
    async def search(self,query:str):
        """Search the web for information."""
        return await redel_exchange(self.queue,'search',query)
    @ai_function()
    async def visit_page(self,href:str):
        """Visit a web page and read its contents."""
        return await redel_exchange(self.queue,'visit',href)
