import csv, tempfile, unittest
from pathlib import Path
from marker_csv import HEADERS, PREFIX, normalize

class MarkerCsv(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.path=Path(self.temp.name)/'x.csv'
        self.rows=[['MARKER_CORE_API',PREFIX+str(i),'42','43',str(i+1),str(100+i*10),str(100+i*10)] for i in range(2)]
    def tearDown(self): self.temp.cleanup()
    def write(self,rows=None,headers=HEADERS):
        with self.path.open('w',newline='') as f:
            w=csv.writer(f); w.writerow(headers); w.writerows(self.rows if rows is None else rows)
    def test_good(self):
        self.write(); self.assertEqual(normalize(self.path)[1]['timestamp_ns'],110)
    def test_invalid(self):
        for mutate in ('header','duplicate','missing','interval','domain','number','unknown'):
            with self.subTest(mutate=mutate):
                rows=[r.copy() for r in self.rows]; headers=HEADERS
                if mutate=='header': headers=HEADERS[:-1]
                elif mutate=='duplicate': rows[1]=rows[0].copy()
                elif mutate=='missing': rows.pop()
                elif mutate=='interval': rows[0][-1]='101'
                elif mutate=='domain': rows[0][0]='OTHER'
                elif mutate=='number': rows[0][2]='NaN'
                elif mutate=='unknown': rows[0][1]=PREFIX+'2'
                self.write(rows,headers)
                with self.assertRaises(ValueError): normalize(self.path)
if __name__=='__main__': unittest.main()
