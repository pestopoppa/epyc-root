"""Incrementally scan complete request-trace records; no process control here."""
import json

class TraceGuard:
    def __init__(self, path, offset):
        self.path = path
        self.offset = offset
        self.pending = b''

    def poll(self):
        with open(self.path, 'rb') as stream:
            stream.seek(0, 2)
            if stream.tell() < self.offset:
                raise RuntimeError('trace truncated')
            stream.seek(self.offset)
            data = stream.read()
        self.offset += len(data)
        lines = (self.pending + data).split(b'\n')
        self.pending = lines.pop()
        for line in lines:
            if not line:
                continue
            event = json.loads(line)
            if event.get('event') == 'layer_complete' and (event.get('native_success') != 1 or event.get('original_flash_fallback_count') != 0):
                return event
        return None

def valid_first_failure(event, manifest):
    return (event.get('schema') == 'lsa-native-graph-v1'
            and event.get('event') == 'layer_complete'
            and event.get('model_sha256') == manifest['model_sha256']
            and event.get('map_sha256') == manifest['map_sha256']
            and event.get('backend') == 'hip'
            and event.get('layer') in range(3,64,4)
            and all(type(event.get(k)) is int for k in ('sequence','slot','epoch','first','count','native_success','original_flash_fallback_count'))
            and event['sequence'] >= 0 and event['slot'] >= 0 and event['epoch'] > 0
            and event['first'] >= 0 and 0 < event['count'] <= 2048 and event['first'] + event['count'] <= 8192
            and event['native_success'] == 0 and event['original_flash_fallback_count'] >= 1
            and bool(event.get('failure_stage'))
            and bool(event.get('failure_reason'))
            and event.get('failure_reason') != 'cascaded_after_first_failure'
            and isinstance(event.get('failure_detail'), str))
