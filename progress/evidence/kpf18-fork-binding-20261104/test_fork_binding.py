"""Exact R6 captured pre-task-assignment fork + following native launch."""
import copy,hashlib,json,pathlib,re,sys,unittest
BASE=pathlib.Path(__file__).resolve().parent
sys.path[:0]=[str(BASE),'/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-normalization-r13/data']
from evidence_view import build
from debug3_data import parse,DataError
from fork_binding import bind_native_fork
RAW_SHA='192c06830316e13c0b86df1c3167aa653667f161ff966ec2d80694d26eb93689'
EVENT_SHA='009ea25cabb3463a0f48dc9de95e311d209c58d0d61065823e7d18a5b449a763'
ABS_START=1166016091
class NativeForkBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(BASE/'fork-launch-native.raw').read_bytes(); event_raw=(BASE/'fork-child-event.json').read_bytes()
        if hashlib.sha256(cls.raw).hexdigest()!=RAW_SHA or hashlib.sha256(event_raw).hexdigest()!=EVENT_SHA:raise ValueError('captured fixture seal')
        cls.event=json.loads(event_raw);view,cls.mapping,_=build(cls.raw);grids,cls.messages=parse(view)
        if grids or len(cls.messages)!=2:raise ValueError('unexpected capture framing')
    def bind(self,messages=None,events=None,mapping=None,scope=ABS_START,raw=None):
        messages=self.messages if messages is None else messages
        return bind_native_fork(messages[0],messages,[self.event] if events is None else events,self.mapping if mapping is None else mapping,scope,self.raw if raw is None else raw)
    def test_actual_old_failure_new_exact_evidence(self):
        self.assertIsNone(re.search(r'id\s+(\d+)\s*\|\s*task\s+(\d+)\s*\|',self.messages[0][2]))
        result=self.bind()
        self.assertEqual((result['slot'],result['logged_task'],result['task'],result['event_id'],result['source'],result['T'],result['total']),(1,-1,205,8,0,32000,36000))
        self.assertEqual(result['fork_native_range'],[1166016091,1166016264]);self.assertEqual(result['launch_native_range'],[1166016264,1166016362])
        self.assertEqual(result['fork_text_sha256'],'afffa4f04502208418f12c1ad2f11a03c3f36174a9390eb1e9ea6ca821d5a027')
        self.assertEqual(result['launch_text_sha256'],'b97bd928480b329e26df101ed1f373358a58f547decd1394b35e834823d6dc02')
    def test_missing_or_ambiguous_launch_is_refused(self):
        with self.assertRaises(DataError):self.bind(messages=self.messages[:1])
        with self.assertRaises(DataError):self.bind(messages=self.messages+[self.messages[1]])
        raw=self.raw.replace(b'launch_slot_: id  1 | task 205',b'launch_slot_: id  2 | task 205',1)
        view,mapping,_=build(raw);_,messages=parse(view)
        with self.assertRaises(DataError):self.bind(messages=messages,mapping=mapping,raw=raw)
    def test_wrong_or_ambiguous_event_is_refused(self):
        with self.assertRaises(DataError):self.bind(events=[])
        with self.assertRaises(DataError):self.bind(events=[self.event,self.event])
        conflicting=copy.deepcopy(self.event);conflicting['response']['timings']['id_task']=206
        with self.assertRaises(DataError):self.bind(events=[self.event,conflicting])
        for field,value in (('slot',2),('native_start',1166016363),('native_end',1166016263)):
            event=copy.deepcopy(self.event);event[field]=value
            with self.subTest(field=field),self.assertRaises(DataError):self.bind(events=[event])
    def test_conflicting_response_and_request_are_refused(self):
        for field,value in (('id_task',206),('id_slot',2),('fork_src_slot',3),('n_fork_tokens',31999),('fork_src_kind','none')):
            event=copy.deepcopy(self.event);event['response']['timings'][field]=value
            with self.subTest(field=field),self.assertRaises(DataError):self.bind(events=[event])
        event=copy.deepcopy(self.event);event['request']['id_slot']=2
        with self.assertRaises(DataError):self.bind(events=[event])
        event=copy.deepcopy(self.event);event['request']['prompt'].pop()
        with self.assertRaises(DataError):self.bind(events=[event])
    def test_original_offset_and_logged_task_conflicts_refused(self):
        with self.assertRaises(DataError):self.bind(scope=0)
        line=self.messages[0];modified=(line[0],line[1],line[2].replace('task -1','task 999'))
        with self.assertRaises(DataError):self.bind(messages=[modified,self.messages[1]])
if __name__=='__main__':unittest.main()
