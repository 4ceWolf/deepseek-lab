#!/usr/bin/env python3
"""Local DeepSeek experiment console. Python standard library only."""
import json, os, sqlite3, threading, time, uuid, urllib.request, urllib.error, runpy
from contextlib import contextmanager
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('DEEPSEEK_LAB_DATA', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
DB = DATA / 'lab.sqlite3'
LOCK = threading.RLock()
KEY = ''
BUSY = set()
DEFAULT = 'Be clear, accurate, and concise. Match the depth of the answer to the task. Ask for clarification only when missing information prevents a useful answer. State uncertainty when evidence is insufficient. Never claim to have used tools or verified information unless a tool result supports it.'

def engine():
    return runpy.run_path(str(ROOT/'engine.py'))

@contextmanager
def connect_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()

def init():
    with connect_db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, title TEXT, created REAL, messages TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, session_id TEXT, created REAL, kind TEXT, payload TEXT)')
    os.chmod(DB, 0o600)

def scrub(value):
    if isinstance(value, str):
        return value.replace(KEY, '[REDACTED]') if KEY else value
    if isinstance(value, list): return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: '[REDACTED]' if k.lower() in ('api_key','authorization','key') else scrub(v) for k,v in value.items()}
    return value

def event(sid, kind, payload):
    with connect_db() as db:
        db.execute('INSERT INTO events VALUES (?,?,?,?,?)', (uuid.uuid4().hex, sid, time.time(), kind, json.dumps(scrub(payload))))

