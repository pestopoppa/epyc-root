import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from browse_backend import BrowseBackend, MAX_CALLS

class BrowseTests(unittest.TestCase):
    def test_search_and_budget(self):
        with patch('src.tools.web.search.web_search', return_value={'success':True,'results':[]}) as search:
            b=BrowseBackend()
            for _ in range(MAX_CALLS): self.assertIn('"success": true', b.invoke('search','neutral query'))
            self.assertIn('budget exhausted', b.invoke('search','another'))
            self.assertEqual(search.call_count, MAX_CALLS)
    def test_private_address_refused_before_connect(self):
        b=BrowseBackend()
        with patch('src.repl_environment.web_guard._build_session') as session:
            self.assertIn('WebGuardRefusal', b.invoke('visit','http://127.0.0.1/secret'))
            session.assert_not_called()
    def test_journal_records_inputs_outputs(self):
        with tempfile.TemporaryDirectory(dir="/dev/shm") as d:
            path=Path(d)/"calls.jsonl"
            with patch("src.tools.web.search.web_search", return_value={"success":True,"results":[]}):
                BrowseBackend(path).invoke("search","neutral",3)
            a,b=map(json.loads,path.read_text().splitlines())
            self.assertEqual((a["phase"],a["max_results"],b["phase"],b["outcome"]),("start",3,"end","success"))
            self.assertIn("results",b["output"])
    def test_rejects_bad_input(self):
        b=BrowseBackend()
        for operation,value in [('arbitrary','q'),('search',''),('search','a'*2049)]:
            with self.assertRaises(ValueError): b.invoke(operation,value)
if __name__=='__main__': unittest.main()
