"""Original unittest status to original JUnit; no expected-status substitution."""
import pathlib,unittest,xml.etree.ElementTree as ET,sys,time
import test_histogram_controls
class OriginalResult(unittest.TestResult):
 def __init__(self):super().__init__();self.rows=[];self.starts={}
 def startTest(self,test):super().startTest(test);self.starts[test.id()]=time.monotonic()
 def row(self,test,kind=None,text=None):
  name=test.id().rsplit('.',1);r=ET.Element('testcase',classname=name[0],name=name[1],time=str(time.monotonic()-self.starts[test.id()]));
  if kind:ET.SubElement(r,kind).text=text
  self.rows.append(r)
 def addSuccess(self,test):super().addSuccess(test);self.row(test)
 def addFailure(self,test,err):super().addFailure(test,err);self.row(test,'failure',self._exc_info_to_string(err,test))
 def addError(self,test,err):super().addError(test,err);self.row(test,'error',self._exc_info_to_string(err,test))
 def addSkip(self,test,reason):super().addSkip(test,reason);self.row(test,'skipped',reason)
r=OriginalResult();unittest.defaultTestLoader.loadTestsFromModule(test_histogram_controls).run(r)
root=ET.Element('testsuite',tests=str(r.testsRun),failures=str(len(r.failures)),errors=str(len(r.errors)),skipped=str(len(r.skipped)));root.extend(r.rows)
p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True)
with p.open('xb') as f:ET.ElementTree(root).write(f,encoding='utf-8',xml_declaration=True)
print('Original unittest collected=%s failure=%s error=%s skipped=%s'%(r.testsRun,len(r.failures),len(r.errors),len(r.skipped)));sys.exit(0 if r.wasSuccessful() and r.testsRun==7 and not r.skipped else 1)