def api(path, payload=None, key=None):
    req = urllib.request.Request('https://api.deepseek.com' + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization':'Bearer ' + (key if key is not None else KEY), 'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', 'replace')[:12000]
        raise RuntimeError(f'DeepSeek HTTP {exc.code}: {body}') from None
    except (TimeoutError, urllib.error.URLError) as exc:
        raise RuntimeError('Connection failed or timed out. Check the run log before retrying; a timed-out request may still be billed.') from None

def sessions():
    with connect_db() as db:
        return [dict(r) for r in db.execute('SELECT id,title,created FROM sessions ORDER BY created DESC')]

def get_session(sid):
    with connect_db() as db:
        row = db.execute('SELECT * FROM sessions WHERE id=?',(sid,)).fetchone()
    if not row: raise ValueError('Conversation not found')
    data = dict(row); data['messages'] = json.loads(data['messages'])
    return data

def new_session(title):
    sid = uuid.uuid4().hex
    with connect_db() as db:
        db.execute('INSERT INTO sessions VALUES (?,?,?,?)',(sid, str(title or 'Untitled experiment')[:100],time.time(),'[]'))
    event(sid,'session_created',{'title':title})
    return sid

def export():
    with connect_db() as db:
        ss = [dict(r) for r in db.execute('SELECT * FROM sessions ORDER BY created')]
        ee = [dict(r) for r in db.execute('SELECT * FROM events ORDER BY created')]
    for s in ss: s['messages'] = json.loads(s['messages'])
    for e in ee: e['payload'] = json.loads(e['payload'])
    return scrub({'format':'deepseek-lab-v1','exported_at':time.time(),'sessions':ss,'events':ee})

def run(data):
    sid = data['session_id']
    with LOCK:
        if sid in BUSY: raise ValueError('This conversation already has a request in progress')
        BUSY.add(sid)
    try:
        session = get_session(sid)
        prompt = str(data.get('prompt','')).strip()
        if not prompt: raise ValueError('Write a message first')
        model = data.get('model','deepseek-flash')
        if model not in ('deepseek-flash','deepseek-v4-pro'): raise ValueError('Unsupported model')
        demo = bool(data.get('demo',False))
        if sid.startswith('recovered_'): raise ValueError('Recovered records are historical and incomplete; start a new conversation.')
        if any(m.get('demo') != demo for m in session['messages'] if m['role'] == 'assistant'):
            raise ValueError('Start a new conversation when switching between Demo and live mode')
        if not demo and not KEY: raise ValueError('Connect your API key first, or select Demo')
        module = engine()
        prepared = module['prepare'](data,session['messages'])
        decision = prepared['decision']
        effort,cap = decision['effort'],decision['max_tokens']
        messages = prepared['messages']
        payload = {'model':model,'messages':messages,'max_tokens':cap,'stream':False,
                   'thinking':{'type':'disabled' if effort=='none' else 'enabled'}}
        if effort != 'none': payload['reasoning_effort'] = effort
        rid = uuid.uuid4().hex
        event(sid,'route',{'run_id':rid,'decision':decision})
        event(sid,'request',{'run_id':rid,'demo':demo,'request':payload})
        start = time.monotonic()
        try:
            if demo:
                response = {'id':'demo-'+rid,'model':model,'choices':[{'message':{'role':'assistant','content':'Demo response — no API request was made.\n\nYour instruction set, message, selected effort, and output budget have been recorded. Connect DeepSeek and turn Demo off to receive a real model answer.'},'finish_reason':'stop'}], 'usage':{}}
            else:
                response = api('/chat/completions',payload)
            elapsed = round(time.monotonic()-start,3)
            choice = response['choices'][0]
            message = choice['message']
            if not isinstance(message.get('content'),str):
                raise ValueError('DeepSeek returned no text content')
            event(sid,'response',{'run_id':rid,'demo':demo,'elapsed_seconds':elapsed,'response':response})
            validation = module['validate'](message['content'],data.get('output_check','none'))
            event(sid,'validation',{'run_id':rid,'result':validation})
            stored = session['messages'] + [{'role':'user','content':prompt,'run_id':rid,'attachments':module['validate_attachments'](data.get('attachments',[]))},
                {'role':'assistant','content':message['content'],'reasoning_content':message.get('reasoning_content',''),
                 'run_id':rid,'model':model,'effort':effort,'demo':demo,'elapsed_seconds':elapsed,
                 'usage':response.get('usage',{}),'finish_reason':choice.get('finish_reason'),'decision':decision,'validation':validation}]
            with connect_db() as db:
                db.execute('UPDATE sessions SET messages=? WHERE id=?',(json.dumps(scrub(stored)),sid))
            return {'session':get_session(sid),'run_id':rid}
        except Exception as exc:
            event(sid,'error',{'run_id':rid,'elapsed_seconds':round(time.monotonic()-start,3),'error':str(exc)})
            raise
    finally:
        with LOCK: BUSY.discard(sid)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,code,data,content_type='application/json'):
        body = (json.dumps(scrub(data)) if content_type=='application/json' else data).encode()
        self.send_response(code)
        self.send_header('Content-Type',content_type+'; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        self.send_header('Content-Length',str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def allowed(self):
        host = self.headers.get('Host','')
        expected = f'127.0.0.1:{self.server.server_port}'
        alternate = f'localhost:{self.server.server_port}'
        if host not in (expected,alternate): return False
        origin = self.headers.get('Origin')
        return origin is None or origin == 'http://'+host
    def do_GET(self):
        if not self.allowed(): return self.reply(403,{'error':'Local access only'})
        path = self.path.split('?')[0]
        try:
            if path in ('/','/app.js','/style.css'):
                name = {'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
                kind = {'/':'text/html','/app.js':'application/javascript','/style.css':'text/css'}[path]
                return self.reply(200,(ROOT/name).read_text(),kind)
            if path == '/api/state': return self.reply(200,{'connected':bool(KEY),'sessions':sessions(),'defaults':engine()['INSTRUCTIONS'],'version':engine()['VERSION'],'knowledge_count':len(engine()['cards']()),'data_directory':str(DATA)})
            if path == '/api/knowledge': return self.reply(200,{'cards':engine()['cards'](),'manifest':json.loads((ROOT/'knowledge/manifest.json').read_text())})
            if path == '/api/export': return self.reply(200,export())
            if path.startswith('/api/session/'):
                return self.reply(200,get_session(path.rsplit('/',1)[1]))
            if path == '/api/events': return self.reply(200,export()['events'])
            return self.reply(404,{'error':'Not found'})
        except Exception as exc: return self.reply(400,{'error':str(exc)})
    def do_POST(self):
        global KEY
        if not self.allowed() or self.headers.get('Content-Type','').split(';')[0] != 'application/json':
            return self.reply(403,{'error':'Same-origin JSON requests only'})
        try:
            size = int(self.headers.get('Content-Length','0'))
            if size < 0 or size > 2_000_000: raise ValueError('Request too large')
            data = json.loads(self.rfile.read(size))
            if self.path == '/api/connect':
                key = str(data.get('key','')).strip()
                if not key: raise ValueError('Enter your DeepSeek API key')
                try: result = api('/models',key=key)
                except Exception:
                    return self.reply(400,{'error':'Could not validate the key with DeepSeek. Check the key and your connection.'})
                with LOCK:
                    if BUSY: raise ValueError('Wait for active runs before changing the key')
                    KEY = key
                event(None,'key_connected',{'models':result.get('data',[])})
                return self.reply(200,{'connected':True})
            if self.path == '/api/disconnect':
                with LOCK:
                    if BUSY: raise ValueError('Wait for active runs before disconnecting')
                    KEY = ''
                event(None,'key_disconnected',{})
                return self.reply(200,{'connected':False})
            if self.path == '/api/session': return self.reply(200,{'id':new_session(data.get('title'))})
            if self.path == '/api/preview':
                history=get_session(data['session_id'])['messages'] if data.get('session_id') else []
                return self.reply(200,engine()['prepare'](data,history))
            if self.path == '/api/run': return self.reply(200,run(data))
            if self.path == '/api/note':
                event(data.get('session_id'),'review',{'run_id':data.get('run_id'),'rating':data.get('rating'),'note':data.get('note','')})
                return self.reply(200,{'saved':True})
            return self.reply(404,{'error':'Not found'})
        except Exception as exc: return self.reply(400,{'error':str(exc)})

if __name__ == '__main__':
    init()
    port = int(os.environ.get('DEEPSEEK_LAB_PORT','8765'))
    server = ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'DeepSeek Lab: http://127.0.0.1:{port}',flush=True)
    server.serve_forever()
