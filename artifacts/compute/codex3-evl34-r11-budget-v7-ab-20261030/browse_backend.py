"""Draft shared search/visit backend, not yet wired to either native arm."""
import json
import os
import threading
import time
from urllib.parse import urljoin
from html.parser import HTMLParser

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer"): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer") and self.hidden: self.hidden -= 1
    def handle_data(self, data):
        if not self.hidden and data.strip(): self.parts.append(data.strip())

MAX_CALLS = 12
MAX_OUTPUT = 16000
MAX_PAGE_BYTES = 262144

class BrowseBackend:
    def __init__(self, journal=None):
        self._lock = threading.Lock()
        self._calls = 0
        self.records = []
        self.journal = journal

    def _write(self, record):
        self.records.append(record)
        if self.journal is not None:
            with open(self.journal, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
                f.flush()
                os.fsync(f.fileno())

    def invoke(self, operation, value, max_results=5):
        if operation not in ('search', 'visit') or not isinstance(value, str) or not value or len(value) > 2048:
            raise ValueError('invalid browsing request')
        if type(max_results) is not int or not 1 <= max_results <= 5:
            raise ValueError('invalid result count')
        with self._lock:
            if self._calls >= MAX_CALLS:
                return '[ERROR: browsing call budget exhausted]'
            self._calls += 1
            call_id = self._calls
            self._write({'id':call_id,'phase':'start','operation':operation,'input':value,'max_results':max_results})
        started = time.monotonic()
        outcome = 'success'
        try:
            if operation == 'search':
                from src.tools.web.search import web_search
                result = web_search(value, max_results=max_results)
                output = json.dumps(result, ensure_ascii=False)
                if not result.get('success'): outcome = 'backend_error'
            else:
                output = self._visit(value)
            output = output[:MAX_OUTPUT]
        except Exception as exc:
            outcome = type(exc).__name__
            output = '[ERROR: browsing failed: ' + outcome + ']'
        with self._lock:
            self._write({'id':call_id,'phase':'end','outcome':outcome,'output':output,'elapsed_seconds':time.monotonic()-started})
        return output

    @staticmethod
    def _visit(url):
        from src.repl_environment import web_guard
        for _ in range(web_guard.MAX_REDIRECTS + 1):
            reason = web_guard.check_url(url)
            if reason:
                raise web_guard.WebGuardRefusal(reason)
            session = web_guard._build_session()
            try:
                with session.get(url, headers={'User-Agent':'OrchestratorBot/1.0'}, timeout=(5, 10), allow_redirects=False, stream=True) as response:
                    if response.status_code in (301, 302, 303, 307, 308) and response.headers.get('Location'):
                        url = urljoin(url, response.headers['Location'])
                        continue
                    response.raise_for_status()
                    data = bytearray()
                    for chunk in response.iter_content(8192):
                        data.extend(chunk[:MAX_PAGE_BYTES - len(data)])
                        if len(data) >= MAX_PAGE_BYTES:
                            break
                    content_type = response.headers.get('Content-Type', '')
                    encoding = response.encoding if 'charset=' in content_type.lower() else 'utf-8'
                    text = bytes(data).decode(encoding or 'utf-8', errors='replace')
                    if 'text/html' in response.headers.get('Content-Type', '').lower():
                        parser = TextParser()
                        parser.feed(text)
                        text = '\n'.join(parser.parts)
                    return text
            finally:
                session.close()
        raise web_guard.WebGuardRefusal('too many redirects')
